import logging

import numpy as np
import pandas as pd

import core.artificial_signal_generators as sig_gen
import core.statistics as stats
import helpers.unit_test as hut

_LOG = logging.getLogger(__name__)


class TestComputeFracZero1(hut.TestCase):
    @staticmethod
    def _get_df(seed: int) -> pd.DataFrame:
        nrows = 15
        ncols = 5
        num_nans = 15
        num_infs = 5
        num_zeros = 20
        #
        np.random.seed(seed=seed)
        mat = np.random.randn(nrows, ncols)
        mat.ravel()[np.random.choice(mat.size, num_nans, replace=False)] = np.nan
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = np.inf
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = -np.inf
        mat.ravel()[np.random.choice(mat.size, num_zeros, replace=False)] = 0
        #
        index = pd.date_range(start="01-04-2018", periods=nrows, freq="30T")
        df = pd.DataFrame(data=mat, index=index)
        return df

    def test1(self) -> None:
        data = [0.466667, 0.2, 0.13333, 0.2, 0.33333]
        index = [0, 1, 2, 3, 4]
        expected = pd.Series(data=data, index=index)
        actual = stats.compute_frac_zero(self._get_df(1))
        pd.testing.assert_series_equal(actual, expected, check_less_precise=3)

    def test2(self) -> None:
        data = [
            0.4,
            0.0,
            0.2,
            0.4,
            0.4,
            0.2,
            0.4,
            0.0,
            0.6,
            0.4,
            0.6,
            0.2,
            0.0,
            0.0,
            0.2,
        ]
        index = pd.date_range(start="1-04-2018", periods=15, freq="30T")
        expected = pd.Series(data=data, index=index)
        actual = stats.compute_frac_zero(self._get_df(1), axis=1)
        pd.testing.assert_series_equal(actual, expected, check_less_precise=3)

    def test3(self) -> None:
        # Equals 20 / 75 = num_zeros / num_points.
        expected = 0.266666
        actual = stats.compute_frac_zero(self._get_df(1), axis=None)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test4(self) -> None:
        series = self._get_df(1)[0]
        expected = 0.466667
        actual = stats.compute_frac_zero(series)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test5(self) -> None:
        series = self._get_df(1)[0]
        expected = 0.466667
        actual = stats.compute_frac_zero(series, axis=0)
        np.testing.assert_almost_equal(actual, expected, decimal=3)


class TestComputeFracNan1(hut.TestCase):
    @staticmethod
    def _get_df(seed: int) -> pd.DataFrame:
        nrows = 15
        ncols = 5
        num_nans = 15
        num_infs = 5
        num_zeros = 20
        #
        np.random.seed(seed=seed)
        mat = np.random.randn(nrows, ncols)
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = np.inf
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = -np.inf
        mat.ravel()[np.random.choice(mat.size, num_zeros, replace=False)] = 0
        mat.ravel()[np.random.choice(mat.size, num_nans, replace=False)] = np.nan
        #
        index = pd.date_range(start="01-04-2018", periods=nrows, freq="30T")
        df = pd.DataFrame(data=mat, index=index)
        return df

    def test1(self) -> None:
        data = [0.4, 0.133333, 0.133333, 0.133333, 0.2]
        index = [0, 1, 2, 3, 4]
        expected = pd.Series(data=data, index=index)
        actual = stats.compute_frac_nan(self._get_df(1))
        pd.testing.assert_series_equal(actual, expected, check_less_precise=3)

    def test2(self) -> None:
        data = [
            0.4,
            0.0,
            0.2,
            0.4,
            0.2,
            0.2,
            0.2,
            0.0,
            0.4,
            0.2,
            0.6,
            0.0,
            0.0,
            0.0,
            0.2,
        ]
        index = pd.date_range(start="1-04-2018", periods=15, freq="30T")
        expected = pd.Series(data=data, index=index)
        actual = stats.compute_frac_nan(self._get_df(1), axis=1)
        pd.testing.assert_series_equal(actual, expected, check_less_precise=3)

    def test3(self) -> None:
        # Equals 15 / 75 = num_nans / num_points.
        expected = 0.2
        actual = stats.compute_frac_nan(self._get_df(1), axis=None)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test4(self) -> None:
        series = self._get_df(1)[0]
        expected = 0.4
        actual = stats.compute_frac_nan(series)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test5(self) -> None:
        series = self._get_df(1)[0]
        expected = 0.4
        actual = stats.compute_frac_nan(series, axis=0)
        np.testing.assert_almost_equal(actual, expected, decimal=3)


class TestComputeFracConstant1(hut.TestCase):
    @staticmethod
    def _get_df(seed: int) -> pd.DataFrame:
        nrows = 15
        ncols = 5
        num_nans = 4
        num_infs = 2
        #
        np.random.seed(seed=1)
        mat = np.random.randint(-1, 1, (nrows, ncols)).astype("float")
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = np.inf
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = -np.inf
        mat.ravel()[np.random.choice(mat.size, num_nans, replace=False)] = np.nan
        #
        index = pd.date_range(start="01-04-2018", periods=nrows, freq="30T")
        df = pd.DataFrame(data=mat, index=index)
        return df

    def test1(self) -> None:
        data = [0.357143, 0.5, 0.285714, 0.285714, 0.071429]
        index = [0, 1, 2, 3, 4]
        expected = pd.Series(data=data, index=index)
        actual = stats.compute_frac_constant(self._get_df(1))
        pd.testing.assert_series_equal(actual, expected, check_less_precise=3)

    def test2(self) -> None:
        series = self._get_df(1)[0]
        expected = 0.357143
        actual = stats.compute_frac_constant(series)
        np.testing.assert_almost_equal(actual, expected, decimal=3)


class TestApplyKpssTest1(hut.TestCase):
    @staticmethod
    def _get_series(seed: int) -> pd.Series:

        np.random.seed(seed=1)
        arparams = np.array([0.75, -0.25])
        maparams = np.array([0.65, 0.35])
        arma_process = sig_gen.ArmaProcess(arparams, maparams)
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(date_range_kwargs=date_range)
        return series

    def test1(self) -> None:
        series = self._get_series(1)
        actual = stats.apply_kpss_test(series)
        actual_string = hut.convert_df_to_string(actual, index=True)
        self.check_string(actual_string)

    def test2(self) -> None:
        series = self._get_series(1)
        actual = stats.apply_kpss_test(series, regression="ct")
        actual_string = hut.convert_df_to_string(actual, index=True)
        self.check_string(actual_string)

    def test3(self) -> None:
        series = self._get_series(1)
        actual = stats.apply_kpss_test(series, nlags="auto")
        actual_string = hut.convert_df_to_string(actual, index=True)
        self.check_string(actual_string)

    def test4(self) -> None:
        series = self._get_series(1)
        actual = stats.apply_kpss_test(series, nlags=5)
        actual_string = hut.convert_df_to_string(actual, index=True)
        self.check_string(actual_string)
