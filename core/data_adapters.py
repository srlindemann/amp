"""
Import as:

import core.data_adapters as adpt
"""

import functools
import logging
from typing import Dict, Generator, Iterable, List, Optional, Tuple, Union

import gluonts

# TODO(*): gluon needs these imports to work properly.
import gluonts.dataset.common as gdc  # isort: skip # noqa: F401 # pylint: disable=unused-import
import gluonts.model.forecast as gmf  # isort: skip # noqa: F401 # pylint: disable=unused-import
import numpy as np
import pandas as pd

import helpers.dbg as dbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# GluonTS
# #############################################################################


def transform_to_gluon(
    df: pd.DataFrame,
    x_vars: List[str],
    y_vars: List[str],
    frequency: Optional[str] = None,
) -> gluonts.dataset.common.ListDataset:
    """
    Transform a dataframe or multiindexed dataframe, e.g., the output of
    `core.event_study.core.build_local_timeseries` into gluonts
    `ListDataset`.

    If `y_vars` consists of one element, it will be passed to
    `ListDataset` as one dimensional time series.

    :param df: dataframe with feature and target columns
    :param frequency: pandas frequency
    :param x_vars: names of feature columns
    :param y_vars: names of target columns
    :return: gluonts `ListDataset`
    """
    dbg.dassert_isinstance(x_vars, list)
    dbg.dassert_isinstance(y_vars, list)
    dbg.dassert_is_subset(x_vars, df.columns)
    dbg.dassert_is_subset(y_vars, df.columns)
    dbg.dassert_not_intersection(
        x_vars, y_vars, "`x_vars` and `y_vars` should not intersect"
    )
    df_freq = df.index.get_level_values(-1).freq
    if frequency is None:
        dbg.dassert_is_not(
            frequency,
            None,
            "Dataframe index does not have a frequency "
            "and 'frequency' is not specified.",
        )
        frequency = df_freq
    else:
        if df_freq is not None:
            dbg.dassert_eq(
                frequency,
                df_freq,
                "Dataframe index frequency and `frequency` "
                "are different; using `frequency`",
            )
            _LOG.debug("No frequency consistency check is performed")
    if isinstance(df.index, pd.MultiIndex):
        iter_func = functools.partial(
            _create_iter_multiindex, frequency=frequency
        )
    else:
        iter_func = _create_iter_single_index
    if len(y_vars) == 1:
        y_vars = y_vars[0]
        one_dim_target = True
    else:
        one_dim_target = False
    ts = gluonts.dataset.common.ListDataset(
        iter_func(df, x_vars, y_vars),
        freq=frequency,
        one_dim_target=one_dim_target,
    )
    return ts


def transform_from_gluon(
    gluon_ts: gluonts.dataset.common.ListDataset,
    x_vars: Iterable[str],
    y_vars: Iterable[str],
    index_name: Optional[str],
) -> pd.DataFrame:
    """
    Transform gluonts `ListDataset` into a dataframe.

    If `gluon_ts` consists of one time series, return singly indexed
    dataframe. Else the output is of the same format as the output of
    `core.event_study.core.build_local_timeseries`.

    :param gluon_ts: gluonts `ListDataset`
    :param x_vars: names of feature columns
    :param y_vars: names of target columns
    :param index_name: name of the datetime index
    :return: if there is one time series in `gluon_ts`, return singly
        indexed dataframe; else return multiindexed dataframe
    """
    if isinstance(y_vars, str):
        y_vars = [y_vars]
    dfs = []
    for ts in iter(gluon_ts):
        start_date = ts[gluonts.dataset.field_names.FieldName.START]
        target = pd.DataFrame(ts[gluonts.dataset.field_names.FieldName.TARGET])
        if len(gluon_ts) == 1:
            idx = pd.date_range(
                start_date, periods=target.shape[0], freq=start_date.freq,
            )
        else:
            idx = [start_date] * target.shape[0]
        target.index = idx
        target.columns = y_vars
        features = pd.DataFrame(
            ts[gluonts.dataset.field_names.FieldName.FEAT_DYNAMIC_REAL],
            index=idx,
        )
        features.columns = x_vars
        dfs.append((features, target))
    df = _convert_tuples_list_to_df(dfs, index_name)
    return df


# TODO(Julia): Add support of multitarget models.
def transform_from_gluon_forecasts(
    forecasts: List[gluonts.model.forecast.SampleForecast],
) -> pd.Series:
    """
    Transform the output of
    `gluonts.evaluation.backtest.make_evaluation_predictions` into a
    dataframe.

    The output is multiindexed series of the
    `(len(forecasts) * prediction_length * num_samples, )` shape:
          - level 0 index contains integer offsets
          - level 1 index contains start dates of forecasts
          - level 2 index contains indices of traces (sample paths)
    We require start dates of forecasts to be unique, so they serve as
    unique identifiers for forecasts.

    :param forecasts: first value of the `make_evaluation_predictions`
        output
    :return: multiindexed series
    """
    start_dates = [forecast.start_date for forecast in forecasts]
    dbg.dassert_no_duplicates(
        start_dates, "Forecast start dates should be unique"
    )
    forecast_dfs = [
        _transform_from_gluon_forecast_entry(forecast) for forecast in forecasts
    ]
    return pd.concat(forecast_dfs).sort_index(level=0)


def _convert_tuples_list_to_df(
    dfs: List[Tuple[pd.DataFrame, pd.DataFrame]], index_name: Optional[str],
) -> pd.DataFrame:
    def _process_features_target(
        features: pd.DataFrame, target: pd.DataFrame
    ) -> pd.DataFrame:
        combined = pd.concat([features, target], axis=1)
        combined.index = pd.MultiIndex.from_arrays(
            [range(combined.shape[0]), combined.index]
        )
        return combined

    dfs = dfs.copy()
    dfs = [_process_features_target(features, target) for features, target in dfs]
    # If `ListDataset` contains only one gluon time series, return
    # singly indexed dataframe; else return a multiindexed dataframe.
    if len(dfs) == 1:
        df = dfs[0]
        df = df.droplevel(0)
        df.index.name = index_name
    else:
        df = pd.concat(dfs, sort=False)
        df.sort_index(level=0, inplace=True)
        df.index.names = [None, index_name]
    return df


def _create_iter_single_index(
    df: pd.DataFrame, x_vars: List[str], y_vars: Union[str, List[str]],
) -> Generator[Dict[str, Union[pd.DataFrame, pd.Timestamp]], None, None]:
    dbg.dassert_isinstance(df.index, pd.DatetimeIndex)
    yield {
        gluonts.dataset.field_names.FieldName.TARGET: df[y_vars],
        gluonts.dataset.field_names.FieldName.START: df.index[0],
        gluonts.dataset.field_names.FieldName.FEAT_DYNAMIC_REAL: df[x_vars],
    }


def _create_iter_multiindex(
    local_ts: pd.DataFrame,
    x_vars: List[str],
    y_vars: Union[str, List[str]],
    frequency: str,
) -> Generator[Dict[str, Union[pd.DataFrame, pd.Timestamp]], None, None]:
    """
    Iterate level 0 of MultiIndex and generate `data_iter` parameter for
    `gluonts.dataset.common.ListDataset`.
    """
    dbg.dassert_isinstance(local_ts.index, pd.MultiIndex)
    dbg.dassert_monotonic_index(local_ts.index.get_level_values(0).unique())
    for ts, local_ts_grid in local_ts.groupby(level=1):
        # Get start date of time series based on `t_0` timestamp and the
        # first grid index.
        first_grid_idx = local_ts_grid.index.get_level_values(0)[0]
        start_date = ts + pd.Timedelta(f"{first_grid_idx}{frequency}")
        df = local_ts_grid.droplevel(0)
        df.index = [start_date] * df.shape[0]
        yield from _create_iter_single_index(df, x_vars, y_vars)


def _transform_from_gluon_forecast_entry(
    forecast_entry: gluonts.model.forecast.SampleForecast,
) -> pd.Series:
    df = pd.DataFrame(forecast_entry.samples)
    unstacked = df.unstack()
    # Add start date as 0 level index.
    unstacked = pd.concat(
        {forecast_entry.start_date: unstacked},
        names=["start_date", "offset", "trace"],
    )
    # This will change the index levels to
    # `["offset", "start_date", "trace"]`.
    unstacked.index = unstacked.index.swaplevel(0, 1)
    return unstacked


# #############################################################################
# SkLearn
# #############################################################################


def transform_to_sklearn(
    df: pd.DataFrame, x_vars: List[str], y_vars: List[str]
) -> Tuple[np.array, np.array]:
    """
    Transform pd.DataFrame into sklearn model inputs.

    Sklearn requires separate feature and target inputs, both with range
    index. To undo the transformation into sklrean format, we need the
    original index and column names.

    :param df: input dataset
    :param x_vars: names of feature columns
    :param y_vars: names of target columns
    :return: (x_vals, y_vals)
    """
    dbg.dassert_not_intersection(
        x_vars, y_vars, "`x_vars` and `y_vars` should not intersect"
    )
    dbg.dassert(
        df.notna().values.any(), "The dataframe should not contain `None` values"
    )
    df = df.reset_index()
    x_vals = df[x_vars].values
    y_vals = df[y_vars].values
    return x_vals, y_vals


def transform_from_sklearn(
    idx: pd.Index, vars_: List[str], vals: np.array,
) -> pd.DataFrame:
    """
    Add index and column names to sklearn output.

    :param idx: data index
    :param vars_: names of feature columns
    :param vals: features data
    :return: dataframe with an index an column names
    """
    dbg.dassert_eq(
        vals.shape,
        (len(idx), len(vars_)),
        "The shape of `vals` does not match the length of `idx` and `vars_`",
    )
    x = pd.DataFrame(vals, index=idx, columns=vars_)
    return x