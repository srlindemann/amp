import logging
import math
from typing import List, Optional, Tuple

from sklearn.model_selection import TimeSeriesSplit

import pandas as pd
import scipy as sp
import statsmodels as sm

import helpers.dbg as dbg

_LOG = logging.getLogger(__name__)

MEAN_COL = "mean"
STD_COL = "std"
SKEW_COL = "skew"
KURT_COL = "kurt"
PVAL_COL = "pvals"
TVAL_COL = "tvals"
ADJ_PVAL_COL = "adj_pvals"


# #############################################################################
# Descriptive statistics
# #############################################################################


# TODO(Paul): Double-check axes in used in calculation.
# Consider exposing `nan_policy`.
def moments(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates, mean, standard deviation, skew, and kurtosis.
    """
    mean = df.mean()
    std = df.std()
    skew = sp.stats.skew(df, nan_policy="omit")
    kurt = sp.stats.kurtosis(df, nan_policy="omit")
    result = pd.DataFrame(
        {MEAN_COL: mean, STD_COL: std, SKEW_COL: skew, KURT_COL: kurt},
        index=df.columns,
    )
    return result


# #############################################################################
# Cross-validation
# #############################################################################


def get_rolling_splits(
    idx: pd.Index, n_splits: int
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Partitions index into chunks and returns pairs of successive chunks.

    If the index looks like
        [0, 1, 2, 3, 4, 5, 6]
    and n_splits = 4, then the splits would be
        [([0, 1], [2, 3]),
         ([2, 3], [4, 5]),
         ([4, 5], [6])]

    A typical use case is where the index is a monotonic increasing datetime
    index. For such cases, causality is respected by the splits.
    """
    dbg.dassert_lte(2, n_splits)
    # Split into equal chunks.
    chunk_size = int(math.ceil(idx.size / n_splits))
    dbg.dassert_lte(1, chunk_size)
    chunks = [idx[i : i + chunk_size] for i in range(0, idx.size, chunk_size)]
    dbg.dassert_eq(len(chunks), n_splits)
    #
    splits = list(zip(chunks[:-1], chunks[1:]))
    return splits


def get_oos_start_split(
    idx: pd.Index,
    datetime_,
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Split index using OOS (out-of-sample) start datetime.
    """
    ins = idx[idx < datetime_]
    oos = idx[idx >= datetime_]
    return [(ins, oos)]


# TODO(Paul): Support train/test/validation or more.
def get_train_test_pct_split(
    idx: pd.Index,
    train_pct: float,
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Split index into train and test sets by percentage.
    """
    dbg.dassert_lte(0.0, train_pct)
    dbg.dassert_lte(train_pct, 1.0)
    #
    train_size = int(train_pct * idx.size)
    dbg.dassert_lte(0, train_size)
    train_split = idx[:train_size]
    test_split = idx[train_size:]
    return [(train_split, test_split)]


def get_expanding_window_splits(
    idx: pd.Index,
    n_splits: int
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Generate splits with expanding overlapping windows.
    """
    dbg.dassert_lte(1, n_splits)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    locs = list(tscv.split(idx))
    splits = [(idx[loc[0]], idx[loc[1]]) for loc in locs]
    return splits


def convert_splits_to_string(splits, df=None):
    txt = "n_splits=%s\n" % len(splits)
    for train_idxs, test_idxs in splits:
        if df is None:
            txt += "  train=%s [%s, %s]" % (
                len(train_idxs),
                min(train_idxs),
                max(train_idxs),
            )
            txt += ", test=[%s, %s] %s" % (
                len(test_idxs),
                min(test_idxs),
                max(test_idxs),
            )
        else:
            txt += "  train=%s [%s, %s]" % (
                len(train_idxs),
                min(df.iloc[train_idxs]),
                max(df.iloc[train_idxs]),
            )
            txt += ", test=%s [%s, %s]" % (
                len(test_idxs),
                min(df.iloc[test_idxs]),
                max(df.iloc[test_idxs]),
            )
        txt += "\n"
    return txt


# #############################################################################
# Hypothesis testing
# #############################################################################


def ttest_1samp(
    df: pd.DataFrame,
    popmean: Optional[float] = None,
    nan_policy: Optional[str] = None,
) -> pd.DataFrame:
    """
    Thin wrapper around scipy's ttest.

    WARNING: Passing in df.dropna(how='all') vs df.dropna() (which defaults to
    'any') can yield different results. Safest is to NOT DROP NANs in the input
    and instead use `nan_policy='omit'`.

    :param df: DataFrame with samples along rows, groups along columns.
    :param popmean: assumed population mean for test
    :param nan_policy: `nan_policy` for scipy's ttest_1samp
    :return: DataFrame with t-value and p-value columns, rows like df's columns
    """
    if popmean is None:
        popmean = 0
    if nan_policy is None:
        nan_policy = "omit"
    tvals, pvals = sp.stats.ttest_1samp(
        df, popmean=popmean, nan_policy=nan_policy
    )
    result = pd.DataFrame({TVAL_COL: tvals, PVAL_COL: pvals}, index=df.columns)
    return result


def multipletests(srs: pd.Series, method: Optional[str] = None) -> pd.Series:
    """
    Thin wrapper around statsmodel's multipletests.

    Returns results in a series indexed like srs.

    Documentation at
    https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html

    :param srs: Series with pvalues
    :param method: `method` for scipy's multipletests
    :return: Series of adjusted p-values
    """
    if method is None:
        method = "fdr_bd"
    pvals_corrected = sm.stats.multitest.multipletests(srs, method=method)[1]
    return pd.Series(pvals_corrected, index=srs.index, name=ADJ_PVAL_COL)


def multi_ttest(
    df: pd.DataFrame,
    popmean: Optional[float] = None,
    nan_policy: Optional[str] = None,
    method: Optional[str] = None,
) -> pd.DataFrame:
    """
    Combines ttest and multitest pvalue adjustment.
    """
    ttest = ttest_1samp(df, popmean=popmean, nan_policy=nan_policy)
    ttest[ADJ_PVAL_COL] = multipletests(ttest[PVAL_COL], method=method)
    return ttest
