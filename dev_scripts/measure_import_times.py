#!/usr/bin/env python

"""
Calculate execution time of imports.
"""

import argparse
import re
from typing import List, Tuple
from tqdm import tqdm
import logging

import helpers.dbg as dbg
import helpers.io_ as io_
import helpers.parser as prsr
import helpers.system_interaction as si
from helpers.timer import Timer


_LOG = logging.getLogger(__name__)


class ImportTimeChecker:
    """
    Class for measure execution time for imports
    """

    def __init__(self, dir_name):
        """
        :param dir_name: directory name to search python files
        """
        self.dir_name = dir_name
        # Store all the modules with execution time (module: elapsed_time).
        self.checked_modules = {}
        # instance of class for measure elapsed time.
        # Pattern for finding modules in file.
        self.match_pattern = '(?m)^\s*(?:from|import)\s+([a-zA-Z0-9_.]+(?:\s*,\s*\w+)*)'

    def find_modules_from_file(self, file_name: str) -> List[str]:
        """
        Search modules in a given file
        :param file_name: filename where need to search modules
        :return: list of all found module name
        """
        _LOG.debug("file_name=%s", file_name)
        text = io_.from_file(file_name)
        modules = re.findall(self.match_pattern, text)
        _LOG.debug("  -> modules=%s", modules)
        return modules

    def measure_time(self, module: str) -> float:
        """
        Measures execution time for a given module and save in self.checked_modules
        :param module: module name
        :return: elapsed time to execute import
        """
        if module not in self.checked_modules:
            # execute python "import module" to measure.
            timer = Timer()
            si.system(f'python -c "import {module}"')
            timer.stop()
            elapsed_time = round(timer.get_elapsed(), 3)
            self.checked_modules[module] = elapsed_time
        return self.checked_modules[module]

    def measure_time_for_all_modules(self) -> None:
        """
        Traverse files and directory and find all modules and measure execution time
        :return: None
        """
        file_names = io_.find_files(self.dir_name, '*.py')
        modules = set()
        for file_name in file_names:
            _LOG.debug('filename: %s', file_name)
            modules_tmp = self.find_modules_from_file(file_name)
            modules.update(set(modules_tmp))
        #
        modules = sorted(list(modules))
        _LOG.info("Found %d modules", len(modules))
        for module in tqdm(modules):
            self.measure_time(module)

    def _sort_by_time(self) -> None:
        """
        Sort time in ascending order in self.checked_modules
        :return: None
        """
        output = sorted(self.checked_modules.items(), key=lambda x: x[1])
        self.checked_modules = {module: time for module, time in output}

    def print_modules_time(self, sort=False) -> None:
        """
        Print all measured modules
        :param sort: defines whether sort output or not
        :return: None
        """
        if sort:
            self._sort_by_time()
        for module, elapsed_time in self.checked_modules.items():
            print(f'{module} {elapsed_time} s')

    def get_total_time(self) -> float:
        """
        Calculates total time spend for importing
        :return: float
        """
        total_time = 0
        for time in self.checked_modules.values():
            total_time += time
        return total_time

    def get_list(self) -> List[Tuple[str, float]]:
        """
        Return self.checled_modules in list format
        :return: list
        """
        output = [(module, elapsed_time) for module, elapsed_time
                  in self.checked_modules.items()]
        return output


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-d', '--directory',
                        type=str,
                        help='search directory (default: current directory)',
                        default='.')
    prsr.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    checker = ImportTimeChecker(args.directory)
    checker.measure_time_for_all_modules()
    checker.print_modules_time(sort=True)
    #
    total_time = checker.get_total_time()
    print(f'Total time for importing: {total_time}')


if __name__ == "__main__":
    _main(_parse())
