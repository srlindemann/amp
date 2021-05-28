#!/usr/bin/env python
r"""
Run a notebook given a config or a list of configs.

# Use example:
> run_notebook.py \
    --dst_dir nlp/test_results \
    --notebook nlp/notebooks/NLP_RP_pipeline.ipynb \
    --function "nlp.build_configs.build_PTask1088_configs()" \
    --num_threads 2
"""
import argparse
import logging
import os
import sys
from typing import List, Optional

import joblib
import tqdm

import core.config as cfg
import core.config_builders as cfgb
import core.dataflow_model.utils as cdtfut
import helpers.dbg as dbg
import helpers.io_ as io_
import helpers.parser as prsr
import helpers.pickle_ as hpickle
import helpers.printing as printing
import helpers.system_interaction as si


_LOG = logging.getLogger(__name__)


# #############################################################################


def _run_notebook(
    i: int,
    notebook_file: str,
    dst_dir: str,
    config: cfg.Config,
    config_builder: str,
    num_attempts: int,
    abort_on_error: bool,
    publish: bool,
) -> Optional[int]:
    """
    Run a notebook for a specific `Config`.

    The `config_builder` is passed inside the notebook to generate a list
    of all configs to be run as part of a series of experiments, but only the
    `i`-th config is run inside a particular notebook.

    :param i: index of config to select in a list of configs
    :param notebook_file: path to file with experiment template
    :param dst_dir: path to directory to store results
    :param config: config for the experiment
    :param config_builder: function used to generate all the configs
    :param num_attempts: maximum number of times to attempt running the
        notebook
    :param abort_on_error: if `True`, raise an error
    :param publish: publish notebook if `True`
    :return: if notebook is skipped ("success.txt" file already exists), return
        `None`; otherwise, return `rc`
    """
    dbg.dassert_file_exists(notebook_file)
    dbg.dassert_isinstance(config, cfg.Config)
    dbg.dassert_dir_exists(dst_dir)

    # Create subdirectory structure for experiment results.
    result_subdir = "result_%s" % i
    experiment_result_dir = os.path.join(dst_dir, result_subdir)
    _LOG.info("experiment_result_dir=%s", experiment_result_dir)
    # If there is already a success file in the dir, skip the experiment.
    file_name = os.path.join(experiment_result_dir, "success.txt")
    if os.path.exists(file_name):
        _LOG.warning("Found file '%s': skipping run %d", file_name, i)
        return
    io_.create_dir(experiment_result_dir, incremental=True)

    # Inject the experiment result dir inside the config.
    # TODO(gp): This operation is also performed on the notebook side
    #  in `get_config_from_env()`. Find a better way to achieve this.
    config = cfgb.set_experiment_result_dir(experiment_result_dir,
                                            config)
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

    # Execute notebook.
    _LOG.info("Executing notebook %d", i)
    # Prepare the destination file.
    dst_file = os.path.join(
        experiment_result_dir,
        os.path.basename(notebook_file).replace(".ipynb", ".%s.ipynb" % i),
    )
    _LOG.info("dst_file=%s", dst_file)
    dst_file = os.path.abspath(dst_file)
    # Export config function and its `id` to the notebook.
    cmd = (
        f'export __CONFIG_BUILDER__="{config_builder}"; '
        + f'export __CONFIG_IDX__="{i}"; '
        + f'export __CONFIG_DST_DIR__="{experiment_result_dir}"'
    )
    cmd += (
        f"; jupyter nbconvert {notebook_file} "
        + " --execute"
        + " --to notebook"
        + f" --output {dst_file}"
        + " --ExecutePreprocessor.kernel_name=python"
        +
        # https://github.com/ContinuumIO/anaconda-issues/issues/877
        " --ExecutePreprocessor.timeout=-1"
    )
    #
    log_file = os.path.join(experiment_result_dir, "run_notebook.%s.log" % i)
    log_file = os.path.abspath(os.path.abspath(log_file))
    # Try running the notebook up to `num_attempts` times.
    dbg.dassert_lte(1, num_attempts)
    rc = -1
    for n in range(1, num_attempts + 1):
        if n > 1:
            _LOG.warning(
                "Attempting to re-run the notebook for the %d / %d time after "
                "rc='%s'",
                n - 1,
                num_attempts,
                rc,
            )
        # Possibly abort on the last attempt.
        is_last_attempt = n == num_attempts
        abort_on_error_curr = is_last_attempt and abort_on_error
        rc = si.system(
            cmd, output_file=log_file, abort_on_error=abort_on_error_curr
        )
        if rc == 0:
            break
    if not abort_on_error and rc != 0:
        _LOG.error(
            "Execution failed for experiment `%s`. "
            "Continuing execution for next experiments.",
            i,
        )
    # Convert to html and publish.
    if publish:
        _LOG.info("Converting notebook %s", i)
        log_file = log_file.replace(".log", ".html.log")
        html_subdir_name = os.path.join(os.path.basename(dst_dir), result_subdir)
        cmd = (
            "python amp/dev_scripts/notebooks/publish_notebook.py"
            + f" --file {dst_file}"
            + f" --subdir {html_subdir_name}"
            + " --action publish"
        )
        si.system(cmd, output_file=log_file)
    # Publish an empty file to indicate a successful finish.
    file_name = os.path.join(experiment_result_dir, "success.txt")
    _LOG.info("file_name=%s", file_name)
    io_.to_file(file_name, "")
    return rc


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Add common experiment options.
    parser = cdtfut.add_experiment_arg(parser)
    # Add notebook options.
    parser.add_argument(
        "--notebook",
        action="store",
        required=True,
        help="File storing the notebook to iterate over",
    )
    parser.add_argument(
        "--publish_notebook",
        action="store_true",
        help="Publish each notebook after it executes",
    )
    prsr.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    # TODO(*): Stop modifying the "meta" level of configs:
    #     https://github.com/.../.../issues/6487
    _LOG.warning("Modifying 'meta' level of the configs.")
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    dst_dir = os.path.abspath(args.dst_dir)
    io_.create_dir(dst_dir, incremental=not args.no_incremental)
    config_builder = args.function
    # Build the configs from the builder.
    configs = get_configs_from_builder(config_builder)
    # Patch the configs.
    configs = cfgb.add_result_dir(dst_dir, configs)
    configs = cfgb.add_config_idx(configs)
    # Select the configs.
    configs = ccbuilders.select_config(
        configs, args.index, args.start_from_index,
    )
    #
    if dry_run:
        _LOG.warning(
            "The following configs will not be executed due to passing --dry_run:"
        )
        for i, config in enumerate(configs):
            print("config_%s:\n %s", i, config)
        sys.exit(0)
    # Get the notebook file.
    notebook_file = args.notebook
    notebook_file = os.path.abspath(notebook_file)
    dbg.dassert_exists(notebook_file)
    # Parse command-line options.
    num_attempts = args.num_attempts
    abort_on_error = not args.skip_on_error
    publish = args.publish_notebook
    #
    num_threads = args.num_threads
    if num_threads == "serial":
        rcs = []
        for config in tqdm.tqdm(configs):
            i = int(config[("meta", "id")])
            _LOG.debug("\n%s", printing.frame("Config %s" % i))
            #
            rc = _run_notebook(
                i,
                notebook_file,
                dst_dir,
                config,
                config_builder,
                num_attempts,
                abort_on_error,
                publish,
            )
            rcs.append(rc)
    else:
        num_threads = int(num_threads)
        # -1 is interpreted by joblib like for all cores.
        _LOG.info("Using %d threads", num_threads)
        rcs = joblib.Parallel(n_jobs=num_threads, verbose=50)(
            joblib.delayed(_run_notebook)(
                int(config[("meta", "id")]),
                notebook_file,
                dst_dir,
                config,
                config_builder,
                num_attempts,
                abort_on_error,
                publish,
            )
            for config in configs
        )
    # Report failing experiments.
    experiment_ids = [int(config[("meta", "id")]) for config in configs]
    failed_experiment_ids = [
        i for i, rc in zip(experiment_ids, rcs) if rc is not None and rc != 0
    ]
    if failed_experiment_ids:
        _LOG.error("Failed experiments are: %s", failed_experiment_ids)


if __name__ == "__main__":
    _main(_parse())
