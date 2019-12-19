#!/usr/bin/env python

"""
Run all the tests needed to qualify a branch for PR.

Qualify a branch and commit.
"""

import argparse
import logging
import os
from typing import List, Tuple

import helpers.dbg as dbg
import helpers.git as git
import helpers.io_ as io_
import helpers.parser as prsr
import helpers.printing as prnt
import helpers.system_interaction as si

_LOG = logging.getLogger(__name__)

# #############################################################################


def _update_branch(
    actions: List[str], dst_branch: str, target_dirs: List[str], output: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Bring the repos in sync with master.
    """
    for dir_ in target_dirs:
        dbg.dassert_exists(dir_)
        # TODO(gp): Make sure that the client is clean.
        branch_name = git.get_branch_name(dir_)
        msg = "dir=%s: merging: %s -> %s" % (dir_, branch_name, dst_branch)
        _LOG.info(msg)
        output.append(msg)
        #
        action = "git_fetch_dst_branch"
        to_execute, actions = prsr.mark_action(action, actions)
        if to_execute:
            cmd = "git fetch origin %s:%s" % (dst_branch, dst_branch)
            si.system(cmd)
        #
        action = "git_pull"
        to_execute, actions = prsr.mark_action(action, actions)
        if to_execute:
            cmd = "cd %s && git pull" % dir_
            si.system(cmd)
        #
        action = "git_merge_master"
        to_execute, actions = prsr.mark_action(action, actions)
        if to_execute:
            cmd = "cd %s && git merge master --commit --no-edit" % dir_
            si.system(cmd)
    return output, actions


def _get_changed_files(dst_branch: str) -> List[str]:
    cmd = "git diff --name-only %s..." % dst_branch
    _, output = si.system_to_string(cmd)
    file_names = si.get_non_empty_lines(output)
    return file_names


def _qualify_branch(
    actions: List[str],
    dst_branch: str,
    target_dirs: List[str],
    test_list: str,
    quick: bool,
    output: List[str],
) -> Tuple[List[str], List[str]]:
    """
    Qualify a branch stored in directory, running linter and unit tests.

    :param dst_branch: directory containing the branch
    :param test_list: test list to run (e.g., fast, slow)
    :param quick: run a single test instead of the entire regression test
    """
    for dir_ in target_dirs:
        dbg.dassert_exists(dir_)
        # - Linter.
        action = "linter"
        to_execute, actions = prsr.mark_action(action, actions)
        if to_execute:
            output.append(prnt.frame("%s: linter log" % dir_))
            # Get the files that were modified in this branch.
            file_names = _get_changed_files(dst_branch)
            msg = "Files modified:\n%s" % prnt.space("\n".join(file_names))
            _LOG.debug(msg)
            output.append(msg)
            if not file_names:
                _LOG.warning("No files different in %s", dst_branch)
            else:
                linter_log = "./%s.linter_log.txt" % dir_
                linter_log = os.path.abspath(linter_log)
                cmd = "linter.py -f %s --linter_log %s" % (
                    " ".join(file_names),
                    linter_log,
                )
                si.system(cmd, suppress_output=False)
                # Read output from the linter.
                txt = io_.from_file(linter_log)
                output.append(txt)
        # - Run tests.
        action = "run_tests"
        to_execute, actions = prsr.mark_action(action, actions)
        if to_execute:
            output.append(prnt.frame("%s: unit tests" % dir_))
            if quick:
                cmd = "pytest -k Test_p1_submodules_sanity_check1"
            else:
                # TODO(gp): Delete cache.
                cmd = "run_tests.py --test %s --num_cpus -1" % test_list
            output.append("cmd line='%s'" % cmd)
            si.system(cmd, suppress_output=False)
    #
    return output, actions


# #############################################################################

_VALID_ACTIONS = [
    "git_fetch_dst_branch",
    "git_pull",
    "git_merge_master",
    "linter",
    "run_tests",
]


def _main(parser):
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    output = []
    # Print actions.
    actions = prsr.select_actions(args, _VALID_ACTIONS)
    output.append("actions=%s" % actions)
    add_frame = True
    actions_as_str = prsr.actions_to_string(actions, _VALID_ACTIONS, add_frame)
    _LOG.info("\n%s", actions_as_str)
    # Find the target.
    target_dirs = ["."]
    dir_name = "amp"
    if os.path.exists(dir_name):
        target_dirs.append(dir_name)
    msg = "target_dirs=%s" % target_dirs
    _LOG.info(msg)
    output.append(msg)
    # TODO(gp): Make sure the Git client is empty.
    # Update the dst branch.
    output, actions = _update_branch(
        actions, args.dst_branch, target_dirs, output
    )
    output, actions = _qualify_branch(
        actions, args.dst_branch, target_dirs, args.test_list, args.quick, output
    )
    # assert 0
    # # Refresh curr repo.
    # _refresh(".")
    # # Refresh amp repo, if needed.
    # if os.path.exists("amp"):
    #     _refresh("amp")
    # # Qualify amp repo.
    # if os.path.exists("amp"):
    #     tag = "amp"
    #     output_tmp = _qualify_branch(
    #         tag, args.dst_branch, args.test_list, args.quick
    #     )
    #     output.extend(output_tmp)
    # #
    # repo_sym_name = git.get_repo_symbolic_name(super_module=True)
    # _LOG.info("repo_sym_name=%s", repo_sym_name)
    # # Qualify current repo.
    # tag = "curr"
    # output_tmp = _qualify_branch(tag, args.dst_branch, args.test_list, args.quick)
    # output.extend(output_tmp)
    # # Qualify amp repo, if needed.
    # if os.path.exists("amp"):
    #     tag = "amp"
    #     output_tmp = _qualify_branch(
    #         tag, args.dst_branch, args.test_list, args.quick
    #     )
    #     output.extend(output_tmp)
    # Forward amp.
    if actions:
        _LOG.warning("actions=%s were not processed", str(actions))
    # Report the output.
    output_as_txt = "\n".join(output)
    io_.to_file(args.summary_file, output_as_txt)
    # print(output_as_txt)
    _LOG.info("Summary file saved into '%s'", args.summary_file)
    # Merge.
    # TODO(gp): Add merge step.


def _parse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dst_branch",
        action="store",
        default="master",
        help="Branch to merge into, typically " "master",
    )
    prsr.add_action_arg(parser, _VALID_ACTIONS)
    parser.add_argument("--test_list", action="store", default="slow")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--merge_if_successful", action="store_true")
    parser.add_argument(
        "--summary_file", action="store", default="./summary_file.txt"
    )
    prsr.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    _main(_parse())
