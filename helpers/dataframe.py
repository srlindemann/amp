"""
Helper functions for processing pandas dataframes.

Import as:

import helpers.dataframe as hdataf
"""

# TODO(gp): Consider merging with `core/pandas_helpers.py`.

import collections
import functools
import logging
import operator
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd

import helpers.dbg as dbg
import helpers.printing as hprint

_LOG = logging.getLogger(__name__)


_METHOD_TO_APPLY = Dict[str, Dict[str, Any]]


def filter_data_by_values(
    data: pd.DataFrame,
    filters: Dict[Union[int, str], Tuple[Any, ...]],
    mode: str,
    info: Optional[collections.OrderedDict] = None,
) -> pd.DataFrame:
    """
    Filter dataframe rows based on column values.

    :param data: dataframe
    :param filters: `{col_name: (possible_values)}`
    :param mode: `and` for conjunction and `or` for disjunction of filters
    :param info: information storage
    :return: filtered dataframe
    """
    if info is None:
        info = collections.OrderedDict()
    info["nrows"] = data.shape[0]
    if not filters:
        info["nrows_remaining"] = data.shape[0]
        return data.copy()
    # Create filter masks for each column.
    masks = []
    for col_name, vals in filters.items():
        dbg.dassert_isinstance(vals, tuple)
        mask = data[col_name].isin(vals)
        info[f"n_{col_name}"] = mask.sum()
        info[f"perc_{col_name}"] = hprint.perc(mask.sum(), data.shape[0])
        masks.append(mask)
    masks = pd.concat(masks, axis=1)
    combined_mask = _combine_masks(masks, mode, info)
    filtered_data = data.loc[combined_mask].copy()
    return filtered_data


def filter_data_by_comparison(
    data: pd.DataFrame,
    filters: Dict[
        Union[int, str], Union[Tuple[str, Any], Tuple[Tuple[str, Any], ...]]
    ],
    mode: str,
    info: Optional[collections.OrderedDict] = None,
) -> pd.DataFrame:
    """
    Filter dataframe by comparing columns to values.

    :param data: dataframe
    :param filters: `{col_name: (comparison_method, value)}` or
        `{col_name: ((comparison_method_i, value_i))}`.
        `comparison_method` is one of the ("eq", "ne", "le", "lt", "ge", "gt")
        pandas method names.
    :param mode: `and` for conjunction and `or` for disjunction of filters
    :param info: information storage
    :return: filtered dataframe
    """
    if info is None:
        info = collections.OrderedDict()
    info["nrows"] = data.shape[0]
    if not filters:
        info["nrows_remaining"] = data.shape[0]
        return data.copy()
    # Create filter masks for each column.
    masks = []
    for col_name, tuple_ in filters.items():
        if not isinstance(tuple_[0], tuple):
            tuple_ = (tuple_,)  # type: ignore
        for comparison_method, val in tuple_:
            dbg.dassert_in(
                comparison_method, ("eq", "ne", "le", "lt", "ge", "gt")
            )
            mask = getattr(data[col_name], comparison_method)(val)
            info[f"n_{col_name}_{comparison_method}_{val}"] = mask.sum()
            info[f"perc_{col_name}_{comparison_method}_{val}"] = hprint.perc(
                mask.sum(), data.shape[0]
            )
            masks.append(mask)
    masks = pd.concat(masks, axis=1)
    combined_mask = _combine_masks(masks, mode, info)
    filtered_data = data.loc[combined_mask].copy()
    return filtered_data


def filter_data_by_method(
    data: pd.DataFrame,
    filters: Dict[Union[int, str], _METHOD_TO_APPLY],
    mode: str,
    info: Optional[collections.OrderedDict] = None,
) -> pd.DataFrame:
    """
    Filter dataframe by calling a method specified for each column.

    :param data: dataframe
    :param filters: `{col_name: {method: kwargs}}`, where `method` is the
        method called on the dataframe column, e.g. "isin" or "str.contains",
        and `kwargs` are the kwargs for this method
    :param mode: `and` for conjunction and `or` for disjunction of filters
    :param info: information storage
    :return: filtered dataframe
    """
    if info is None:
        info = collections.OrderedDict()
    info["nrows"] = data.shape[0]
    if not filters:
        info["nrows_remaining"] = data.shape[0]
        return data.copy()
    # Create filter masks for each column.
    masks = []
    for col_name, method_dict in filters.items():
        for method, kwargs in method_dict.items():
            mask = operator.attrgetter(method)(data[col_name])(**kwargs)
            info[f"n_{col_name}"] = mask.sum()
            info[f"perc_{col_name}"] = hprint.perc(mask.sum(), data.shape[0])
            masks.append(mask)
    masks = pd.concat(masks, axis=1)
    combined_mask = _combine_masks(masks, mode, info)
    filtered_data = data.loc[combined_mask].copy()
    return filtered_data


def _combine_masks(
    masks: pd.DataFrame, mode: str, info: collections.OrderedDict
) -> pd.Series:
    if mode == "and":
        combined_mask = masks.all(axis=1)
    elif mode == "or":
        combined_mask = masks.any(axis=1)
    else:
        raise ValueError("Invalid `mode`='%s'" % mode)
    if combined_mask.sum() == 0:
        _LOG.warning("No data remaining after filtering.")
    info["nrows_remaining"] = combined_mask.sum()
    return combined_mask


def apply_nan_mode(
    srs: pd.Series,
    mode: str = "leave_unchanged",
    info: Optional[dict] = None,
) -> pd.Series:
    """
    Process NaN values in a series according to the parameters.

    :param srs: pd.Series to process
    :param mode: method of processing NaNs
        - "leave_unchanged" - no transformation
        - "drop" - drop all NaNs
        - "ffill" - forward fill not leading NaNs
        - "ffill_and_drop_leading" - do ffill and drop leading NaNs
        - "fill_with_zero" - fill NaNs with 0
        - "strict" - raise ValueError that NaNs are detected
    :param info: information storage
    :return: transformed copy of input series
    """
    dbg.dassert_isinstance(srs, pd.Series)
    if srs.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
    if mode == "leave_unchanged":
        res = srs.copy()
    elif mode == "drop":
        res = srs.dropna().copy()
    elif mode == "ffill":
        res = srs.ffill().copy()
    elif mode == "ffill_and_drop_leading":
        res = srs.ffill().dropna().copy()
    elif mode == "fill_with_zero":
        res = srs.fillna(0).copy()
    elif mode == "strict":
        res = srs.copy()
        if srs.isna().any():
            raise ValueError(f"NaNs detected in mode `{mode}`")
    else:
        raise ValueError(f"Unrecognized mode `{mode}`")
    #
    if info is not None:
        dbg.dassert_isinstance(info, dict)
        # Dictionary should be empty.
        dbg.dassert(not info)
        info["series_name"] = srs.name
        info["num_elems_before"] = len(srs)
        info["num_nans_before"] = np.isnan(srs).sum()
        info["num_elems_removed"] = len(srs) - len(res)
        info["num_nans_imputed"] = (
            info["num_nans_before"] - info["num_elems_removed"]
        )
        info["percentage_elems_removed"] = (
            100.0 * info["num_elems_removed"] / info["num_elems_before"]
        )
        info["percentage_elems_imputed"] = (
            100.0 * info["num_nans_imputed"] / info["num_elems_before"]
        )
    return res


def infer_sampling_points_per_year(data: Union[pd.Series, pd.DataFrame]) -> float:
    """
    Return the number of index time points per year.

    TODO(*): Consider extending to all frequencies and count points by
        explicitly building indices of the given frequency.

    :param data: series or dataframe with non-null `data.index.freq`
    :return: number of time points per year (approximate)
    """
    dbg.dassert(data.index.freq)
    freq = data.index.freq
    # TODO(*): Make start, end dates parameters that can be passed in.
    return compute_points_per_year_for_given_freq(freq)


@functools.lru_cache()
def compute_points_per_year_for_given_freq(freq: str) -> float:
    """
    Return the number of index time points per year.

    :param freq: string identifier of date frequency
    :return: number of time points per year (approximate)
    """
    # `pd.date_range` breaks for zero-period frequencies, so we need to work
    # around that.
    try:
        # Leap years: 2012, 2016.
        points_in_span = pd.date_range(
            freq=freq, start="2012-01-01", end="2019-12-31"
        ).size
        span_in_years = 8
        points_per_year: float = points_in_span / span_in_years
        return points_per_year
    except ZeroDivisionError:
        return 0.0
