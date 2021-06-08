"""
Contain functions used by both `run_experiment.py` and `run_notebook.py` to run
experiments.

Import as:

import core.dataflow_model.utils as cdtfut
"""

# TODO(gp): experiment_utils.py

import argparse
import collections
import glob
import logging
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

import core.config as cconfig
import core.config as cfg
import core.config_builders as cfgb
import core.dataflow as dtg
import helpers.dbg as dbg
import helpers.io_ as io_
import helpers.pickle_ as hpickle
import helpers.printing as hprint

_LOG = logging.getLogger(__name__)


def add_experiment_arg(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add common command line options to run the experiments.
    """
    parser.add_argument(
        "--src_dir",
        action="store",
        required=True,
        help="Directory storing the results",
    )
    parser.add_argument(
        "--clean_dst_dir",
        action="store_true",
        help="Delete the destination dir before running experiments",
    )
    parser.add_argument(
        "--no_incremental",
        action="store_true",
        help="Skip experiments already performed",
    )
    parser.add_argument(
        "--config_builder",
        action="store",
        required=True,
        help="""
        Full invocation of Python function to create configs, e.g.,
        `nlp.build_configs.build_Task1297_configs(random_seed_variants=[911,2,0])`
        """,
    )
    parser.add_argument(
        "--skip_on_error",
        action="store_true",
        help="Continue execution of experiments after encountering an error",
    )
    parser.add_argument(
        "--index",
        action="store",
        default=None,
        help="Run a single experiment corresponding to the i-th config",
    )
    parser.add_argument(
        "--start_from_index",
        action="store",
        default=None,
        help="Run experiments starting from a specified index",
    )
    parser.add_argument(
        "--only_print_configs",
        action="store_true",
        help="Print the configs and exit",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Print configs and exit without running",
    )
    # TODO(gp): Add an option to run a short experiment to sanity check the flow.
    parser.add_argument(
        "--num_attempts",
        default=1,
        type=int,
        help="Repeat running the experiment up to `num_attempts` times",
        required=False,
    )
    parser.add_argument(
        "--num_threads",
        action="store",
        help="Number of threads to use (-1 to use all CPUs)",
        required=True,
    )
    return parser


def skip_configs_already_executed(
    configs: List[cconfig.Config], incremental: bool
) -> Tuple[List[cconfig.Config], int]:
    """
    Remove from the list the configs that have already been executed.
    """
    configs_out = []
    num_skipped = 0
    for config in configs:
        # If there is already a success file in the dir, skip the experiment.
        experiment_result_dir = config[("meta", "experiment_result_dir")]
        file_name = os.path.join(experiment_result_dir, "success.txt")
        if incremental and os.path.exists(file_name):
            idx = config[("meta", "id")]
            _LOG.warning("Found file '%s': skipping run %d", file_name, idx)
            num_skipped += 1
        else:
            configs_out.append(config)
    return configs_out, num_skipped


def mark_config_as_success(experiment_result_dir: str) -> None:
    """
    Publish an empty file to indicate a successful finish.
    """
    file_name = os.path.join(experiment_result_dir, "success.txt")
    _LOG.info("Creating file_name='%s'", file_name)
    io_.to_file(file_name, "success")


def setup_experiment_dir(config: cconfig.Config) -> None:
    """
    Set up the directory and the book-keeping artifacts for the experiment
    running `config`.

    :return: whether we need to run this config or not
    """
    dbg.dassert_isinstance(config, cconfig.Config)
    # Create subdirectory structure for experiment results.
    experiment_result_dir = config[("meta", "experiment_result_dir")]
    _LOG.info("Creating experiment dir '%s'", experiment_result_dir)
    io_.create_dir(experiment_result_dir, incremental=True)
    # Prepare book-keeping files.
    file_name = os.path.join(experiment_result_dir, "config.pkl")
    _LOG.debug("Saving '%s'", file_name)
    hpickle.to_pickle(config, file_name)
    #
    file_name = os.path.join(experiment_result_dir, "config.txt")
    _LOG.debug("Saving '%s'", file_name)
    io_.to_file(file_name, str(config))


def select_config(
    configs: List[cconfig.Config],
    index: Optional[int],
    start_from_index: Optional[int],
) -> List[cconfig.Config]:
    """
    Select configs to run based on the command line parameters.

    :param configs: list of configs
    :param index: index of a config to execute, if not `None`
    :param start_from_index: index of a config to start execution from, if not `None`
    :return: list of configs to execute
    """
    dbg.dassert_container_type(configs, List, cconfig.Config)
    dbg.dassert_lte(1, len(configs))
    if index is not None:
        index = int(index)
        _LOG.warning("Only config %d will be executed because of --index", index)
        dbg.dassert_lte(0, index)
        dbg.dassert_lt(index, len(configs))
        configs = [configs[index]]
    elif start_from_index is not None:
        start_from_index = int(start_from_index)
        _LOG.warning(
            "Only configs >= %d will be executed because of --start_from_index",
            start_from_index,
        )
        dbg.dassert_lte(0, start_from_index)
        dbg.dassert_lt(start_from_index, len(configs))
        configs = [c for idx, c in enumerate(configs) if idx >= start_from_index]
    _LOG.info("Selected %s configs", len(configs))
    dbg.dassert_container_type(configs, List, cconfig.Config)
    return configs


def get_configs_from_command_line(args: argparse.Namespace) -> List[cconfig.Config]:
    """
    Return all the configs to run given the command line interface.

    The configs are patched with all the information from the command
    line (e.g., `idx`, `config_builder`, `experiment_builder`,
    `src_dir`, `experiment_result_dir`).
    """
    # Build the map with the config parameters.
    config_builder = args.config_builder
    configs = cconfig.get_configs_from_builder(config_builder)
    params = {
        "config_builder": args.config_builder,
        "src_dir": args.dst_dir,
    }
    if hasattr(args, "experiment_builder"):
        params["experiment_builder"] = args.experiment_builder
    # Patch the configs with the command line parameters.
    configs = cconfig.patch_configs(configs, params)
    _LOG.info("Generated %d configs from the builder", len(configs))
    # Select the configs based on command line options.
    index = args.index
    start_from_index = args.start_from_index
    configs = select_config(configs, index, start_from_index)
    _LOG.info("Selected %d configs from command line", len(configs))
    # Remove the configs already executed.
    incremental = not args.no_incremental
    configs, num_skipped = skip_configs_already_executed(configs, incremental)
    _LOG.info("Removed %d configs since already executed", num_skipped)
    _LOG.info("Need to execute %d configs", len(configs))
    # Handle --dry_run, if needed.
    if args.dry_run:
        _LOG.warning(
            "The following configs will not be executed due to passing --dry_run:"
        )
        for i, config in enumerate(configs):
            print(hprint.frame("Config %d/%s" % (i + 1, len(configs))))
            print(str(config))
        sys.exit(0)
    return configs


def report_failed_experiments(configs: List[cconfig.Config], rcs: List[int]) -> int:
    """
    Report failing experiments.

    :return: return code
    """
    # Get the experiment selected_idxs.
    experiment_ids = [int(config[("meta", "id")]) for config in configs]
    # Match experiment selected_idxs with their return codes.
    failed_experiment_ids = [
        i for i, rc in zip(experiment_ids, rcs) if rc is not None and rc != 0
    ]
    # Report.
    if failed_experiment_ids:
        _LOG.error(
            "There are %d failed experiments: %s",
            len(failed_experiment_ids),
            failed_experiment_ids,
        )
        rc = -1
    else:
        rc = 0
    # TODO(gp): Save on a file the failed experiments' configs.
    return rc


# #############################################################################


def save_experiment_result_bundle(
    config: cfg.Config, result_bundle: dtg.ResultBundle
) -> None:
    """
    Save the `ResultBundle` from running `Config`.
    """
    path = os.path.join(
        config["meta", "experiment_result_dir"], "result_bundle.pkl"
    )
    # TODO(gp): This should be a method of `ResultBundle`.
    obj = result_bundle.to_config().to_dict()
    hpickle.to_pickle(obj, path)


# TODO(gp): We might want also to compare to the original experiments Configs.
def load_experiment_artifacts(
    src_dir: str, file_name: str, selected_idxs: Optional[Iterable[int]] = None
) -> Dict[int, Any]:
    """
    Load all the files in dirs under `src_dir` that match `file_name`.

    This function assumes subdirectories withing `dst_dir` have the following
    structure:
    ```
    {dst_dir}/result_{idx}/{file_name}
    ```
    where `idx` denotes an integer encoded in the subdirectory name.

    The function returns the contents of the files, indexed by the integer extracted
    from the subdirectory index name.

    :param src_dir: directory containing subdirectories of experiment results
        It is the directory that was specified as `--dst_dir` in `run_experiment.py`
        and `run_notebook.py`
    :param file_name: the file name within each run results subdirectory to load
        E.g., `result_bundle.pkl`
    :param selected_idxs: specific experiment indices to load
        - `None` (default) loads all available indices
    """
    _LOG.info("# Load artifacts '%s' from '%s'", file_name, src_dir)
    # Retrieve all the subdirectories in `src_dir`.
    subdirs = [d for d in glob.glob(f"{src_dir}/result_*") if os.path.isdir(d)]
    _LOG.info("Found %d experiment subdirs in '%s'", len(subdirs), src_dir)
    # Build a mapping from "config_idx" to "experiment_dir".
    config_idx_to_dir = {}
    for subdir in subdirs:
        _LOG.debug("subdir='%s'", subdir)
        # E.g., `result_123"
        m = re.match(r"^result_(\d+)$", os.path.basename(subdir))
        dbg.dassert(m)
        key = int(m.group(1))
        dbg.dassert_not_in(key, config_idx_to_dir)
        config_idx_to_dir[key] = subdir
    # Specify the indices of files to load.
    config_idxs = config_idx_to_dir.keys()
    if selected_idxs is None:
        selected_keys = sorted(config_idxs)
    else:
        idxs_l = set(selected_idxs)
        dbg.dassert_is_subset(idxs_l, set(config_idxs))
        selected_keys = [key for key in sorted(config_idxs) if key in idxs_l]
    # Iterate over experiment directories.
    results = collections.OrderedDict()
    for key in selected_keys:
        subdir = config_idx_to_dir[key]
        dbg.dassert_dir_exists(subdir)
        file_name_tmp = os.path.join(src_dir, subdir, file_name)
        _LOG.info("Loading '%s'", file_name_tmp)
        if not os.path.exists(file_name_tmp):
            _LOG.warning("Can't find '{file_name_tmp}': skipping")
            continue
        if file_name_tmp.endswith(".pkl"):
            # Load pickle files.
            res = hpickle.from_pickle(
                file_name_tmp, log_level=logging.DEBUG, verbose=False
            )
        elif file_name_tmp.endswith(".json"):
            # Load JSON files.
            with open(file_name_tmp, "r") as file:
                res = json.load(file)
        elif file_name_tmp.endswith(".txt"):
            # Load txt files.
            res = hio.from_file(file_name_tmp)
        else:
            raise ValueError(f"Unsupported file type='{file_name_tmp}'")
        results[key] = res
    return results
