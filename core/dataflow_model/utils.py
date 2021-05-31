"""
Contain functions used by both `run_pipeline.py` and `run_notebook.py` to run
experiment.

Import as:

import core.dataflow_model.utils as cdtfut
"""

import argparse
import logging
import os
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)


import core.config as cfg
import core.config_builders as cfgb
import helpers.dbg as dbg
import helpers.io_ as io_

_LOG = logging.getLogger(__name__)


def add_experiment_arg(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add common command line options to run the experiments.
    """
    parser.add_argument(
        "--dst_dir",
        action="store",
        required=True,
        help="Directory storing the results",
    )
    parser.add_argument(
        "--no_incremental",
        action="store_true",
        help="Delete the dir before running or skip experiments already performed",
    )
    parser.add_argument(
        "--config_builder",
        action="store",
        required=True,
        help="Full invocation of Python function to create configs, e.g., "
        "`nlp.build_configs.build_PTask1297_configs(random_seed_variants="
        "[911,2,42,0])`",
    )
    parser.add_argument(
        "--skip_on_error",
        action="store_true",
        help="Continue execution of experiments after encountering an error",
    )
    parser.add_argument(
        "--index",
        action="store",
        help="Run a single experiment corresponding to the i-th config",
    )
    parser.add_argument(
        "--start_from_index",
        action="store",
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
    # TODO(gp): Run a short experiment to sanity check the flow.
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


def skip_configs_already_executed(configs, incremental):
    configs_out = []
    num_skipped = 0
    for config in configs:
        # If there is already a success file in the dir, skip the experiment.
        experiment_result_dir = config[("meta", "experiment_result_dir")]
        file_name = os.path.join(experiment_result_dir, "success.txt")
        if incremental and os.path.exists(file_name):
            _LOG.warning("Found file '%s': skipping run %d", file_name, i)
            num_skipped += 1
        else:
            configs_out.append(config)
    return configs_out, num_skipped


def mark_config_as_success(experiment_result_dir):
    # Publish an empty file to indicate a successful finish.
    file_name = os.path.join(experiment_result_dir, "success.txt")
    _LOG.info("file_name=%s", file_name)
    io_.to_file(file_name, "")


def setup_experiment_dir(config):
    """
    Set up the directory and the book-keeping artifacts for the experiment
    running `config`.

    :return: whether we need to run this config or not
    """
    dbg.dassert_isinstance(config, cfg.Config)
    # TODO(gp): Can we just create instead of asserting?
    # dbg.dassert_dir_exists(dst_dir)

    # Create subdirectory structure for experiment results.
    # result_subdir = "result_%s" % i
    # experiment_result_dir = os.path.join(dst_dir, result_subdir)
    # _LOG.info("experiment_result_dir=%s", experiment_result_dir)
    experiment_result_dir = config[("meta", "experiment_result_dir")]
    # TODO(gp): Create dir.
    io_.create_dir(experiment_result_dir, incremental=True)

    # # If there is already a success file in the dir, skip the experiment.
    # file_name = os.path.join(experiment_result_dir, "success.txt")
    # if incremental and os.path.exists(file_name):
    #     _LOG.warning("Found file '%s': skipping run %d", file_name, i)
    #     # TODO(gp): Return to execute.
    #     return False

    # # Inject the experiment result dir inside the config.
    # # TODO(gp): This operation is also performed on the notebook side
    # #  in `get_config_from_env()`. Find a better way to achieve this.
    # config = cfgb.set_experiment_result_dir(experiment_result_dir,
    #                                         config)
    # Prepare book-keeping files.
    file_name = os.path.join(experiment_result_dir, "config.pkl")
    _LOG.info("file_name=%s", file_name)
    hpickle.to_pickle(config, file_name)
    #
    file_name = os.path.join(experiment_result_dir, "config.txt")
    _LOG.info("file_name=%s", file_name)
    io_.to_file(file_name, str(config))
    #
    file_name = os.path.join(experiment_result_dir, "config_builder.txt")
    _LOG.info("file_name=%s", file_name)
    io_.to_file(
        file_name,
        "Config builder: %s\nConfig index: %s" % (config_builder, str(i)),
    )


def select_config(
    configs: List[cfg.Config], index: int, start_from_index: int
) -> List[cfg.Config]:
    """
    Select configs to run from a list of configs.

    :param configs: a list of configs
    :param index: index of a config to execute
    :param start_from_index: index of a config to start execution with
    :return: a list of configs to execute
    """
    if index:
        ind = int(index)
        dbg.dassert_lte(0, ind)
        dbg.dassert_lt(ind, len(configs))
        _LOG.warning(
            "Only config %s will be executed due to passing --index", ind
        )
        # TODO(gp): Why this to overwrite index?
        if "id" in configs[0]["meta"].to_dict():
            # Select a config based on the id parameter if it exists.
            configs = [x for x in configs if int(x[("meta", "id")]) == ind]
        else:
            # Otherwise use index to select a config.
            configs = [x for i, x in enumerate(configs) if i == ind]
    elif start_from_index:
        start_from_index = int(start_from_index)
        dbg.dassert_lte(0, start_from_index)
        dbg.dassert_lt(start_from_index, len(configs))
        _LOG.warning(
            "Only configs %s and higher will be executed due to passing --start_from_index",
            start_from_index,
        )
        # TODO(gp): Why this to overwrite index?
        if "id" in configs[0]["meta"].to_dict():
            # Select configs based on the id parameter if it exists.
            configs = [
                x for x in configs if int(x[("meta", "id")]) >= start_from_index
            ]
        else:
            # Otherwise use index to select configs.
            configs = [x for i, x in enumerate(configs) if i >= start_from_index]
    _LOG.info("Created %s config(s)", len(configs))


def get_configs_from_command_line(args):
    """
    Return all the configs to run given the command line interface.

    The configs are patched with all the information from the command line
    (e.g., `idx`, `config_builder`, `pipeline_builder`, `dst_dir`,
    `experiment_dst_dir`).
    """
    config_builder = args.function
    configs = cfgb.get_configs_from_builder(config_builder)
    # Common params.
    params = {
        "config_builder": args.config_builder,
        "dst_dir": args.dst_dir,
      }
    if getattr(args, "pipeline_builder"):
        params["pipeline_builder"] = args.pipeline_builder
    configs = cfgb.patch_configs(configs, params)
    _LOG.info("Generated %d configs from the builder", len(configs))
    # Select the configs based on command line options.
    index = args.index
    start_from_index = args.start_from_index
    configs = select_config(configs, index, start_from_index)
    _LOG.info("Selected %d configs from command line", len(configs))
    # Remove the configs already executed.
    configs, num_skipped = skip_configs_already_executed(configs, incremental)
    _LOG.info("Removed %d configs since already executed", num_skipped)
    _LOG.info("Need to execute %d configs", len(configs))
    # Handle --dry_run, if needed.
    if args.dry_run:
        _LOG.warning(
            "The following configs will not be executed due to passing --dry_run:"
        )
        for i, config in enumerate(configs):
            print("config_%s:\n %s", i, config)
        sys.exit(0)
    return configs