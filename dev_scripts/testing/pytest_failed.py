#!/usr/bin/env python

"""
Print the failing tests from the last `pytest` run in all the (super and
sub-module) repos.

> last_failures.py
...
amp/dev_scripts/test/test_amp_dev_scripts.py
amp/documentation/scripts/test/test_all.py
"""

import argparse
import json
import logging
import os

import helpers.dbg as dbg
import helpers.git as git
import helpers.io_ as io_
import helpers.parser as prsr
import helpers.printing as prnt

_LOG = logging.getLogger(__name__)


def _get_failed_tests(file_name):
    tests = []
    # If path exists, parse the content.
    if os.path.exists(file_name):
        # {
        # "vendors/test/test_vendors.py::Test_gp::test1": true,
        # "vendors/test/test_vendors.py::Test_kibot_utils1::...": true,
        # }
        txt = io_.from_file(file_name)
        vals = json.loads(txt)
        dbg.dassert_isinstance(vals, dict)
        tests = [k for k, v in vals.items() if v]
    return tests


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    prsr.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level, use_exec_path=False)
    #
    dir_names = [".", "amp"]
    for dir_name in dir_names:
        if os.path.exists(dir_name):
            # Print the symbolic name of the repo.
            repo_name = git.get_repo_symbolic_name_from_dirname(dir_name)
            _LOG.debug("\n%s", prnt.frame(repo_name))
            # Print the failed tests.
            file_name = os.path.join(dir_name, ".pytest_cache/v/cache/lastfailed")
            tests = _get_failed_tests(file_name)
            print("\n".join(tests))


if __name__ == "__main__":
    _main(_parse())