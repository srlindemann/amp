import logging

try:
    import ib_insync
except ModuleNotFoundError:
    print("Can't find ib_insync")
import pandas as pd
import pytest

import instrument_master.common.db.init as icdini
import instrument_master.ib.data.extract.gateway.test.utils as iidegt
import instrument_master.ib.data.extract.gateway.utils as iidegu

_LOG = logging.getLogger(__name__)


@pytest.mark.skipif(
    not icdini.is_inside_im_container(),
    reason="Testable only inside IB container",
)
class Test_get_historical_data(iidegt.IbExtractionTest):
    def test_get_end_timestamp1(self) -> None:
        """
        Test get_end_timestamp() for ES in and outside regular trading hours
        (RTH).
        """
        contract = ib_insync.ContFuture("ES", "GLOBEX", currency="USD")
        what_to_show = "TRADES"
        use_rth = True
        ts1 = iidegu.get_end_timestamp(self.ib, contract, what_to_show, use_rth)
        _LOG.debug("ts1=%s", ts1)
        #
        use_rth = False
        ts2 = iidegu.get_end_timestamp(self.ib, contract, what_to_show, use_rth)
        _LOG.debug("ts2=%s", ts2)

    def test_req_historical_data1(self) -> None:
        """
        Test req_historical_data() on a single day in trading hours.

        Requesting data for a day ending at 18:00 gets the entire
        trading day.
        """
        # 2021-02-18 is a Thursday and it's full day.
        end_ts = pd.Timestamp("2021-02-18 18:00:00")
        use_rth = True
        short_signature, long_signature = self._req_historical_data_helper(
            end_ts, use_rth
        )
        exp = """
        signature=len=9 [2021-02-18 09:30:00-05:00, 2021-02-18 16:30:00-05:00]
        min_max_df=
                         min       max
        2021-02-18  09:30:00  16:30:00
        """
        self.assert_equal(short_signature, exp, fuzzy_match=True)
        self.check_string(long_signature)

    def test_req_historical_data2(self) -> None:
        """
        Test req_historical_data() on a single day outside trading hours.

        Requesting data for a day ending at 18:00 gets data for a 24 hr
        period.
        """
        # 2021-02-18 is a Thursday and it's full day.
        end_ts = pd.Timestamp("2021-02-18 18:00:00")
        use_rth = False
        short_signature, long_signature = self._req_historical_data_helper(
            end_ts, use_rth
        )
        exp = """
        signature=len=24 [2021-02-17 18:00:00-05:00, 2021-02-18 16:30:00-05:00]
        min_max_df=
                         min       max
        2021-02-17  18:00:00  23:00:00
        2021-02-18  00:00:00  16:30:00
        """
        self.assert_equal(short_signature, exp, fuzzy_match=True)
        self.check_string(long_signature)

    def test_req_historical_data3(self) -> None:
        """
        Test req_historical_data() on a single day outside trading hours.

        Requesting data for a day ending at midnight gets data after
        18:00.
        """
        # 2021-02-18 is a Thursday and it's full day.
        end_ts = pd.Timestamp("2021-02-18 00:00:00")
        use_rth = False
        short_signature, long_signature = self._req_historical_data_helper(
            end_ts, use_rth
        )
        exp = """
        signature=len=6 [2021-02-17 18:00:00-05:00, 2021-02-17 23:00:00-05:00]
        min_max_df=
                         min       max
        2021-02-17  18:00:00  23:00:00
        """
        self.assert_equal(short_signature, exp, fuzzy_match=True)
        self.check_string(long_signature)

    def test_req_historical_data4(self) -> None:
        """
        Test req_historical_data() on a single day outside trading hours.

        Requesting data for a day ending at noon gets data after 18:00
        of the day before.
        """
        # 2021-02-18 is a Thursday and it's full day.
        end_ts = pd.Timestamp("2021-02-18 12:00:00")
        use_rth = False
        short_signature, long_signature = self._req_historical_data_helper(
            end_ts, use_rth
        )
        exp = """
        signature=len=18 [2021-02-17 18:00:00-05:00, 2021-02-18 11:00:00-05:00]
        min_max_df=
                         min       max
        2021-02-17  18:00:00  23:00:00
        2021-02-18  00:00:00  11:00:00
        """
        self.assert_equal(short_signature, exp, fuzzy_match=True)
        self.check_string(long_signature)

    def test_req_historical_data5(self) -> None:
        """
        Test req_historical_data() on a non-existing day.
        """
        # 2018-02-29 doesn't exist, since 2018 is not a leap year.
        end_ts = pd.Timestamp("2018-01-29 14:00:00-05:00")
        use_rth = False
        short_signature, long_signature = self._req_historical_data_helper(
            end_ts, use_rth
        )
        exp = """
        """
        self.assert_equal(short_signature, exp, fuzzy_match=True)
        self.check_string(long_signature)

    def test_req_historical_data6(self) -> None:
        """
        Test req_historical_data() on a day when the market is closed.
        """
        # 2018-02-19 is a Thursday and it's president day.
        end_ts = pd.Timestamp("2018-02-19 14:00:00-05:00")
        use_rth = False
        short_signature, long_signature = self._req_historical_data_helper(
            end_ts, use_rth
        )
        exp = """
        """
        self.assert_equal(short_signature, exp, fuzzy_match=True)
        self.check_string(long_signature)
