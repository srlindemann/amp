#!/usr/bin/env python

"""
Qualify a branch for being merged to master.

> git_merge_branch.py
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


def _process_repo(
    actions: List[str],
    dir_name: str,
    dst_branch: str,
    test_list: str,
    abort_on_error: bool,
    quick: bool,
    autostash: bool,
) -> Tuple[bool, List[str], List[str]]:
    """
    Qualify a branch stored in `dir_name`, running linter and unit tests.

    :param dst_branch: directory containing the branch
    :param test_list: test list to run (e.g., fast, slow)
    :param quick: run a single test instead of the entire regression test
    """
    dbg.dassert_exists(dir_name)
    _LOG.debug("\n%s", prnt.frame("Processing: %s" % dir_name, char1=">"))
    is_ok = True
    output: List[str] = []
    # TODO(gp): `git pull` ensures that the Git client is clean. We can have a
    #  better check, if needed.
    cd_cmd = "cd %s && " % dir_name
    #
    action = "git_fetch_dst_branch"
    to_execute, actions = prsr.mark_action(action, actions)
    if to_execute:
        branch_name = git.get_branch_name(dir_name)
        _LOG.debug("branch_name='%s'", branch_name)
        if branch_name != "master":
            cmd = "git fetch origin %s:%s" % (dst_branch, dst_branch)
            si.system(cd_cmd + cmd)
    #
    action = "git_pull"
    to_execute, actions = prsr.mark_action(action, actions)
    if to_execute:
        cmd = "git pull"
        if autostash:
            _LOG.warning("Using `git pull --autostash`")
            cmd += " --autostash"
        si.system(cd_cmd + cmd)
    #
    action = "git_merge_master"
    to_execute, actions = prsr.mark_action(action, actions)
    if to_execute:
        cmd = "git merge master --commit --no-edit"
        si.system(cd_cmd + cmd)
    #
    action = "linter"
    to_execute, actions = prsr.mark_action(action, actions)
    if to_execute:
        output.append(prnt.frame("%s: linter log" % dir_name))
        # Get the files that were modified in this branch.
        file_names = git.get_modified_files_in_branch(dir_name, dst_branch)
        msg = "Files modified: %d\n%s" % (
            len(file_names),
            prnt.space("\n".join(file_names)),
        )
        _LOG.debug(msg)
        output.append(msg)
        if not file_names:
            _LOG.warning("No files different in %s", dst_branch)
        else:
            linter_log = "linter_log.txt"
            if dir_name != ".":
                linter_log = "%s.%s" % (dir_name, linter_log)
            linter_log = os.path.abspath(linter_log)
            cmd = "linter.py -b --linter_log %s" % linter_log
            rc = si.system(
                cd_cmd + cmd, suppress_output=False, abort_on_error=False,
            )
            _LOG.info("linter output=\n%s", linter_log)
            if rc != 0:
                _LOG.warning("There are lints. Please take time to fix them")
            # Read output from the linter.
            txt = io_.from_file(linter_log)
            output.append(txt)
    #
    action = "run_tests"
    to_execute, actions = prsr.mark_action(action, actions)
    if to_execute:
        output.append(prnt.frame("%s: unit tests" % dir_name))
        if quick:
            _LOG.warning("Running a quick unit test")
            cmd = "pytest -k Test_dassert1"
        else:
            # Delete pytest.
            si.pytest_clean_artifacts(".")
            # Run the tests.
            cmd = "run_tests.py --test %s --num_cpus -1" % test_list
        output.append("cmd line='%s'" % cmd)
        rc = si.system(
            cd_cmd + cmd, suppress_output=False, abort_on_error=abort_on_error
        )
        output.append("  rc=%s" % rc)
        if not abort_on_error and rc != 0:
            output.append(
                "WARNING: unit tests failed: skipping as per user request"
            )
        # Update the function rc.
        is_ok &= rc == 0
    return is_ok, output, actions


def _merge_all_branches(
    actions: List[str], dst_branch: str, target_dirs: List[str]
) -> List[str]:
    action = "merge"
    to_execute, actions = prsr.mark_action(action, actions)
    if to_execute:
        # We need to merge the submodules first.
        for dir_name in reversed(target_dirs):
            branch_name = git.get_branch_name(dir_name)
            if branch_name == dst_branch:
                _LOG.warning(
                    "Skipping merging in dir '%s' since it's already " "'%s'",
                    dir_name,
                    dst_branch,
                )
            else:
                _LOG.warning(
                    "Merging '%s' -> '%s' in dir '%s'",
                    branch_name,
                    dst_branch,
                    dir_name,
                )
                cd_cmd = "cd %s && " % dir_name
                cmd_arr = []
                cmd_arr.append("git checkout master")
                cmd_arr.append("git pull")
                msg = "Merging %s -> %s" % (branch_name, dst_branch)
                cmd_arr.append(
                    "git merge %s -m '%s' --no-ff --commit" % (branch_name, msg)
                )
                cmd_arr.append("git push")
                # TODO(gp): Delete branch.
                cmd = " && ".join(cmd_arr)
                si.system(cd_cmd + cmd)
    return actions  # type: ignore


# #############################################################################

_VALID_ACTIONS = [
    "git_fetch_dst_branch",
    "git_pull",
    "git_merge_master",
    "linter",
    "run_tests",
    "merge",
]


_DEFAULT_ACTIONS = [
    "linter",
    "run_tests",
]


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    output = []
    output.append("cmd=%s" % dbg.get_command_line())
    # Print actions.
    actions = prsr.select_actions(args, _VALID_ACTIONS, _DEFAULT_ACTIONS)
    output.append("actions=%s" % actions)
    add_frame = True
    actions_as_str = prsr.actions_to_string(actions, _VALID_ACTIONS, add_frame)
    _LOG.info("\n%s", actions_as_str)
    # Find the target repos.
    # Note that the repos should be in reversed topological order, i.e., the
    # first one is the supermodule.
    target_dirs = ["."]
    # TODO(gp): What to do with infra?
    dir_name = "amp"
    if os.path.exists(dir_name):
        target_dirs.append(dir_name)
    msg = "target_dirs=%s" % target_dirs
    _LOG.info(msg)
    output.append(msg)
    #
    is_ok = True
    for dir_name in target_dirs:
        actions_tmp = actions[:]
        abort_on_error = not args.continue_on_error
        is_ok_tmp, output_tmp, actions_tmp = _process_repo(
            actions_tmp,
            dir_name,
            args.dst_branch,
            args.test_list,
            abort_on_error,
            args.quick,
            args.autostash,
        )
        is_ok &= is_ok_tmp
        output.extend(output_tmp)
        # Update the actions on the last loop.
        if dir_name == target_dirs[-1]:
            actions = actions_tmp
    # Report the output.
    _LOG.info("Summary file saved into '%s'", args.summary_file)
    output_as_txt = "\n".join(output)
    io_.to_file(args.summary_file, output_as_txt)
    # Print output.
    txt = io_.from_file(args.summary_file)
    msg = "--> Please attach this to your PR <--"
    print(prnt.frame(msg, char1="-").rstrip("\n"))
    print(txt + "\n")
    print(prnt.line(char="/").rstrip("\n"))
    # Merge.
    if not is_ok:
        _LOG.error(
            "Can't merge since some repo didn't pass the qualification process"
        )
    else:
        actions = _merge_all_branches(actions, args.dst_branch, target_dirs)
    # Forward amp.
    # TODO(gp): Implement this.
    # Check that everything was executed.
    if actions:
        _LOG.error("actions=%s were not processed", str(actions))


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dst_branch",
        action="store",
        default="master",
        help="Branch to merge into, typically " "master",
    )
    prsr.add_action_arg(parser, _VALID_ACTIONS, _DEFAULT_ACTIONS)
    parser.add_argument(
        "--autostash", action="store_true", help="Use --autostash in git pull"
    )
    parser.add_argument("--test_list", action="store", default="slow")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument(
        "--continue_on_error",
        action="store_true",
        help="Do not abort on the first error",
    )
    parser.add_argument(
        "--summary_file",
        action="store",
        default="./pr_summary.txt",
        help="File with the summary of the merge",
    )
    parser.add_argument("--merge_if_successful", action="store_true")
    prsr.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    _main(_parse())