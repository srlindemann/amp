import logging
import os.path
from typing import List, Match, Optional, Tuple

import helpers.traceback_helper as htrace
import helpers.unit_test as hut

import helpers.dbg as dbg
import helpers.system_interaction as hsinte


_LOG = logging.getLogger(__name__)


class Test_Traceback1(hut.TestCase):
    def test_parse1(self) -> None:
        txt = """

        TEST
Traceback
    TEST
Traceback (most recent call last):
  File "/app/amp/test/test_lib_tasks.py", line 27, in test_get_gh_issue_title2
    act = ltasks._get_gh_issue_title(issue_id, repo)
  File "/app/amp/lib_tasks.py", line 1265, in _get_gh_issue_title
    task_prefix = git.get_task_prefix_from_repo_short_name(repo_short_name)
  File "/app/amp/helpers/git.py", line 397, in get_task_prefix_from_repo_short_name
    if repo_short_name == "amp":
NameError: name 'repo_short_name' is not defined
    TEST TEST TEST
"""
        purify_from_client = True
        # pylint: disable=line-too-long
        exp_cfile = [
            (
                "helpers/test/test_lib_tasks.py",
                27,
                "test_get_gh_issue_title2:act = ltasks._get_gh_issue_title(issue_id, repo)",
            ),
            (
                "lib_tasks.py",
                1265,
                "_get_gh_issue_title:task_prefix = git.get_task_prefix_from_repo_short_name(repo_short_name)",
            ),
            (
                "helpers/git.py",
                397,
                'get_task_prefix_from_repo_short_name:if repo_short_name == "amp":',
            ),
        ]
        exp_cfile = htrace.cfile_to_str(exp_cfile)
        # pylint: enable=line-too-long
        exp_traceback = """
Traceback (most recent call last):
  File "/app/amp/test/test_lib_tasks.py", line 27, in test_get_gh_issue_title2
    act = ltasks._get_gh_issue_title(issue_id, repo)
  File "/app/amp/lib_tasks.py", line 1265, in _get_gh_issue_title
    task_prefix = git.get_task_prefix_from_repo_short_name(repo_short_name)
  File "/app/amp/helpers/git.py", line 397, in get_task_prefix_from_repo_short_name
    if repo_short_name == "amp":
        """.rstrip().lstrip()
        self._parse_traceback_helper(
                                txt,
                                purify_from_client,
                                exp_cfile,
                                exp_traceback)

    def test_parse_empty_traceback1(self) -> None:
        """
        Parse an empty traceback file.
        """
        txt = """

        TEST
Traceback
    TEST TEST TEST
"""
        purify_from_client = True
        exp_cfile = []
        exp_cfile = htrace.cfile_to_str(exp_cfile)
        exp_traceback = "None"
        self._parse_traceback_helper(
            txt,
            purify_from_client,
            exp_cfile,
            exp_traceback)

    def test_parse2(self) -> None:
        """
        Parse a traceback file with both files from Docker and local files.
        """
        txt = """
Traceback (most recent call last):
  File "./amp/core/dataflow_model/run_pipeline.py", line 146, in <module>
    _main(_parse())
  File "./amp/core/dataflow_model/run_pipeline.py", line 105, in _main
    configs = cdtfut.get_configs_from_command_line(args)
  File "/app/amp/core/dataflow_model/utils.py", line 228, in get_configs_from_command_line
    "config_builder": args.config_builder,
"""
        purify_from_client = True
        exp_cfile = [
            ("amp/core/dataflow_model/run_pipeline.py", 146, "<module>:_main(_parse())"),
            ("amp/core/dataflow_model/run_pipeline.py", 105, "_main:configs = cdtfut.get_configs_from_command_line(args)"),
            ("amp/core/dataflow_model/utils.py", 228, 'get_configs_from_command_line:"config_builder": args.config_builder,')
            ]
        exp_cfile = htrace.cfile_to_str(exp_cfile)
        exp_traceback = txt
        self._parse_traceback_helper(
            txt,
            purify_from_client,
            exp_cfile,
            exp_traceback)

    def _parse_traceback_helper(self,
                           txt: str,
                           purify_from_client: bool,
                           exp_cfile: str,
                           exp_traceback: str) -> None:
        dbg.dassert_isinstance(txt, str)
        dbg.dassert_isinstance(exp_cfile, str)
        dbg.dassert_isinstance(exp_traceback, str)
        # Run the function under test.
        act_cfile, act_traceback = htrace.parse_traceback(txt,
                                                          purify_from_client=purify_from_client)
        _LOG.debug("act_cfile=\n%s", act_cfile)
        # Compare cfile.
        act_cfile = htrace.cfile_to_str(act_cfile)
        act_cfile = hut.purify_amp_references(act_cfile)
        act_cfile = hut.purify_app_references(act_cfile)
        #
        exp_cfile = hut.purify_amp_references(exp_cfile)
        exp_cfile = hut.purify_app_references(exp_cfile)
        self.assert_equal(act_cfile, exp_cfile, fuzzy_match=True)
        # Compare traceback.
        # Handle `None`.
        act_traceback = str(act_traceback)
        self.assert_equal(act_traceback, exp_traceback, fuzzy_match=True)

    # @staticmethod
    # def _purify_from_client(cfile: htrace.CFILE_ROW) -> htrace.CFILE_ROW:
    #     """
    #     Remove the references to '/app/amp/' and '/app/` from a CFILE_ROW.
    #     """
    #     cfile_tmp = []
    #     for cfile_row in cfile:
    #         file_name, line_num, text = cfile_row
    #         file_name = os.path.normpath(file_name)
    #         for prefix in ["/app/amp/", "/app/", "amp/"]:
    #             if file_name.startswith(prefix):
    #                 # TODO(gp): Use Python3.9 removeprefix.
    #                 file_name = file_name.replace(prefix, "")
    #         cfile_row = (file_name, line_num, text)
    #         cfile_tmp.append(cfile_row)
    #     return cfile_tmp
