"""
Import as:

import core.statistics as stats
"""

import collections
import datetime
import functools
import logging
import math
from typing import Any, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import scipy as sp
import sklearn.model_selection
import statsmodels
import statsmodels.api as sm

import core.finance as fin
import helpers.dataframe as hdf
import helpers.dbg as dbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# Descriptive statistics
# #############################################################################


# TODO(Paul): Double-check axes in used in calculation.
def compute_moments(
    srs: pd.Series, nan_mode: Optional[str] = None, prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate, mean, standard deviation, skew, and kurtosis.

    :param srs: input series for computing moments
    :param nan_mode: argument for hdf.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: series of computed moments
    """
    dbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    result_index = [
        prefix + "mean",
        prefix + "std",
        prefix + "skew",
        prefix + "kurtosis",
    ]
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        n_stats = len(result_index)
        nan_result = pd.Series(
            data=[np.nan for i in range(n_stats)],
            index=result_index,
            name=srs.name,
        )
        return nan_result
    result_values = [
        data.mean(),
        data.std(),
        sp.stats.skew(data, nan_policy="raise"),
        sp.stats.kurtosis(data, nan_policy="raise"),
    ]
    result = pd.Series(data=result_values, index=result_index, name=srs.name)
    return result


# TODO(*): Move this function out of this library.
def replace_infs_with_nans(
    data: Union[pd.Series, pd.DataFrame],
) -> Union[pd.Series, pd.DataFrame]:
    """
    Replace infs with nans in a copy of `data`.
    """
    if data.empty:
        _LOG.warning("Empty input!")
    return data.replace([np.inf, -np.inf], np.nan)


def compute_frac_zero(
    data: Union[pd.Series, pd.DataFrame],
    atol: float = 0.0,
    axis: Optional[int] = 0,
) -> Union[float, pd.Series]:
    """
    Calculate fraction of zeros in a numerical series or dataframe.

    :param data: numeric series or dataframe
    :param atol: absolute tolerance, as in `np.isclose`
    :param axis: numpy axis for summation
    """
    # Create an ndarray of zeros of the same shape.
    zeros = np.zeros(data.shape)
    # Compare values of `df` to `zeros`.
    is_close_to_zero = np.isclose(data.values, zeros, atol=atol)
    num_zeros = is_close_to_zero.sum(axis=axis)
    return _compute_denominator_and_package(num_zeros, data, axis)


def compute_frac_nan(
    data: Union[pd.Series, pd.DataFrame], axis: Optional[int] = 0
) -> Union[float, pd.Series]:
    """
    Calculate fraction of nans in `data`.

    :param data: numeric series or dataframe
    :param axis: numpy axis for summation
    """
    num_nans = data.isna().values.sum(axis=axis)
    return _compute_denominator_and_package(num_nans, data, axis)


def compute_frac_inf(
    data: Union[pd.Series, pd.DataFrame], axis: Optional[int] = 0
) -> Union[float, pd.Series]:
    """
    Count fraction of infs in a numerical series or dataframe.

    :param data: numeric series or dataframe
    :param axis: numpy axis for summation
    """
    num_infs = np.isinf(data.values).sum(axis=axis)
    return _compute_denominator_and_package(num_infs, data, axis)


# TODO(Paul): Consider exposing `rtol`, `atol`.
def compute_frac_constant(
    data: Union[pd.Series, pd.DataFrame]
) -> Union[float, pd.Series]:
    """
    Compute fraction of values in the series that changes at the next timestamp.

    :param data: numeric series or dataframe
    :param axis: numpy axis for summation
    """
    diffs = data.diff().iloc[1:]
    constant_frac = compute_frac_zero(diffs, axis=0)
    return constant_frac


# TODO(Paul): Refactor to work with dataframes as well. Consider how to handle
#     `axis`, which the pd.Series version of `copy()` does not take.
def count_num_finite_samples(data: pd.Series) -> float:
    """
    Count number of finite data points in a given time series.

    :param data: numeric series or dataframe
    """
    if data.empty:
        _LOG.warning("Empty input series `%s`", data.name)
        return np.nan
    data = data.copy()
    data = replace_infs_with_nans(data)
    return data.count()


# TODO(Paul): Extend to dataframes.
def count_num_unique_values(data: pd.Series) -> int:
    """
    Count number of unique values in the series.
    """
    if data.empty:
        _LOG.warning("Empty input series `%s`", data.name)
        return np.nan
    srs = pd.Series(data=data.unique())
    return count_num_finite_samples(srs)


def _compute_denominator_and_package(
    reduction: Union[float, np.ndarray],
    data: Union[pd.Series, pd.DataFrame],
    axis: Optional[float] = None,
) -> Union[float, pd.Series]:
    """
    Normalize and package `reduction` according to `axis` and `data` metadata.

    This is a helper function used for several `compute_frac_*` functions:
    - It determines the denominator to use in normalization (for the `frac`
      part)
    - It packages the output so that it has index/column information as
      appropriate

    :param reduction: contains a reduction of `data` along `axis`
    :param data: numeric series or dataframe
    :param axis: indicates row or column or else `None` for ignoring 2d
        structure
    """
    if isinstance(data, pd.Series):
        df = data.to_frame()
    else:
        df = data
    nrows, ncols = df.shape
    # Ensure that there is data available.
    # TODO(Paul): Consider adding a check on the column data type.
    if nrows == 0 or ncols == 0:
        _LOG.warning("No data available!")
        return np.nan
    # Determine the correct denominator based on `axis`.
    if axis is None:
        denom = nrows * ncols
    elif axis == 0:
        denom = nrows
    elif axis == 1:
        denom = ncols
    else:
        raise ValueError("axis=%i" % axis)
    normalized = reduction / denom
    # Return float or pd.Series as appropriate based on dimensions and axis.
    if isinstance(normalized, float):
        dbg.dassert(not axis)
        return normalized
    dbg.dassert_isinstance(normalized, np.ndarray)
    if axis == 0:
        return pd.Series(data=normalized, index=df.columns)
    if axis == 1:
        return pd.Series(data=normalized, index=df.index)
    raise ValueError("axis=`%s` but expected to be `0` or `1`!" % axis)


# #############################################################################
# Sharpe Ratio
# #############################################################################


def summarize_sharpe_ratio(
    log_rets: pd.Series, prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate SR, SE(SR) from rets with an index freq and annualize.

    TODO(*): Consider de-biasing when the number of sample points is small,
        e.g., https://www.twosigma.com/wp-content/uploads/sharpe-tr-1.pdf
    """
    prefix = prefix or ""
    sr = compute_annualized_sharpe_ratio(log_rets)
    sr_se_estimate = compute_annualized_sharpe_ratio_standard_error(log_rets)
    res = pd.Series(
        data=[sr, sr_se_estimate],
        index=[prefix + "ann_sharpe", prefix + "ann_sharpe_se"],
        name=log_rets.name,
    )
    return res


def compute_annualized_sharpe_ratio(
    log_rets: Union[pd.Series, pd.DataFrame],
) -> Union[float, pd.Series]:
    """
    Compute SR from rets with an index freq and annualize.

    :param log_rets: time series of log returns
    :return: annualized Sharpe ratio
    """
    points_per_year = hdf.infer_sampling_points_per_year(log_rets)
    sr = compute_sharpe_ratio(log_rets, points_per_year)
    return sr


def compute_annualized_sharpe_ratio_standard_error(
    log_rets: Union[pd.Series, pd.DataFrame],
) -> Union[float, pd.Series]:
    """
    Compute SE(SR) from rets with an index freq and annualize.

    This function calculates the standard error with respect to the original
    sampling frequency and then rescales to turn it into a standard error
    for the corresponding annualized Sharpe ratio.

    :param log_rets: time series of log returns
    :return: standard error estimate of annualized Sharpe ratio
    """
    points_per_year = hdf.infer_sampling_points_per_year(log_rets)
    se_sr = compute_sharpe_ratio_standard_error(log_rets, points_per_year)
    return se_sr


def compute_sharpe_ratio(
    log_rets: Union[pd.Series, pd.DataFrame], time_scaling: Union[int, float] = 1
) -> Union[float, pd.Series]:
    r"""
    Calculate Sharpe Ratio (SR) from log returns and rescale.

    For a detailed exploration of SR, see
    http://www.gilgamath.com/pages/ssc.html.

    :param log_rets: time series of log returns
    :param time_scaling: rescales SR by a factor of \sqrt(time_scaling).
        - For SR with respect to the sampling frequency, set equal to 1
        - For annualization, set equal to the number of sampling frequency
          ticks per year (e.g., =252 if daily returns are provided)
    :return: Sharpe Ratio
    """
    dbg.dassert_lte(1, time_scaling, f"time_scaling=`{time_scaling}`")
    sr = log_rets.mean() / log_rets.std()
    sr *= np.sqrt(time_scaling)
    if isinstance(sr, pd.Series):
        sr.name = "SR"
    return sr


def compute_sharpe_ratio_standard_error(
    log_rets: Union[pd.Series, pd.DataFrame], time_scaling: Union[int, float] = 1
) -> Union[float, pd.Series]:
    """
    Calculate Sharpe Ratio standard error from log returns and rescale.

    :param log_rets: time series of log returns
    :param time_scaling: as in `compute_sharpe_ratio`
    :return: Sharpe ratio standard error estimate
    """
    dbg.dassert_lte(1, time_scaling, f"time_scaling=`{time_scaling}`")
    # Compute the Sharpe ratio using the sampling frequency units[
    sr = compute_sharpe_ratio(log_rets, time_scaling=1)
    # TODO(*): Use `nan_mode` to determine size
    sr_var_estimate = (1 + (sr ** 2) / 2) / log_rets.dropna().size
    sr_se_estimate = np.sqrt(sr_var_estimate)
    # Rescale.
    rescaled_sr_se_estimate = np.sqrt(time_scaling) * sr_se_estimate
    if isinstance(sr, pd.Series):
        rescaled_sr_se_estimate = "SE(SR)"
    return rescaled_sr_se_estimate


# #############################################################################
# Cross-validation
# #############################################################################


def get_rolling_splits(
    idx: pd.Index, n_splits: int
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Partition index into chunks and returns pairs of successive chunks.

    If the index looks like
        [0, 1, 2, 3, 4, 5, 6]
    and n_splits = 4, then the splits would be
        [([0, 1], [2, 3]),
         ([2, 3], [4, 5]),
         ([4, 5], [6])]

    A typical use case is where the index is a monotonic increasing datetime
    index. For such cases, causality is respected by the splits.
    """
    dbg.dassert_monotonic_index(idx)
    n_chunks = n_splits + 1
    dbg.dassert_lte(1, n_splits)
    # Split into equal chunks.
    chunk_size = int(math.ceil(idx.size / n_chunks))
    dbg.dassert_lte(1, chunk_size)
    chunks = [idx[i : i + chunk_size] for i in range(0, idx.size, chunk_size)]
    dbg.dassert_eq(len(chunks), n_chunks)
    #
    splits = list(zip(chunks[:-1], chunks[1:]))
    return splits


def get_oos_start_split(
    idx: pd.Index, datetime_: Union[datetime.datetime, pd.Timestamp]
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Split index using OOS (out-of-sample) start datetime.
    """
    dbg.dassert_monotonic_index(idx)
    ins_mask = idx < datetime_
    dbg.dassert_lte(1, ins_mask.sum())
    oos_mask = ~ins_mask
    dbg.dassert_lte(1, oos_mask.sum())
    ins = idx[ins_mask]
    oos = idx[oos_mask]
    return [(ins, oos)]


# TODO(Paul): Support train/test/validation or more.
def get_train_test_pct_split(
    idx: pd.Index, train_pct: float
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Split index into train and test sets by percentage.
    """
    dbg.dassert_monotonic_index(idx)
    dbg.dassert_lt(0.0, train_pct)
    dbg.dassert_lt(train_pct, 1.0)
    #
    train_size = int(train_pct * idx.size)
    dbg.dassert_lte(0, train_size)
    train_split = idx[:train_size]
    test_split = idx[train_size:]
    return [(train_split, test_split)]


def get_expanding_window_splits(
    idx: pd.Index, n_splits: int
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Generate splits with expanding overlapping windows.
    """
    dbg.dassert_monotonic_index(idx)
    dbg.dassert_lte(1, n_splits)
    tscv = sklearn.model_selection.TimeSeriesSplit(n_splits=n_splits)
    locs = list(tscv.split(idx))
    splits = [(idx[loc[0]], idx[loc[1]]) for loc in locs]
    return splits


def truncate_index(idx: pd.Index, min_idx: Any, max_idx: Any) -> pd.Index:
    """
    Return subset of idx with values >= min_idx and < max_idx.
    """
    dbg.dassert_monotonic_index(idx)
    # TODO(*): PartTask667: Consider using bisection to avoid linear scans.
    min_mask = idx >= min_idx
    max_mask = idx < max_idx
    mask = min_mask & max_mask
    dbg.dassert_lte(1, mask.sum())
    return idx[mask]


def combine_indices(idxs: Iterable[pd.Index]) -> pd.Index:
    """
    Combine multiple indices into a single index for cross-validation splits.

    This is computed as the union of all the indices within the largest common
    interval.

    TODO(Paul): Consider supporting multiple behaviors with `mode`.
    """
    for idx in idxs:
        dbg.dassert_monotonic_index(idx)
    # Find the maximum start/end datetime overlap of all source indices.
    max_min = max([idx.min() for idx in idxs])
    _LOG.debug("Latest start datetime of indices=%s", max_min)
    min_max = min([idx.max() for idx in idxs])
    _LOG.debug("Earliest end datetime of indices=%s", min_max)
    truncated_idxs = [truncate_index(idx, max_min, min_max) for idx in idxs]
    # Take the union of truncated indices. Though all indices fall within the
    # datetime range [max_min, min_max), they do not necessarily have the same
    # resolution or all values.
    composite_idx = functools.reduce(lambda x, y: x.union(y), truncated_idxs)
    return composite_idx


def convert_splits_to_string(splits: collections.OrderedDict) -> str:
    txt = "n_splits=%s\n" % len(splits)
    for train_idxs, test_idxs in splits:
        txt += "train=%s [%s, %s]" % (
            len(train_idxs),
            min(train_idxs),
            max(train_idxs),
        )
        txt += "\n"
        txt += "test=%s [%s, %s]" % (
            len(test_idxs),
            min(test_idxs),
            max(test_idxs),
        )
        txt += "\n"
    return txt


# #############################################################################
# Hypothesis testing
# #############################################################################


def ttest_1samp(
    srs: pd.Series,
    popmean: Optional[float] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Thin wrapper around scipy's ttest.

    :param srs: input series for computing statistics
    :param popmean: assumed population mean for test
    :param nan_mode: argument for hdf.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: series with t-value and p-value
    """
    dbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    popmean = popmean or 0
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    result_index = [
        prefix + "tval",
        prefix + "pval",
    ]
    nan_result = pd.Series(
        data=[np.nan, np.nan], index=result_index, name=srs.name
    )
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        tval, pval = sp.stats.ttest_1samp(
            data, popmean=popmean, nan_policy="raise"
        )
    except ValueError as inst:
        _LOG.warning(inst)
        return nan_result
    result_values = [
        tval,
        pval,
    ]
    result = pd.Series(data=result_values, index=result_index, name=data.name)
    return result


def multipletests(
    srs: pd.Series,
    method: Optional[str] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Wrap statsmodel's multipletests.

    Returns results in a series indexed like srs.
    Documentation at
    https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html

    :param srs: Series with pvalues
    :param method: `method` for scipy's multipletests
    :param nan_mode: approach to deal with NaNs, can be "strict" or "ignore"
    :param prefix: optional prefix for metrics' outcome
    :return: Series of adjusted p-values
    """
    dbg.dassert_isinstance(srs, pd.Series)
    method = method or "fdr_bh"
    nan_mode = nan_mode or "strict"
    dbg.dassert_in(nan_mode, ["strict", "ignore"])
    prefix = prefix or ""
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    if data.empty:
        _LOG.warning("Empty input series `%s`", data.name)
        return pd.Series([np.nan], name=prefix + "adj_pval")
    pvals_corrected = statsmodels.stats.multitest.multipletests(
        data, method=method
    )[1]
    return pd.Series(pvals_corrected, index=data.index, name=prefix + "adj_pval")


def multi_ttest(
    data: pd.DataFrame,
    popmean: Optional[float] = None,
    nan_mode: Optional[str] = None,
    method: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.DataFrame:
    """
    Combine ttest and multitest pvalue adjustment.
    """
    popmean = popmean or 0
    nan_mode = nan_mode or "ignore"
    method = method or "fdr_bh"
    prefix = prefix or ""
    dbg.dassert_isinstance(data, pd.DataFrame)
    if data.empty:
        _LOG.warning("Empty input!")
        return pd.DataFrame(
            [np.nan, np.nan, np.nan],
            index=[prefix + "tval", prefix + "pval", prefix + "adj_pval"],
            columns=[data.columns],
        )
    res = data.apply(
        ttest_1samp, popmean=popmean, nan_mode=nan_mode, prefix=prefix
    ).T
    res[prefix + "adj_pval"] = multipletests(res[prefix + "pval"], method=method)
    return res


def apply_normality_test(
    srs: pd.Series, nan_mode: Optional[str] = None, prefix: Optional[str] = None,
) -> pd.Series:
    """
    Test (indep) null hypotheses that each col is normally distributed.

    An omnibus test of normality that combines skew and kurtosis.

    :param prefix: optional prefix for metrics' outcome
    :param nan_mode: argument for hdf.apply_nan_mode()
    :return: series with statistics and p-value
    """
    dbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    result_index = [
        prefix + "stat",
        prefix + "pval",
    ]
    n_stats = len(result_index)
    nan_result = pd.Series(
        data=[np.nan for i in range(n_stats)], index=result_index, name=srs.name
    )
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        stat, pval = sp.stats.normaltest(data, nan_policy="raise")
    except ValueError as inst:
        # This can raise if there are not enough data points, but the number
        # required can depend upon the input parameters.
        _LOG.warning(inst)
        return nan_result
    result_values = [
        stat,
        pval,
    ]
    result = pd.Series(data=result_values, index=result_index, name=data.name)
    return result


# TODO(*): Maybe add `inf_mode`.
def apply_adf_test(
    srs: pd.Series,
    maxlag: Optional[int] = None,
    regression: Optional[str] = None,
    autolag: Optional[str] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Implement a wrapper around statsmodels' adfuller test.

    :param srs: pandas series of floats
    :param maxlag: as in stattools.adfuller
    :param regression: as in stattools.adfuller
    :param autolag: as in stattools.adfuller
    :param nan_mode: argument for hdf.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: test statistic, pvalue, and related info
    """
    dbg.dassert_isinstance(srs, pd.Series)
    regression = regression or "c"
    autolag = autolag or "AIC"
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    # https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html
    result_index = [
        prefix + "stat",
        prefix + "pval",
        prefix + "used_lag",
        prefix + "nobs",
        prefix + "critical_values_1%",
        prefix + "critical_values_5%",
        prefix + "critical_values_10%",
        prefix + "ic_best",
    ]
    n_stats = len(result_index)
    nan_result = pd.Series(
        data=[np.nan for i in range(n_stats)], index=result_index, name=data.name,
    )
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        (
            adf_stat,
            pval,
            usedlag,
            nobs,
            critical_values,
            icbest,
        ) = sm.tsa.stattools.adfuller(
            data.values, maxlag=maxlag, regression=regression, autolag=autolag
        )
    except ValueError as inst:
        # This can raise if there are not enough data points, but the number
        # required can depend upon the input parameters.
        _LOG.warning(inst)
        return nan_result
        #
    result_values = [
        adf_stat,
        pval,
        usedlag,
        nobs,
        critical_values["1%"],
        critical_values["5%"],
        critical_values["10%"],
        icbest,
    ]
    result = pd.Series(data=result_values, index=result_index, name=data.name)
    return result


def apply_kpss_test(
    srs: pd.Series,
    regression: Optional[str] = None,
    nlags: Optional[Union[int, str]] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Implement a wrapper around statsmodels' KPSS test.

    http://debis.deu.edu.tr/userweb//onder.hanedar/dosyalar/kpss.pdf

    :param srs: pandas series of floats
    :param regression: as in stattools.kpss
    :param nlags: as in stattools.kpss
    :param nan_mode: argument for hdf.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: test statistic, pvalue, and related info
    """
    dbg.dassert_isinstance(srs, pd.Series)
    regression = regression or "c"
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    # https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html
    result_index = [
        prefix + "stat",
        prefix + "pval",
        prefix + "lags",
        prefix + "critical_values_1%",
        prefix + "critical_values_5%",
        prefix + "critical_values_10%",
    ]
    n_stats = len(result_index)
    nan_result = pd.Series(
        data=[np.nan for i in range(n_stats)], index=result_index, name=data.name,
    )
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        (kpss_stat, pval, lags, critical_values,) = sm.tsa.stattools.kpss(
            data.values, regression=regression, nlags=nlags
        )
    except ValueError:
        # This can raise if there are not enough data points, but the number
        # required can depend upon the input parameters.
        return nan_result
        #
    result_values = [
        kpss_stat,
        pval,
        lags,
        critical_values["1%"],
        critical_values["5%"],
        critical_values["10%"],
    ]
    result = pd.Series(data=result_values, index=result_index, name=data.name)
    return result


def compute_zero_nan_inf_stats(
    srs: pd.Series, prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate finite and non-finite values in time series.

    :param srs: pandas series of floats
    :param prefix: optional prefix for metrics' outcome
    :return: series of stats
    """
    # TODO(*): To be optimized/rewritten in #2340.
    prefix = prefix or ""
    dbg.dassert_isinstance(srs, pd.Series)
    result_index = [
        prefix + "n_rows",
        prefix + "frac_zero",
        prefix + "frac_nan",
        prefix + "frac_inf",
        prefix + "frac_constant",
        prefix + "num_finite_samples",
    ]
    n_stats = len(result_index)
    nan_result = pd.Series(
        data=[np.nan for i in range(n_stats)], index=result_index, name=srs.name
    )
    if srs.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    result_values = [
        len(srs),
        compute_frac_zero(srs),
        compute_frac_nan(srs),
        compute_frac_inf(srs),
        compute_frac_constant(srs),
        count_num_finite_samples(srs),
        # TODO(*): Add after extension to dataframes.
        # "num_unique_values",
        # stats.count_num_unique_values
    ]
    result = pd.Series(data=result_values, index=result_index, name=srs.name)
    return result


def apply_ljung_box_test(
    srs: pd.Series,
    lags: Optional[Union[int, pd.Series]] = None,
    model_df: Optional[int] = None,
    period: Optional[int] = None,
    return_df: Optional[bool] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.DataFrame:
    """
    Implement a wrapper around statsmodels' Ljung-Box test.

    :param srs: pandas series of floats
    :param lags: as in diagnostic.acorr_ljungbox
    :param model_df: as in diagnostic.acorr_ljungbox
    :param period: as in diagnostic.acorr_ljungbox
    :param return_df: as in diagnostic.acorr_ljungbox
    :param nan_mode: argument for hdf.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: test statistic, pvalue
    """
    dbg.dassert_isinstance(srs, pd.Series)
    model_df = model_df or 0
    return_df = return_df or True
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    # https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html
    columns = [
        prefix + "stat",
        prefix + "pval",
    ]
    # Make an output for empty or too short inputs.
    nan_result = pd.DataFrame([[np.nan, np.nan]], columns=columns)
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        result = sm.stats.diagnostic.acorr_ljungbox(
            data.values,
            lags=lags,
            model_df=model_df,
            period=period,
            return_df=return_df,
        )
    except ValueError as inst:
        _LOG.warning(inst)
        return nan_result
    #
    if return_df:
        df_result = result
    else:
        df_result = pd.DataFrame(result).T
    df_result.columns = columns
    return df_result


def calculate_hit_rate(
    srs: pd.Series,
    alpha: Optional[float] = None,
    method: Optional[str] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
    mode: Optional[str] = None,
) -> pd.Series:
    """
    Calculate hit rate statistics.

    :param srs: pandas series of 0s, 1s and NaNs
    :param alpha: as in statsmodels.stats.proportion.proportion_confint()
    :param method: as in statsmodels.stats.proportion.proportion_confint()
    :param nan_mode: argument for hdf.apply_nan_mode(), can affect confidence
        intervals calculation
    :param prefix: optional prefix for metrics' outcome
    :param mode: `strict` or `sign`. `strict` requires a series of `0`s, `1`s
        and possibly `NaNs`; `sign` interprets positive finite numbers as hits
    :return: hit rate statistics: point estimate, lower bound, upper bound
    """
    alpha = alpha or 0.05
    method = method or "jeffreys"
    dbg.dassert_lte(0, alpha)
    dbg.dassert_lte(alpha, 1)
    dbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    mode = mode or "sign"
    # Process series.
    conf_alpha = (1 - alpha / 2) * 100
    result_index = [
        prefix + "hit_rate_point_est",
        prefix + f"hit_rate_{conf_alpha:.2f}%CI_lower_bound",
        prefix + f"hit_rate_{conf_alpha:.2f}%CI_upper_bound",
    ]
    srs = srs.replace([-np.inf, np.inf], np.nan)
    srs = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    if srs.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        nan_result = pd.Series(index=result_index, name=srs.name, dtype="float64")
        return nan_result
    if mode == "strict":
        dbg.dassert_is_subset(
            srs, [0, 1], "Series should contain only 0s, 1s and NaNs"
        )
        hit_mask = srs.copy()
    elif mode == "sign":
        hit_mask = srs > 0
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    # Calculate confidence intervals.
    point_estimate = hit_mask.mean()
    hit_lower, hit_upper = statsmodels.stats.proportion.proportion_confint(
        count=hit_mask.sum(), nobs=hit_mask.count(), alpha=alpha, method=method
    )
    result_values = [point_estimate, hit_lower, hit_upper]
    result = pd.Series(data=result_values, index=result_index, name=srs.name)
    return result


def compute_jensen_ratio(
    signal: pd.Series,
    p_norm: float = 2,
    inf_mode: Optional[str] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate a ratio >= 1 with equality only when Jensen's inequality holds.

    Definition and derivation:
      - The result is the p-th root of the expectation of the p-th power of
        abs(f), divided by the expectation of abs(f). If we apply Jensen's
        inequality to (abs(signal)**p)**(1/p), renormalizing the lower bound to
        1, then the upper bound is the valued calculated by this function.
      - An alternative derivation is to apply Holder's inequality to `signal`,
        using the constant function `1` on the support of the `signal` as the
        2nd function.

    Interpretation:
      - If we apply this function to returns in the case where the expected
        value of returns is 0 and we take p_norm = 2, then the result of this
        function can be interpreted as a renormalized realized volatility.
      - For a Gaussian signal, the expected value is np.sqrt(np.pi / 2), which
        is approximately 1.25. This holds regardless of the volatility of the
        Gaussian (so the measure is scale invariant).
      - For a stationary function, the expected value does not change with
        sampled series length.
      - For a signal that is t-distributed with 4 dof, the expected value is
        approximately 1.41.
    """
    dbg.dassert_isinstance(signal, pd.Series)
    # Require that we evaluate a norm.
    dbg.dassert_lte(1, p_norm)
    # TODO(*): Maybe add l-infinity support. For many stochastic signals, we
    # should not expect a finite value in the continuous limit.
    dbg.dassert(np.isfinite(p_norm))
    # Set reasonable defaults for inf and nan modes.
    inf_mode = inf_mode or "return_nan"
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    data = hdf.apply_nan_mode(signal, nan_mode=nan_mode)
    nan_result = pd.Series(
        data=[np.nan], index=[prefix + "jensen_ratio"], name=signal.name
    )
    dbg.dassert(not data.isna().any())
    # Handle infs.
    # TODO(*): apply special functions for inf_mode after #2624 is completed.
    has_infs = (~data.apply(np.isfinite)).any()
    if has_infs:
        if inf_mode == "return_nan":
            # According to a strict interpretation, each norm is infinite, and
            # and so their quotient is undefined.
            return nan_result
        elif inf_mode == "ignore":
            # Replace inf values with np.nan and drop.
            data = data.replace([-np.inf, np.inf], np.nan).dropna()
        else:
            raise ValueError(f"Unrecognized inf_mode `{inf_mode}")
    dbg.dassert(data.apply(np.isfinite).all())
    # Return NaN if there is no data.
    if data.size == 0:
        _LOG.warning("Empty input signal `%s`", signal.name)
        return nan_result
    # Calculate norms.
    lp = sp.linalg.norm(data, ord=p_norm)
    l1 = sp.linalg.norm(data, ord=1)
    # Ignore support where `signal` has NaNs.
    scaled_support = data.size ** (1 - 1 / p_norm)
    jensen_ratio = scaled_support * lp / l1
    res = pd.Series(
        data=[jensen_ratio], index=[prefix + "jensen_ratio"], name=signal.name
    )
    return res


def compute_forecastability(
    signal: pd.Series,
    mode: str = "welch",
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    r"""
    Compute frequency-domain-based "forecastability" of signal.

    Reference: https://arxiv.org/abs/1205.4591

    `signal` is assumed to be second-order stationary.

    Denote the forecastability estimator by \Omega(\cdot).
    Let x_t, y_t be time series. Properties of \Omega include:
    a) \Omega(y_t) = 0 iff y_t is white noise
    b) scale and shift-invariant:
         \Omega(a y_t + b) = \Omega(y_t) for real a, b, a \neq 0.
    c) max sub-additivity for uncorrelated processes:
         \Omega(\alpha x_t + \sqrt{1 - \alpha^2} y_t) \leq
         \max\{\Omega(x_t), \Omega(y_t)\},
       if \E(x_t y_s) = 0 for all s, t \in \Z;
       equality iff alpha \in \{0, 1\}.
    """
    dbg.dassert_isinstance(signal, pd.Series)
    nan_mode = nan_mode or "fill_with_zero"
    prefix = prefix or ""
    data = hdf.apply_nan_mode(signal, nan_mode=nan_mode)
    # Return NaN if there is no data.
    if data.size == 0:
        _LOG.warning("Empty input signal `%s`", signal.name)
        nan_result = pd.Series(
            data=[np.nan], index=[prefix + "forecastability"], name=signal.name
        )
        return nan_result
    if mode == "welch":
        _, psd = sp.signal.welch(data)
    elif mode == "periodogram":
        # TODO(Paul): Maybe log a warning about inconsistency of periodogram
        #     for estimating power spectral density.
        _, psd = sp.signal.periodogram(data)
    else:
        raise ValueError("Unsupported mode=`%s`" % mode)
    forecastability = 1 - sp.stats.entropy(psd, base=psd.size)
    res = pd.Series(
        data=[forecastability],
        index=[prefix + "forecastability"],
        name=signal.name,
    )
    return res


def compute_max_drawdown(
    log_rets: pd.Series, prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate max drawdown statistic.

    :param log_rets: pandas series of log returns
    :param prefix: optional prefix for metrics' outcome
    :return: max drawdown as a negative percentage loss
    """
    dbg.dassert_isinstance(log_rets, pd.Series)
    prefix = prefix or ""
    result_index = [prefix + "max_drawdown"]
    nan_result = pd.Series(
        index=result_index, name=log_rets.name, dtype="float64"
    )
    if log_rets.empty:
        _LOG.warning("Empty input series `%s`", log_rets.name)
        return nan_result
    pct_drawdown = fin.compute_perc_loss_from_high_water_mark(log_rets)
    max_drawdown = -100 * (pct_drawdown.max())
    result = pd.Series(data=max_drawdown, index=result_index, name=log_rets.name)
    return result


def compute_zero_diff_proportion(
    srs: pd.Series,
    atol: Optional[float] = None,
    rtol: Optional[float] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Compute proportion of unvarying periods in a series.

    https://numpy.org/doc/stable/reference/generated/numpy.isclose.html

    :param srs: pandas series of floats
    :param atol: as in numpy.isclose
    :param rtol: as in numpy.isclose
    :param nan_mode: argument for hdf.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: series with proportion of unvarying periods
    """
    dbg.dassert_isinstance(srs, pd.Series)
    atol = atol or 0
    rtol = rtol or 1e-05
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    result_index = [
        prefix + "approx_const_count",
        prefix + "approx_const_frac",
    ]
    if data.shape[0] < 2:
        _LOG.warning(
            "Input series `%s` with size '%d' is too small",
            srs.name,
            data.shape[0],
        )
        nan_result = pd.Series(
            data=[np.nan, np.nan], index=result_index, name=srs.name
        )
        return nan_result
    # Compute if neighboring elements are equal within the given tolerance.
    equal_ngb_srs = np.isclose(data.shift(1)[1:], data[1:], atol=atol, rtol=rtol)
    # Compute number and proportion of equals among all neighbors pairs.
    approx_const_count = equal_ngb_srs.sum()
    n_pairs = data.shape[0] - 1
    approx_const_frac = approx_const_count / n_pairs
    result_values = [approx_const_count, approx_const_frac]
    res = pd.Series(data=result_values, index=result_index, name=srs.name)
    return res


def get_interarrival_time(
    srs: pd.Series, nan_mode: Optional[str] = None,
) -> Optional[pd.Series]:
    """
    Get interrarival time from index of a time series.

    :param srs: pandas series of floats
    :param nan_mode: argument for hdf.apply_nan_mode()
    :return: series with interrarival time
    """
    dbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "ignore"
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    if data.empty:
        _LOG.warning("Empty input `%s`", srs.name)
        return None
    index = data.index
    # Check index of a series. We require that the input
    #     series have a sorted datetime index.
    dbg.dassert_isinstance(index, pd.DatetimeIndex)
    dbg.dassert_monotonic_index(index)
    # Compute a series of interrairival time.
    interrarival_time = pd.Series(index).diff()
    return interrarival_time


def compute_interarrival_time_stats(
    srs: pd.Series, nan_mode: Optional[str] = None, prefix: Optional[str] = None,
) -> pd.Series:
    """
    Compute interarrival time statistics.

    :param srs: pandas series of interrarival time
    :param nan_mode: argument for hdf.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: series with statistic and related info
    """
    dbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "ignore"
    prefix = prefix or ""
    data = hdf.apply_nan_mode(srs, nan_mode=nan_mode)
    result_index = [
        prefix + "n_unique",
        prefix + "mean",
        prefix + "std",
        prefix + "max",
        prefix + "min",
    ]
    if data.shape[0] < 2:
        _LOG.warning(
            "Input series `%s` with size '%d' is too small",
            srs.name,
            data.shape[0],
        )
        nan_result = pd.Series(index=result_index, name=data.name, dtype="object")
        return nan_result
    interarrival_time = get_interarrival_time(data)
    n_unique = interarrival_time.nunique()
    mean = interarrival_time.mean()
    std = interarrival_time.std()
    max_value = interarrival_time.max()
    min_value = interarrival_time.min()
    #
    result_values = [n_unique, mean, std, max_value, min_value]
    res = pd.Series(
        data=result_values, index=result_index, name=srs.name, dtype="object"
    )
    return res
