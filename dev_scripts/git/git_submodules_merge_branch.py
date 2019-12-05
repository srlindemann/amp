#!/usr/bin/env python

"""
Run 
"""

import argparse
import logging
import os
from typing import List

import helpers.dbg as dbg
import helpers.git as git
import helpers.io_ as io_
import helpers.parser as prsr
import helpers.printing as prnt
import helpers.system_interaction as si

_LOG = logging.getLogger(__name__)

# #############################################################################


def _get_changed_files(dst_branch: str) -> List[str]:
    cmd = "git diff --name-only %s..." % dst_branch
    _, output = si.system_to_string(cmd)
    file_names = output.split("\n")
    return file_names


def _qualify_branch(tag: str, dst_branch: str, test_list: str) -> List[str]:
    output = []
    # - Linter.
    output.append(prnt.frame("%s: linter log" % tag))
    file_names = _get_changed_files(dst_branch)
    output.append("Files modified:\n%s", prnt.prepend(file_names))
    linter_log = "./%s.linter_log.txt" % tag
    linter_log = os.path.abspath(linter_log)
    cmd = "linter.py -f %s" % " ".join(file_names)
    si.system(cmd, suppress_output=False)
    # Read output from the linter.
    txt = io_.from_file(linter_log)
    output.append(txt)
    # - Run tests.
    if False:
        output.append(prnt.frame("%s: tests" % tag))
        cmd = "run_tests.py --test %s --num_cpus -1" % test_list
        output.append("cmd=%s" % cmd)
        si.system(cmd, suppress_output=False)
    #
    return output


# #############################################################################


def _parse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--src_branch",
        action="store",
        default=None,
        help="Name of the branch to merge. No value means use "
        "the branch we are currently in",
    )
    parser.add_argument(
        "--dst_branch",
        action="store",
        default="master",
        help="Branch to merge into, typically " "master",
    )
    parser.add_argument("--test_list", action="store", default="slow")
    parser.add_argument("--merge_if_successful", action="store_true")
    parser.add_argument(
        "--summary_file", action="store", default="./summary_file.txt"
    )
    prsr.add_verbosity_arg(parser)
    return parser


def _main(parser):
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    output = []
    # Update the src branch.
    if args.src_branch is not None:
        cmd = "git checkout %s" % args.src_branch
        si.system(cmd)
    # If this is master, then raise an error.
    branch_name = git.get_branch_name()
    _LOG.info("Current branch_name: %s", branch_name)
    msg = "%s -> %s" % (branch_name, args.dst_branch)
    output.append(msg)
    dbg.dassert_ne(branch_name, "master", "You can't merge from master")
    # TODO(gp): Stash and clean.
    # TODO(gp): Make sure the Git client is empty.
    cmd = "git pull"
    si.system(cmd)
    # Update the dst branch.
    cmd = "git fetch origin %s:%s" % (args.dst_branch, args.dst_branch)
    si.system(cmd)
    #
    repo_sym_name = git.get_repo_symbolic_name(super_module=True)
    _LOG.info("repo_sym_name=%s", repo_sym_name)
    # Qualify current repo.
    output_tmp = _qualify_branch("curr", args.dst_branch, args.test_list)
    output.extend(output_tmp)
    # Qualify amp repo.
    if os.path.exists("amp"):
        output_tmp = _qualify_branch("amp", args.dst_branch, args.test_list)
        output.extend(output_tmp)


if __name__ == "__main__":
    _main(_parse())
