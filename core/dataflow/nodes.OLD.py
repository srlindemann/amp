import abc
import collections
import copy
import datetime
import functools
import inspect
import io
import logging
import os
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

import core.artificial_signal_generators as cartif
import core.finance as cfinan
import core.signal_processing as csigna
import helpers.dbg as dbg
from core.dataflow.core import Node

_LOG = logging.getLogger(__name__)


# TODO(*): Create a dataflow types file in dataflow/core/types.py.
# TODO(*): As a convention we don't need to add _TYPE.
# TODO(*): _COL_TYPE -> COL_NAME
_COL_TYPE = Union[int, str]
# TODO(*): -> DATETIME
_PANDAS_DATE_TYPE = Union[str, pd.Timestamp, datetime.datetime]

# TIMEDELTA = Union[pd.DateOffset, pd.Timedelta, str]

# TODO(gp): Should we allow None to indicate beginning / end of time?
#  This complicates the code to simplify the life of the client.
#  Instead we can define constants START_DATETIME=..., END_DATETIME
# Intervals are interpreted as closed [a, b].
# TODO(gp): Should we stick to usual [a, b) interpretation everywhere for
#  consistency? This might be a big change.
# INTERVAL = List[Tuple[Optional[DATETIME], Optional[DATETIME]]]

# INFO = collections.OrderedDict[str, Any]

# This seems common, but not sure if it is worth it to obscure the meaning
#  for saving few chars.
# NODE_OUTPUT = Dict[str, pd.DataFrame]

# Defining types
# Pros:
# - consistency and easy to read
# Cons:
# - a new symbol to look up (but PyCharm is your BFF here)

# def validate_input_output_df(df):
#     if single_index:
#         dbg.dassert_no_duplicates(items)
#     idx = df.index
#     dbg.dassert_isindex(idx, datetime)
#     dbg.dassert_is_monotonic(idx)
#     dbg.dassert_strictly_increasing_index(self.df)


# #############################################################################
# Abstract Node classes with sklearn-style interfaces
# #############################################################################


class FitPredictNode(Node, abc.ABC):
    """
    Define an abstract class with sklearn-style `fit` and `predict` functions.

    Nodes may store a dictionary of information for each method
    following the method's invocation.
    """

    def __init__(
        self,
        nid: str,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
    ) -> None:
        # TODO(gp): I'd force the clients to be explicit here?
        if inputs is None:
            inputs = ["df_in"]
        if outputs is None:
            outputs = ["df_out"]
        super().__init__(nid=nid, inputs=inputs, outputs=outputs)
        # Dict 'method name -> various info'.
        self._info: Dict[str, Any] = collections.OrderedDict()

    @abc.abstractmethod
    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Fit this node's model using the input data stored in `df_in`.

        :return: TODO(gp)
        """

    @abc.abstractmethod
    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Use this node's model to predict on the input data stored in `df_in`.

        :return: TODO(gp)
        """

    def get_fit_state(self) -> Dict[str, Any]:
        """
        TODO(gp): ?
        """
        return {}

    def set_fit_state(self, fit_state: Dict[str, Any]) -> None:
        """
        TODO(gp): ?
        """

    def get_info(
        self, method: str
    ) -> Optional[Union[str, collections.OrderedDict]]:
        """
        Return the information stored in this node for the given `method`.
        """
        # TODO(Paul): Add a dassert_getattr function to use here and in core.
        dbg.dassert_isinstance(method, str)
        dbg.dassert(getattr(self, method))
        if method in self._info.keys():
            return self._info[method]
        # TODO(Paul): Maybe crash if there is no info.
        _LOG.warning("No info found for nid=%s, method=%s", self.nid, method)
        return None

    # TODO(gp): values -> info
    # TODO(gp): We should merge the dicts instead of overwrite, to keep
    #  classes composable. Otherwise a derived class overrides the values.
    def _set_info(self, method: str, values: collections.OrderedDict) -> None:
        dbg.dassert_isinstance(method, str)
        dbg.dassert(getattr(self, method))
        dbg.dassert_isinstance(values, collections.OrderedDict)
        # Save the info in the node: we make a copy just to be safe.
        self._info[method] = copy.copy(values)


# TODO(gp): Is this still abstract? What methods are still not over-written?
class DataSource(FitPredictNode, abc.ABC):
    """
    A source node that can be configured for cross-validation.

    Being a source, this node doesn't have any input but only outputs.
    """

    def __init__(self, nid: str, outputs: Optional[List[str]] = None) -> None:
        if outputs is None:
            outputs = ["df_out"]
        # Do not allow any empty list.
        dbg.dassert(outputs)
        super().__init__(nid, inputs=[], outputs=outputs)
        #
        # TODO(gp): I'd make it protected _df at least.
        self.df = None
        self._fit_intervals = None
        self._predict_intervals = None
        self._predict_idxs = None

    def set_fit_intervals(self, intervals: List[Tuple[Any, Any]]) -> None:
        """
        Set the intervals to be used when fitting the model.

        :param intervals: closed time intervals like [start1, end1],
            [start2, end2]. `None` boundary is interpreted as data start/end
        """
        self._validate_intervals(intervals)
        self._fit_intervals = intervals

    def get_single_output_name(self):
        # For now most of the data source nodes assume that there is a single
        # output when they return `{"df_out": df}`.
        # This makes the assumption explicit.
        dbg.dassert_eq(len(self.output_names), 1)
        return self.output_names[0]

    # `DataSource` does not have a `df_in` in either `fit` or `predict` as a
    # typical `FitPredictNode` does.
    # pylint: disable=arguments-differ
    def fit(self) -> Dict[str, pd.DataFrame]:
        """
        :return: training set as df
        """
        if self._fit_intervals is not None:
            # Compute the union of all the indices.
            # TODO(gp): What if there are None in the interval?
            idx_slices = [
                self.df.loc[interval[0] : interval[1]].index
                for interval in self._fit_intervals
            ]
            idx = functools.reduce(lambda x, y: x.union(y), idx_slices)
            # TODO(gp): Add a
            # dbg.dassert_issubset(idx, self.dx.index) ?
            fit_df = self.df.loc[idx]
        else:
            fit_df = self.df
        dbg.dassert(not fit_df.empty)
        fit_df = fit_df.copy()
        # Compute the info for `fit_df`.
        info = collections.OrderedDict()
        info["fit_df_info"] = get_df_info_as_string(fit_df)
        self._set_info("fit", info)
        return {self.get_single_output_name(): fit_df}

    def set_predict_intervals(self, intervals: List[Tuple[Any, Any]]) -> None:
        """
        :param intervals: closed time intervals like [start1, end1],
            [start2, end2]. `None` boundary is interpreted as data start/end

        TODO(*): Warn if intervals overlap with `fit` intervals.
        TODO(*): Maybe enforce that the intervals be ordered.
        """
        self._validate_intervals(intervals)
        self._predict_intervals = intervals

    # pylint: disable=arguments-differ
    def predict(self) -> Dict[str, pd.DataFrame]:
        """
        :return: test set as df
        """
        # TODO(gp): Factor it out since this is similar enough to `fit`.
        if self._predict_intervals is not None:
            idx_slices = [
                self.df.loc[interval[0] : interval[1]].index
                for interval in self._predict_intervals
            ]
            idx = functools.reduce(lambda x, y: x.union(y), idx_slices)
            predict_df = self.df.loc[idx].copy()
        else:
            predict_df = self.df.copy()
        dbg.dassert(not predict_df.empty)
        #
        info = collections.OrderedDict()
        info["predict_df_info"] = get_df_info_as_string(predict_df)
        self._set_info("predict", info)
        #
        # return {self.get_single_output_name(): predict_df}
        return {"df_out": df_out}

    # TODO(gp): Make df protected since there is an accessor. We can use
    #  a property.
    def get_df(self) -> pd.DataFrame:
        dbg.dassert_is_not(self.df, None, "No DataFrame found!")
        return self.df

    # TODO(gp): I'd make free standing in dataflow/core/intervals.py
    @staticmethod
    def _validate_intervals(intervals: List[Tuple[Any, Any]]) -> None:
        dbg.dassert_isinstance(intervals, list)
        for interval in intervals:
            dbg.dassert_eq(len(interval), 2)
            if interval[0] is not None and interval[1] is not None:
                dbg.dassert_lte(interval[0], interval[1])
        # TODO(gp): Should we enforce that intervals are not overlapping?


class Transformer(FitPredictNode, abc.ABC):
    """
    Stateless single-input single-output node with an abstract `transform`.
    """

    # TODO(Paul): Consider giving users the option of renaming the single
    #  input and single output (but verify there is only one of each).
    def __init__(self, nid: str) -> None:
        super().__init__(nid)

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        # TODO(gp): -> validate_df
        dbg.dassert_no_duplicates(df_in.columns)
        # Transform the input df.
        df_out, info = self._transform(df_in)
        # Compute info.
        self._set_info("fit", info)
        # TODO(gp): -> validate_df
        dbg.dassert_no_duplicates(df_out.columns)
        # return {self.get_single_output_name(): df_out}
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        # TODO(gp): -> validate_df
        dbg.dassert_no_duplicates(df_in.columns)
        # Transform the input df.
        df_out, info = self._transform(df_in)
        # Compute info.
        self._set_info("predict", info)
        # TODO(gp): -> validate_df
        dbg.dassert_no_duplicates(df_out.columns)
        # return {self.get_single_output_name(): df_out}
        return {"df_out": df_out}

    @abc.abstractmethod
    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        """
        :return: transformed df, info
        """


# #############################################################################
# Data source nodes
# #############################################################################

# TODO(gp): Move all DataSource nodes in nodes_data_source.py?


class ReadDataFromDf(DataSource):
    """
    Data source node that feed data from the given `df`.
    """

    def __init__(self, nid: str, df: pd.DataFrame) -> None:
        super().__init__(nid)
        # TODO(gp): -> validate_input_output_df or is it done by the superclass?
        dbg.dassert_isinstance(df, pd.DataFrame)
        self.df = df


# TODO(gp): -> FileDataSource? The file can be on S3.
class DiskDataSource(DataSource):
    """
    Data source node that reads data from a file.
    """

    def __init__(
        self,
        nid: str,
        file_path: str,
        timestamp_col: Optional[str] = None,
        # TODO(gp): -> start_dt, end_dt?
        start_date: Optional[_PANDAS_DATE_TYPE] = None,
        end_date: Optional[_PANDAS_DATE_TYPE] = None,
        reader_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create data source node reading CSV or parquet data from disk.

        :param nid: node identifier
        :param file_path: path to the file (CSV or Parquet file)
        # TODO(*): Don't the readers support this already?
        :param timestamp_col: name of the timestamp column. If `None`, assume
            that index contains timestamps
        :param start_date: data start date in timezone of the dataset, included
        :param end_date: data end date in timezone of the dataset, included
        :param reader_kwargs: kwargs for the data reading function
        """
        super().__init__(nid)
        self._file_path = file_path
        self._timestamp_col = timestamp_col
        self._start_date = start_date
        self._end_date = end_date
        self._reader_kwargs = reader_kwargs or {}

    # TODO(gp): How can it be Optional? A SourceNode should always read.
    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        """
        :return: training set as df
        """
        self._lazy_load()
        return super().fit()

    # TODO(gp): What about predict?

    def _read_data(self) -> None:
        """
        Read the data from the passed `file_path`.
        """
        # Get the extension.
        ext = os.path.splitext(self._file_path)[-1]
        # Pick the function to use.
        if ext == ".csv":
            if "index_col" not in self._reader_kwargs:
                self._reader_kwargs["index_col"] = 0
            read_data = pd.read_csv
        elif ext == ".pq":
            read_data = pd.read_parquet
        else:
            raise ValueError("Invalid file extension='%s'" % ext)
        # Read the data.
        self.df = read_data(self._file_path, **self._reader_kwargs)

    def _process_data(self) -> None:
        # Ensure that the index is valid.
        if self._timestamp_col is not None:
            # TODO(gp): Do we need a drop=True?
            self.df.set_index(self._timestamp_col, inplace=True)
        self.df.index = pd.to_datetime(self.df.index)
        dbg.dassert_strictly_increasing_index(self.df)
        # Trim the data.
        self.df = self.df.loc[self._start_date : self._end_date]
        dbg.dassert(not self.df.empty, "Dataframe is empty")

    # TODO(gp): A little thin and used only once: I would inline to not
    #  introduce another symbol?
    def _lazy_load(self) -> None:
        if self.df is not None:
            return
        self._read_data()
        self._process_data()


class ArmaGenerator(DataSource):
    """
    A node for generating price data from ARMA process returns.
    """

    def __init__(
        self,
        nid: str,
        # Index parameters.
        frequency: str,
        start_date: _PANDAS_DATE_TYPE,
        end_date: _PANDAS_DATE_TYPE,
        # ARMA parameters.
        ar_coeffs: Optional[List[float]] = None,
        ma_coeffs: Optional[List[float]] = None,
        scale: Optional[float] = None,
        burnin: Optional[float] = None,
        seed: Optional[float] = None,
    ) -> None:
        """
        The ARMA parameters are the same as `cartif.ArmaProcess`.

        :param start_date, end_date, frequency: used to generate the datetime index
        """
        super().__init__(nid)
        # Save parameters.
        self._frequency = frequency
        self._start_date = start_date
        self._end_date = end_date
        self._ar_coeffs = ar_coeffs or [0]
        self._ma_coeffs = ma_coeffs or [0]
        self._scale = scale or 1
        self._burnin = burnin or 0
        self._seed = seed
        # Initialize process.
        self._arma_process = cartif.ArmaProcess(
            ar_coeffs=self._ar_coeffs, ma_coeffs=self._ma_coeffs
        )

    # TODO(gp): There is a common idiom where fit and predict are the same
    #  besides a few small difference. Maybe we can use a Mixin with an
    #  abstract method with the common code?
    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        """
        The fit/predict dataframe contain "close" and "vol" columns.
        """
        self._lazy_load()
        return super().fit()

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().predict()

    def _lazy_load(self) -> None:
        if self.df is not None:
            return
        rets = self._arma_process.generate_sample(
            date_range_kwargs={
                "start": self._start_date,
                "end": self._end_date,
                "freq": self._frequency,
            },
            scale=self._scale,
            burnin=self._burnin,
            seed=self._seed,
        )
        # Cumulatively sum to generate a price series (implicitly assumes the
        # returns are log returns; at small enough scales and short enough
        # times this is practically interchangeable with percentage returns).
        # TODO(*): Allow specification of annualized target volatility.
        prices = np.exp(0.1 * rets.cumsum())
        prices.name = "close"
        # Convert to a df.
        self.df = prices.to_frame()
        # Trim to [start_date, end_date].
        self.df = self.df.loc[self._start_date : self._end_date]
        # Use constant volume (for now).
        # TODO(gp): Call it "Volume".
        self.df["vol"] = 100


class MultivariateNormalGenerator(DataSource):
    """
    A node for generating price data from multivariate normal returns.
    """

    def __init__(
        self,
        nid: str,
        # Index parameters.
        frequency: str,
        start_date: _PANDAS_DATE_TYPE,
        end_date: _PANDAS_DATE_TYPE,
        # Process parameters.
        dim: int,
        seed: Optional[float] = None,
    ) -> None:
        super().__init__(nid)
        # Save parameters.
        self._frequency = frequency
        self._start_date = start_date
        self._end_date = end_date
        self._dim = dim
        self._seed = seed
        self._multivariate_normal_process = cartif.MultivariateNormalProcess()
        # Initialize process with appropriate dimension.
        self._multivariate_normal_process.set_cov_from_inv_wishart_draw(
            dim=self._dim, seed=self._seed
        )

    # TODO(gp): Can it be Optional?
    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        """
        The fit/predict dataframe contain "close" and "vol" columns.
        """
        self._lazy_load()
        return super().fit()

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().predict()

    def _lazy_load(self) -> None:
        if self.df is not None:
            return
        rets = self._multivariate_normal_process.generate_sample(
            date_range_kwargs={
                "start": self._start_date,
                "end": self._end_date,
                "freq": self._frequency,
            },
            seed=self._seed,
        )
        # Cumulatively sum to generate a price series (implicitly assumes the
        # returns are log returns; at small enough scales and short enough
        # times this is practically interchangeable with percentage returns).
        # TODO(*): We hard-code a scale factor to make these look more
        #     realistic, but it would be better to allow the user to specify
        #     a target annualized volatility.
        prices = np.exp(0.1 * rets.cumsum())
        prices = prices.rename(columns=lambda x: "MN" + str(x))
        # Use constant volume (for now).
        volume = pd.DataFrame(
            index=prices.index, columns=prices.columns, data=100
        )
        df = pd.concat([prices, volume], axis=1, keys=["close", "vol"])
        self.df = df
        self.df = self.df.loc[self._start_date : self._end_date]


# #############################################################################
# Plumbing nodes
# #############################################################################


class YConnector(FitPredictNode):
    """
    Create an output dataframe from two input dataframes.
    """

    # TODO(Paul): Support different input/output names.
    def __init__(
        self,
        nid: str,
        connector_func: Callable[..., pd.DataFrame],
        connector_kwargs: Optional[Any] = None,
    ) -> None:
        """
        :param nid: unique node id
        :param connector_func: function used to connect the input dataframes
            into a single one. E.g.,
            - Merge
              ```
              connector_func = lambda df_in1, df_in2, connector_kwargs:
                  df_in1.merge(df_in2, **connector_kwargs)
              ```
            - Reindexing
              ```
              connector_func = lambda df_in1, df_in2, connector_kwargs:
                  df_in1.reindex(index=df_in2.index, **connector_kwargs)
              ```
            - User-defined functions
              ```
              # my_func(df_in1, df_in2, **connector_kwargs)
              connector_func = my_func
              ```
        :param connector_kwargs: kwargs associated with `connector_func`
        """
        super().__init__(nid, inputs=["df_in1", "df_in2"])
        self._connector_func = connector_func
        self._connector_kwargs = connector_kwargs or {}
        self._df_in1_col_names = None
        self._df_in2_col_names = None

    def get_df_in1_col_names(self) -> List[str]:
        """
        Allow introspection on column names of input dataframe #1.
        """
        _check_col_names(self._df_in1_col_names)
        return self._df_in1_col_names

    def get_df_in2_col_names(self) -> List[str]:
        """
        Allow introspection on column names of input dataframe #2.
        """
        _check_col_names(self._df_in2_col_names)
        return self._df_in2_col_names

    # pylint: disable=arguments-differ
    def fit(
        self, df_in1: pd.DataFrame, df_in2: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        df_out, info = self._apply_connector_func(df_in1, df_in2)
        self._set_info("fit", info)
        # TODO(gp): -> get_single_output_name()
        return {"df_out": df_out}

    # pylint: disable=arguments-differ
    def predict(
        self, df_in1: pd.DataFrame, df_in2: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        df_out, info = self._apply_connector_func(df_in1, df_in2)
        self._set_info("predict", info)
        return {"df_out": df_out}

    def _apply_connector_func(
        self, df_in1: pd.DataFrame, df_in2: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        # Apply the connector function.
        self._df_in1_col_names = df_in1.columns.tolist()
        self._df_in2_col_names = df_in2.columns.tolist()
        df_out = self._connector_func(df_in1, df_in2, **self._connector_kwargs)
        # TODO(Paul): Add meaningful info.
        info = collections.OrderedDict()
        info["df_merged_info"] = get_df_info_as_string(df_out)
        return df_out, info

    @staticmethod
    def _check_col_names(col_names: List[str]) -> None:
        dbg.dassert_is_not(
            col_names,
            None,
            "No column names. This may indicate an invocation prior to "
            "graph execution.",
        )


# #############################################################################
# Transformer nodes
# #############################################################################


# TODO(gp): IMO I'd make it a function rather than relying on the hidden
#  self._transformed_col_names to plug it into a function.
class ColModeMixin:
    """
    Select columns to propagate in output dataframe.
    """

    def _apply_col_mode(
        self,
        df_in: pd.DataFrame,
        df_out: pd.DataFrame,
        # -> List[str] ?
        cols: Optional[List[Any]] = None,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Merge transformed dataframe with original dataframe.

        :param df_in: original dataframe
        :param df_out: transformed dataframe (not changed)
        :param cols: columns in `df_in` that were transformed to obtain
            `df_out`
            - `None` defaults to all columns in `df_out`
        :param col_mode: determines what columns are propagated.
            - It defaults to "merge all".
            - `None`: TODO(gp): ?
            - "merge_all": perform an outer merge
            - "replace_selected": TODO(gp): ?
            - "replace_all": TODO(gp): ?
        :param col_rename_func: function for naming transformed columns
            - E.g., `lambda x: "zscore_" + x`
            - `None` defaults to identity transform
        :return: dataframe with columns selected by `col_mode`
        """
        # TODO(gp): -> validate_input_output_df?
        dbg.dassert_isinstance(df_in, pd.DataFrame)
        dbg.dassert_isinstance(df_out, pd.DataFrame)
        #
        dbg.dassert(cols is None or isinstance(cols, list))
        cols = cols or df_out.columns.tolist()
        #
        col_rename_func = col_rename_func or (lambda x: x)
        dbg.dassert_isinstance(col_rename_func, collections.Callable)
        #
        col_mode = col_mode or "merge_all"
        # Rename transformed columns using the passed function.
        df_out = df_out.rename(columns=col_rename_func)
        self._transformed_col_names = df_out.columns.tolist()
        # Select columns to return.
        if col_mode == "merge_all":
            # `df_in` and `df_out` must have common columns.
            shared_columns = df_out.columns.intersection(df_in.columns)
            dbg.dassert(
                shared_columns.empty,
                "Transformed column names `%s` conflict with existing column "
                "names `%s`.",
                df_out.columns,
                df_in.columns,
            )
            # Outer merge.
            df_out = df_in.merge(
                df_out, how="outer", left_index=True, right_index=True
            )
        elif col_mode == "replace_selected":
            df_in_not_transformed_cols = df_in.columns.drop(cols)
            dbg.dassert(
                df_in_not_transformed_cols.intersection(df_out.columns).empty,
                "Transformed column names `%s` conflict with existing column "
                "names `%s`.",
                df_out.columns,
                df_in_not_transformed_cols,
            )
            df_out = df_in.drop(columns=cols).merge(
                df_out, left_index=True, right_index=True
            )
        elif col_mode == "replace_all":
            pass
        else:
            dbg.dfatal("Unsupported column mode `%s`", col_mode)
        dbg.dassert_no_duplicates(df_out.columns.tolist())
        return df_out


class ColumnTransformer(Transformer, ColModeMixin):
    """
    Perform non-index modifying changes of columns.
    """

    def __init__(
        self,
        nid: str,
        transformer_func: Callable[..., pd.DataFrame],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        # TODO(Paul): May need to assume `List` instead.
        cols: Optional[Iterable[str]] = None,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        :param nid: unique node id
        :param transformer_func: df -> df. The keyword `info` (if present) is
            assumed to have a specific semantic meaning. If present,
                - An empty dict is passed in to this `info`
                - The resulting (populated) dict is included in the node's
                  `_info`
        :param transformer_kwargs: transformer_func kwargs
        :param cols, col_rename_func, col_mode: same as `ColModeMixin`
        :param nan_mode: `leave_unchanged` or `drop`. If `drop`, applies to all
            columns simultaneously.
        """
        super().__init__(nid)
        if cols is not None:
            dbg.dassert_isinstance(cols, list)
        # Save parameters.
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        self._cols = cols
        self._col_rename_func = col_rename_func
        self._col_mode = col_mode
        self._nan_mode = nan_mode or "leave_unchanged"
        # Store the list of columns after the transformation.
        self._transformed_col_names = None
        # TODO(gp): What does it mean?
        self._fit_cols = cols

    @property
    def transformed_col_names(self) -> List[str]:
        dbg.dassert_is_not(
            self._transformed_col_names,
            None,
            "No transformed column names. This may indicate an invocation prior "
            "to graph execution.",
        )
        return self._transformed_col_names

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        # TODO(gp): Why two copies?
        df_in = df.copy()
        df = df.copy()
        if self._fit_cols is None:
            # TODO(gp): Can df has no columns?
            self._fit_cols = df.columns.tolist() or self._cols
        if self._cols is None:
            dbg.dassert_set_eq(self._fit_cols, df.columns)
        df = df[self._fit_cols]
        idx = df.index
        # Handle the nan mode.
        if self._nan_mode == "leave_unchanged":
            pass
        elif self._nan_mode == "drop":
            df = df.dropna()
        else:
            raise ValueError(f"Unrecognized `nan_mode` {self._nan_mode}")
        # Initialize container to store info (e.g., auxiliary stats) in the
        # node.
        info = collections.OrderedDict()
        # Perform the column transformation operations.
        # Introspect to see whether `_transformer_func` contains an `info`
        # parameter. If so, inject an empty dict to be populated when
        # `_transformer_func` is executed.
        func_sig = inspect.signature(self._transformer_func)
        if "info" in func_sig.parameters:
            func_info = collections.OrderedDict()
            df = self._transformer_func(
                df, info=func_info, **self._transformer_kwargs
            )
            info["func_info"] = func_info
        else:
            df = self._transformer_func(df, **self._transformer_kwargs)
        df = df.reindex(index=idx)
        # TODO(Paul): Consider supporting the option of relaxing or
        #  foregoing this check.
        dbg.dassert(
            df.index.equals(df_in.index),
            "Input/output indices differ but are expected to be the same!",
        )
        # Maybe merge transformed columns with a subset of input df columns.
        df = self._apply_col_mode(
            df_in,
            df,
            cols=df.columns.tolist(),
            col_rename_func=self._col_rename_func,
            col_mode=self._col_mode,
        )
        #
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


# TODO(gp): Lots of same code. Can we just wrap ColumnTransformer and check
#  that has one column and then transform into a series?
class SeriesTransformer(Transformer, ColModeMixin):
    """
    Perform non-index modifying changes of columns.
    """

    def __init__(
        self,
        nid: str,
        transformer_func: Callable[..., pd.DataFrame],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        # TODO(Paul): May need to assume `List` instead.
        cols: Optional[Iterable[Union[int, str]]] = None,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        Same interface as ColumnTransformer but transformer_func is srs -> df.
        """
        super().__init__(nid)
        if cols is not None:
            dbg.dassert_isinstance(cols, list)
        self._cols = cols
        self._col_rename_func = col_rename_func
        self._col_mode = col_mode
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        # Store the list of columns after the transformation.
        self._transformed_col_names = None
        self._nan_mode = nan_mode or "leave_unchanged"
        self._fit_cols = cols

    @property
    def transformed_col_names(self) -> List[str]:
        dbg.dassert_is_not(
            self._transformed_col_names,
            None,
            "No transformed column names. This may indicate "
            "an invocation prior to graph execution.",
        )
        return self._transformed_col_names

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df_in = df.copy()
        df = df.copy()
        if self._fit_cols is None:
            self._fit_cols = df.columns.tolist() or self._cols
        if self._cols is None:
            dbg.dassert_set_eq(self._fit_cols, df.columns)
        df = df[self._fit_cols]
        idx = df.index
        # Initialize container to store info (e.g., auxiliary stats) in the
        # node.
        info = collections.OrderedDict()
        info["func_info"] = collections.OrderedDict()
        func_info = info["func_info"]
        srs_list = []
        for col in df.columns:
            col_info = collections.OrderedDict()
            srs = df[col]
            if self._nan_mode == "leave_unchanged":
                pass
            elif self._nan_mode == "drop":
                srs = srs.dropna()
            else:
                raise ValueError(f"Unrecognized `nan_mode` {self._nan_mode}")
            # Perform the column transformation operations.
            # Introspect to see whether `_transformer_func` contains an `info`
            # parameter. If so, inject an empty dict to be populated when
            # `_transformer_func` is executed.
            func_sig = inspect.signature(self._transformer_func)
            if "info" in func_sig.parameters:
                func_info = collections.OrderedDict()
                srs = self._transformer_func(
                    srs, info=col_info, **self._transformer_kwargs
                )
                func_info[col] = col_info
            else:
                srs = self._transformer_func(srs, **self._transformer_kwargs)
            if self._col_rename_func is not None:
                srs.name = self._col_rename_func(col)
            else:
                srs.name = col
            srs_list.append(srs)
        info["func_info"] = func_info
        df = pd.concat(srs_list, axis=1)
        df = df.reindex(index=idx)
        # TODO(Paul): Consider supporting the option of relaxing or
        # foregoing this check.
        dbg.dassert(
            df.index.equals(df_in.index),
            "Input/output indices differ but are expected to be the same!",
        )
        # Maybe merge transformed columns with a subset of input df columns.
        df = self._apply_col_mode(
            df_in,
            df,
            cols=df.columns.tolist(),
            col_rename_func=None,
            col_mode=self._col_mode,
        )
        #
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


# TODO(gp): I understand that it was better to branch and modify the code,
#  but now there is lots of copy/paste code. I would factor out the code to
#  work on series and then invoke it from all the transformers.
class MultiindexSeriesTransformer(Transformer):
    """
    Perform non-index modifying changes of columns.

    When operating on multiple columns, this applies the transformer function
    one series at a time. Additionally, NaN-handling is performed "locally"
    (one series at a time, without regard to NaNs in other columns).

    Example: df like
    ```
                          close                     vol
                          MN0   MN1    MN2   MN3    MN0    MN1    MN2    MN3
    2010-01-04 10:30:00 -2.62  8.81  14.93 -0.88  100.0  100.0  100.0  100.0
    2010-01-04 11:00:00 -2.09  8.27  16.75 -0.92  100.0  100.0  100.0  100.0
    2010-01-04 11:30:00 -2.52  6.97  12.56 -1.52  100.0  100.0  100.0  100.0
    2010-01-04 12:00:00 -2.54  5.30   8.90 -1.54  100.0  100.0  100.0  100.0
    2010-01-04 12:30:00 -1.91  2.02   4.65 -1.77  100.0  100.0  100.0  100.0
    ```

    Then, e.g., to calculate, returns, we could take:
      - `in_col_group = ("close", )`
      - `out_col_group = ("ret_0", )`

    The transformer_func and `nan_mode` would operate on the price columns
    individually and return one return column per price column, e.g.,
    generating

    ```
                          ret_0                   close                     vol
                          MN0   MN1   MN2   MN3   MN0   MN1    MN2   MN3    MN0    MN1    MN2    MN3
    2010-01-04 10:30:00 -0.02  0.11  0.16 -0.35 -2.62  8.81  14.93 -0.88  100.0  100.0  100.0  100.0
    2010-01-04 11:00:00 -0.20 -0.06  0.12  0.04 -2.09  8.27  16.75 -0.92  100.0  100.0  100.0  100.0
    2010-01-04 11:30:00  0.20 -0.16 -0.25  0.66 -2.52  6.97  12.56 -1.52  100.0  100.0  100.0  100.0
    2010-01-04 12:00:00  0.01 -0.24 -0.29  0.01 -2.54  5.30   8.90 -1.54  100.0  100.0  100.0  100.0
    2010-01-04 12:30:00 -0.25 -0.62 -0.48  0.15 -1.91  2.02   4.65 -1.77  100.0  100.0  100.0  100.0
    ```
    """

    def __init__(
        self,
        nid: str,
        in_col_group: Tuple[_COL_TYPE],
        out_col_group: Tuple[_COL_TYPE],
        transformer_func: Callable[..., pd.Series],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        For reference, let:

          - N = df.columns.nlevels
          - leaf_cols = df[in_col_group].columns

        :param nid: unique node id
        :param in_col_group: a group of cols specified by the first N - 1
            levels
        :param out_col_group: new output col group names. This specifies the
            names of the first N - 1 levels. The leaf_cols names remain the
            same.
        :param transformer_func: srs -> srs
        :param transformer_kwargs: transformer_func kwargs
        :param nan_mode: `leave_unchanged` or `drop`. If `drop`, applies to
            columns individually.
        """
        super().__init__(nid)
        dbg.dassert_isinstance(in_col_group, tuple)
        dbg.dassert_isinstance(out_col_group, tuple)
        dbg.dassert_eq(
            len(in_col_group),
            len(out_col_group),
            msg="Column hierarchy depth must be preserved.",
        )
        self._in_col_group = in_col_group
        self._out_col_group = out_col_group
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        self._nan_mode = nan_mode or "leave_unchanged"
        # The leaf col names are determined from the dataframe at runtime.
        self._leaf_cols = None

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        # After indexing by `self._in_col_group`, we should have a flat column
        # index.
        dbg.dassert_eq(
            len(self._in_col_group),
            df.columns.nlevels - 1,
            "Dataframe multiindex column depth incompatible with config.",
        )
        # Do not allow overwriting existing columns.
        dbg.dassert_not_in(
            self._out_col_group,
            df.columns,
            "Desired column names already present in dataframe.",
        )
        df_in = df
        df = df[self._in_col_group].copy()
        self._leaf_cols = df.columns.tolist()
        idx = df.index
        # Initialize container to store info (e.g., auxiliary stats) in the
        # node..
        info = collections.OrderedDict()
        info["func_info"] = collections.OrderedDict()
        func_info = info["func_info"]
        srs_list = []
        for col in self._leaf_cols:
            col_info = collections.OrderedDict()
            srs = df[col]
            if self._nan_mode == "leave_unchanged":
                pass
            elif self._nan_mode == "drop":
                srs = srs.dropna()
            else:
                raise ValueError(f"Unrecognized `nan_mode` {self._nan_mode}")
            # Perform the column transformation operations.
            # Introspect to see whether `_transformer_func` contains an `info`
            # parameter. If so, inject an empty dict to be populated when
            # `_transformer_func` is executed.
            func_sig = inspect.signature(self._transformer_func)
            if "info" in func_sig.parameters:
                func_info = collections.OrderedDict()
                srs = self._transformer_func(
                    srs, info=col_info, **self._transformer_kwargs
                )
                func_info[col] = col_info
            else:
                srs = self._transformer_func(srs, **self._transformer_kwargs)
            dbg.dassert_isinstance(srs, pd.Series)
            srs.name = col
            srs_list.append(srs)
        info["func_info"] = func_info
        # Combine the series representing leaf col transformations back into a
        # single dataframe.
        df = pd.concat(srs_list, axis=1)
        # Prefix the leaf col names with level(s) specified by "out_col_group".
        df = pd.concat([df], axis=1, keys=self._out_col_group)
        df = df.reindex(index=idx)
        dbg.dassert(
            df.index.equals(df_in.index),
            "Input/output indices differ but are expected to be the same!",
        )
        df = df.merge(
            df_in,
            how="outer",
            left_index=True,
            right_index=True,
        )
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


class DataframeMethodRunner(Transformer):
    """
    Node that applies a method of data frame (e.g., `dropna`) to an input df.

    It is assumed that the method doesn't change the df in place.
    """

    def __init__(
        self,
        nid: str,
        method: str,
        method_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(nid)
        dbg.dassert(method)
        self._method = method
        self._method_kwargs = method_kwargs or {}

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        # Make a copy to protect against a method modifying the df in place.
        df = df.copy()
        func = getattr(df, self._method)
        df = func(**self._method_kwargs)
        # Ensure that the method returns a dataframe.
        dbg.dassert_isinstance(df, pd.DataFrame)
        # Prepare info.
        info = collections.OrderedDict()
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


class Resample(Transformer):
    """
    Node that applies `core.signal_processing.resample()` to a df.
    """

    def __init__(
        self,
        nid: str,
        rule: Union[pd.DateOffset, pd.Timedelta, str],
        agg_func: str,
        resample_kwargs: Optional[Dict[str, Any]] = None,
        agg_func_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        :param rule: resampling frequency
        :param agg_func: a function that is applied to the resampler
        :param resample_kwargs: kwargs for `resample`. Should not include
            `rule` since we handle this separately.
        :param agg_func_kwargs: kwargs for agg_func
        """
        super().__init__(nid)
        self._rule = rule
        self._agg_func = agg_func
        self._resample_kwargs = resample_kwargs or {}
        self._agg_func_kwargs = agg_func_kwargs or {}

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        # Apply resampling function.
        df = df.copy()
        resampler = csigna.resample(df, rule=self._rule, **self._resample_kwargs)
        func = getattr(resampler, self._agg_func)
        df = func(**self._agg_func_kwargs)
        # Package info.
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


class TimeBarResampler(Transformer):
    def __init__(
        self,
        nid: str,
        rule: Union[pd.DateOffset, pd.Timedelta, str],
        return_cols: Optional[list] = None,
        return_agg_func: Optional[str] = None,
        return_agg_func_kwargs: Optional[dict] = None,
        price_cols: Optional[list] = None,
        price_agg_func: Optional[str] = None,
        price_agg_func_kwargs: Optional[list] = None,
        volume_cols: Optional[list] = None,
        volume_agg_func: Optional[str] = None,
        volume_agg_func_kwargs: Optional[list] = None,
    ) -> None:
        """
        Resample time bars with returns, price, volume.

        This function wraps `resample_time_bars()`. Params as in that
        function.
        """
        super().__init__(nid)
        self._rule = rule
        self._return_cols = return_cols
        self._return_agg_func = return_agg_func
        self._return_agg_func_kwargs = return_agg_func_kwargs
        self._price_cols = price_cols
        self._price_agg_func = price_agg_func
        self._price_agg_func_kwargs = price_agg_func_kwargs
        self._volume_cols = volume_cols
        self._volume_agg_func = volume_agg_func
        self._volume_agg_func_kwargs = volume_agg_func_kwargs

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df = df.copy()
        df = cfinan.resample_time_bars(
            df,
            self._rule,
            return_cols=self._return_cols,
            return_agg_func=self._return_agg_func,
            return_agg_func_kwargs=self._return_agg_func_kwargs,
            price_cols=self._price_cols,
            price_agg_func=self._price_agg_func,
            price_agg_func_kwargs=self._price_agg_func_kwargs,
            volume_cols=self._volume_cols,
            volume_agg_func=self._volume_agg_func,
            volume_agg_func_kwargs=self._volume_agg_func_kwargs,
        )
        # Package info.
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


class TwapVwapComputer(Transformer):
    def __init__(
        self,
        nid: str,
        # TODO(gp): -> TIMEDELTA
        rule: Union[pd.DateOffset, pd.Timedelta, str],
        # TODO(gp): -> str
        price_col: Any,
        volume_col: Any,
    ) -> None:
        """
        Calculate TWAP and VWAP prices from price and volume columns.

        This function wraps `compute_twap_vwap()`. Params as in that
        function.
        """
        super().__init__(nid)
        self._rule = rule
        self._price_col = price_col
        self._volume_col = volume_col

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df = df.copy()
        df = cfinan.compute_twap_vwap(
            df,
            self._rule,
            price_col=self._price_col,
            volume_col=self._volume_col,
        )
        # Package info.
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


# #############################################################################
# Results processing
# #############################################################################


class VolatilityNormalizer(FitPredictNode, ColModeMixin):
    def __init__(
        self,
        nid: str,
        col: str,
        target_volatility: float,
        col_mode: Optional[str] = None,
    ) -> None:
        """
        Normalize series to target annual volatility.

        :param col: name of column to rescale
        :param target_volatility: target volatility as a proportion
        :param col_mode: `merge_all` (default) or `replace_all`
            - `replace_all`: return only the rescaled column
            - `merge_all`: append the rescaled column to input dataframe
        """
        super().__init__(nid)
        self._col = col
        self._target_volatility = target_volatility
        dbg.dassert_is_proportion(self._target_volatility)
        self._col_mode = col_mode or "merge_all"
        dbg.dassert_in(self._col_mode, ["merge_all", "replace_all"])
        # TODO(gp): Can it be None? I'd do
        # self._scale_factor: float
        self._scale_factor: Optional[float] = None

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dbg.dassert_in(self._col, df_in.columns)
        self._scale_factor = cfinan.compute_volatility_normalization_factor(
            df_in[self._col], self._target_volatility
        )
        # TODO(gp): Factor out?
        rescaled_y_hat = self._scale_factor * df_in[self._col]
        df_out = self._apply_col_mode(
            df_in,
            rescaled_y_hat.to_frame(),
            cols=[self._col],
            col_rename_func=lambda x: f"rescaled_{x}",
            col_mode=self._col_mode,
        )
        # Store info.
        info = collections.OrderedDict()
        info["scale_factor"] = self._scale_factor
        self._set_info("fit", info)
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dbg.dassert_in(self._col, df_in.columns)
        rescaled_y_hat = self._scale_factor * df_in[self._col]
        df_out = self._apply_col_mode(
            df_in,
            rescaled_y_hat.to_frame(),
            cols=[self._col],
            col_rename_func=lambda x: f"rescaled_{x}",
            col_mode=self._col_mode,
        )
        return {"df_out": df_out}


# #############################################################################
# Utilities
# #############################################################################


# TODO(gp): It is general enough to go to `helpers.printing`.
def get_df_info_as_string(
    df: pd.DataFrame, exclude_memory_usage: bool = True
) -> str:
    """
    Get dataframe info as string.

    :param df: dataframe
    :param exclude_memory_usage: whether to exclude memory usage information
    :return: dataframe info as `str`
    """
    buffer = io.StringIO()
    df.info(buf=buffer)
    info = buffer.getvalue()
    if exclude_memory_usage:
        # Remove memory usage (and a newline).
        info = info.rsplit("\n", maxsplit=2)[0]
    return info
