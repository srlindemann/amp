import enum
import os
from typing import List, Tuple

import pandas as pd

import vendors2.kibot.metadata.config as config
import vendors2.kibot.metadata.types as types


class ParsingState(enum.Enum):
    # started parsing the file, no keywords encountered
    Started = 0
    # A listed section header was found
    ListedSectionStarted = 1
    # The column headers were skipped
    HeaderSkipped = 2
    # A delisted section header was found
    DelistedSectionStarted = 3


class TickerListsLoader:
    def get(self, ticker_list: str, listed: bool = True) -> List[types.Ticker]:
        s3_path = os.path.join(
            config.S3_PREFIX, config.TICKER_LISTS_SUB_DIR, f"{ticker_list}.txt",
        )

        lines = self._get_lines(s3_path=s3_path)
        listed_tickers, delisted_tickers = self._parse_lines(lines=lines)
        return listed_tickers if listed else delisted_tickers

    @staticmethod
    def _get_lines(s3_path: str) -> List[str]:
        return [
            line[0] for line in pd.read_csv(s3_path, sep="/t").values.tolist()
        ]

    def _parse_lines(
        self, lines: List[str]
    ) -> Tuple[List[types.Ticker], List[types.Ticker]]:
        """Get a list of listed & delisted tickers from lines."""
        listed_tickers: List[types.Ticker] = []
        delisted_tickers: List[types.Ticker] = []

        state = ParsingState.Started

        for line in lines:
            if not line.strip():
                # Skip empty lines.
                continue

            if state == ParsingState.ListedSectionStarted:
                state = ParsingState.HeaderSkipped
                continue

            if line.strip() == "Listed:":
                state = ParsingState.ListedSectionStarted
                continue
            if line.strip() == "Delisted:":
                state = ParsingState.DelistedSectionStarted
                continue

            if state == ParsingState.HeaderSkipped:
                listed_tickers.append(self._get_ticker_from_line(line))
            elif state == ParsingState.DelistedSectionStarted:
                delisted_tickers.append(self._get_ticker_from_line(line))

        return listed_tickers, delisted_tickers

    @staticmethod
    def _get_ticker_from_line(line: str) -> types.Ticker:
        """Get a ticker from a line.

        Example line:
        #       Symbol  StartDate       Size(MB)    Description     Exchange        Industry        Sector 1
        AA      4/27/2007       68      "Alcoa Corporation"     NYSE    "Aluminum"      "Basic Industries"
        """
        args = line.split("\t")
        # Remove new line from last element. Note: if we strip before splitting, the tab
        # delimiters would be removed as well if a column is empty.
        args[-1] = args[-1].strip()
        # Skip index col.
        args = args[1:]
        ret = types.Ticker(*args)
        return ret
