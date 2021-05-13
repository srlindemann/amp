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

import pandas as pd

import core.artificial_signal_generators as cartif
import core.finance as cfinan
import core.signal_processing as csigna
import helpers.dbg as dbg
from core.dataflow.core import Node

_LOG = logging.getLogger(__name__)


# TODO(*): Create a dataflow types file.
_COL_TYPE = Union[int, str]
_PANDAS_DATE_TYPE = Union[str, pd.Timestamp, datetime.datetime]


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
        if inputs is None:
            inputs = ["df_in"]
        if outputs is None:
            outputs = ["df_out"]
        super().__init__(nid=nid, inputs=inputs, outputs=outputs)
        self._info = collections.OrderedDict()

    @abc.abstractmethod
    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        pass

    @abc.abstractmethod
    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        pass

    def get_fit_state(self) -> Dict[str, Any]:
        return {}

    def set_fit_state(self, fit_state: Dict[str, Any]) -> None:
        pass

    def get_info(
        self, method: str
    ) -> Optional[Union[str, collections.OrderedDict]]:
        # TODO(Paul): Add a dassert_getattr function to use here and in core.
        dbg.dassert_isinstance(method, str)
        dbg.dassert(getattr(self, method))
        if method in self._info.keys():
            return self._info[method]
        # TODO(Paul): Maybe crash if there is no info.
        _LOG.warning("No info found for nid=%s, method=%s", self.nid, method)
        return None

    def _set_info(self, method: str, values: collections.OrderedDict) -> None:
        dbg.dassert_isinstance(method, str)
        dbg.dassert(getattr(self, method))
        dbg.dassert_isinstance(values, collections.OrderedDict)
        # Save the info in the node: we make a copy just to be safe.
        self._info[method] = copy.copy(values)


class DataSource(FitPredictNode, abc.ABC):
    """
    A source node that can be configured for cross-validation.
    """

    def __init__(self, nid: str, outputs: Optional[List[str]] = None) -> None:
        if outputs is None:
            outputs = ["df_out"]
        # Do not allow any empty list.
        dbg.dassert(outputs)
        super().__init__(nid, inputs=[], outputs=outputs)
        #
        self.df = None
        self._fit_intervals = None
        self._predict_intervals = None
        self._predict_idxs = None

    def set_fit_intervals(self, intervals: List[Tuple[Any, Any]]) -> None:
        """
        :param intervals: closed time intervals like [start1, end1],
            [start2, end2]. `None` boundary is interpreted as data start/end
        """
        self._validate_intervals(intervals)
        self._fit_intervals = intervals

    # DataSource does not have a `df_in` in either `fit` or `predict` as a
    # typical `FitPredictNode` does.
    # pylint: disable=arguments-differ
    def fit(self) -> Dict[str, pd.DataFrame]:
        """
        :return: training set as df
        """
        if self._fit_intervals is not None:
            idx_slices = [
                self.df.loc[interval[0] : interval[1]].index
                for interval in self._fit_intervals
            ]
            idx = functools.reduce(lambda x, y: x.union(y), idx_slices)
            fit_df = self.df.loc[idx].copy()
        else:
            fit_df = self.df.copy()
        info = collections.OrderedDict()
        info["fit_df_info"] = get_df_info_as_string(fit_df)
        self._set_info("fit", info)
        dbg.dassert(not fit_df.empty)
        return {self.output_names[0]: fit_df}

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
        if self._predict_intervals is not None:
            idx_slices = [
                self.df.loc[interval[0] : interval[1]].index
                for interval in self._predict_intervals
            ]
            idx = functools.reduce(lambda x, y: x.union(y), idx_slices)
            predict_df = self.df.loc[idx].copy()
        else:
            predict_df = self.df.copy()
        info = collections.OrderedDict()
        info["predict_df_info"] = get_df_info_as_string(predict_df)
        self._set_info("predict", info)
        dbg.dassert(not predict_df.empty)
        return {self.output_names[0]: predict_df}

    def get_df(self) -> pd.DataFrame:
        dbg.dassert_is_not(self.df, None, "No DataFrame found!")
        return self.df

    @staticmethod
    def _validate_intervals(intervals: List[Tuple[Any, Any]]) -> None:
        dbg.dassert_isinstance(intervals, list)
        for interval in intervals:
            dbg.dassert_eq(len(interval), 2)
            if interval[0] is not None and interval[1] is not None:
                dbg.dassert_lte(interval[0], interval[1])


class Transformer(FitPredictNode, abc.ABC):
    """
    Stateless Single-Input Single-Output node.
    """

    # TODO(Paul): Consider giving users the option of renaming the single
    # input and single output (but verify there is only one of each).
    def __init__(self, nid: str) -> None:
        super().__init__(nid)

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dbg.dassert_no_duplicates(df_in.columns)
        # Transform the input df.
        df_out, info = self._transform(df_in)
        self._set_info("fit", info)
        dbg.dassert_no_duplicates(df_out.columns)
        return {"df_out": df_out}

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dbg.dassert_no_duplicates(df_in.columns)
        # Transform the input df.
        df_out, info = self._transform(df_in)
        self._set_info("predict", info)
        dbg.dassert_no_duplicates(df_out.columns)
        return {"df_out": df_out}

    @abc.abstractmethod
    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        """
        :return: df, info
        """


# #############################################################################
# Data source nodes
# #############################################################################


class ReadDataFromDf(DataSource):
    def __init__(self, nid: str, df: pd.DataFrame) -> None:
        super().__init__(nid)
        dbg.dassert_isinstance(df, pd.DataFrame)
        self.df = df


class DiskDataSource(DataSource):
    def __init__(
        self,
        nid: str,
        file_path: str,
        timestamp_col: Optional[str] = None,
        start_date: Optional[_PANDAS_DATE_TYPE] = None,
        end_date: Optional[_PANDAS_DATE_TYPE] = None,
        reader_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create data source node reading CSV or parquet data from disk.

        :param nid: node identifier
        :param file_path: path to the file
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

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        """
        :return: training set as df
        """
        self._lazy_load()
        return super().fit()

    def _read_data(self) -> None:
        ext = os.path.splitext(self._file_path)[-1]
        if ext == ".csv":
            if "index_col" not in self._reader_kwargs:
                self._reader_kwargs["index_col"] = 0
            read_data = pd.read_csv
        elif ext == ".pq":
            read_data = pd.read_parquet
        else:
            raise ValueError("Invalid file extension='%s'" % ext)
        self.df = read_data(self._file_path, **self._reader_kwargs)

    def _process_data(self) -> None:
        if self._timestamp_col is not None:
            self.df.set_index(self._timestamp_col, inplace=True)
        self.df.index = pd.to_datetime(self.df.index)
        dbg.dassert_strictly_increasing_index(self.df)
        self.df = self.df.loc[self._start_date : self._end_date]
        dbg.dassert(not self.df.empty, "Dataframe is empty")

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
        frequency: str,
        start_date: _PANDAS_DATE_TYPE,
        end_date: _PANDAS_DATE_TYPE,
        ar_coeffs: Optional[List[float]] = None,
        ma_coeffs: Optional[List[float]] = None,
        scale: Optional[float] = None,
        burnin: Optional[float] = None,
        seed: Optional[float] = None,
    ) -> None:
        super().__init__(nid)
        self._frequency = frequency
        self._start_date = start_date
        self._end_date = end_date
        self._ar_coeffs = ar_coeffs or [0]
        self._ma_coeffs = ma_coeffs or [0]
        self._scale = scale or 1
        self._burnin = burnin or 0
        self._seed = seed
        self._arma_process = cartif.ArmaProcess(
            ar_coeffs=self._ar_coeffs, ma_coeffs=self._ma_coeffs
        )

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        """
        :return: training set as df
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
        prices = rets.cumsum()
        prices.name = "close"
        self.df = prices.to_frame()
        self.df = self.df.loc[self._start_date : self._end_date]
        # Use constant volume (for now).
        self.df["vol"] = 100


class MultivariateNormalGenerator(DataSource):
    """
    A node for generating price data from multivariate normal returns.
    """

    def __init__(
        self,
        nid: str,
        frequency: str,
        start_date: _PANDAS_DATE_TYPE,
        end_date: _PANDAS_DATE_TYPE,
        dim: int,
        seed: Optional[float] = None,
    ) -> None:
        super().__init__(nid)
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

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        """
        :return: training set as df
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
        prices = rets.cumsum()
        prices = prices.rename(columns=lambda x: "MN" + str(x))
        # Use constant volume (for now).
        volume = pd.DataFrame(index=prices.index, columns=prices.columns,
                              data=100)
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
        :param connector_func:
            * Merge
            ```
            connector_func = lambda df_in1, df_in2, **connector_kwargs:
                df_in1.merge(df_in2, **connector_kwargs)
            ```
            * Reindexing
            ```
            connector_func = lambda df_in1, df_in2, connector_kwargs:
                df_in1.reindex(index=df_in2.index, **connector_kwargs)
            ```
            * User-defined functions
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
        return self._get_col_names(self._df_in1_col_names)

    def get_df_in2_col_names(self) -> List[str]:
        """
        Allow introspection on column names of input dataframe #2.
        """
        return self._get_col_names(self._df_in2_col_names)

    # pylint: disable=arguments-differ
    def fit(
        self, df_in1: pd.DataFrame, df_in2: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        df_out, info = self._apply_connector_func(df_in1, df_in2)
        self._set_info("fit", info)
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
        self._df_in1_col_names = df_in1.columns.tolist()
        self._df_in2_col_names = df_in2.columns.tolist()
        # TODO(Paul): Add meaningful info.
        df_out = self._connector_func(df_in1, df_in2, **self._connector_kwargs)
        info = collections.OrderedDict()
        info["df_merged_info"] = get_df_info_as_string(df_out)
        return df_out, info

    @staticmethod
    def _get_col_names(col_names: List[str]) -> List[str]:
        dbg.dassert_is_not(
            col_names,
            None,
            "No column names. This may indicate "
            "an invocation prior to graph execution.",
        )
        return col_names


# #############################################################################
# Transformer nodes
# #############################################################################


class ColModeMixin:
    """
    Selects columns to propagate in output dataframe.
    """

    def _apply_col_mode(
        self,
        df_in: pd.DataFrame,
        df_out: pd.DataFrame,
        cols: Optional[List[Any]] = None,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Merge transformed dataframe with original dataframe.

        :param df_in: original dataframe
        :param df_out: transformed dataframe
        :param cols: columns in `df_in` that were transformed to obtain
            `df_out`. `None` defaults to all columns in `df_out`
        :param col_mode: `None`, "merge_all", "replace_selected", or
            "replace_all". Determines what columns are propagated. `None`
            defaults to "merge all". If "merge_all", perform an outer merge
        :param col_rename_func: function for naming transformed columns, e.g.,
            lambda x: "zscore_" + x. `None` defaults to identity transform
        :return: dataframe with columns selected by `col_mode`
        """
        dbg.dassert_isinstance(df_in, pd.DataFrame)
        dbg.dassert_isinstance(df_out, pd.DataFrame)
        dbg.dassert(cols is None or isinstance(cols, list))
        cols = cols or df_out.columns.tolist()
        col_rename_func = col_rename_func or (lambda x: x)
        dbg.dassert_isinstance(col_rename_func, collections.Callable)
        col_mode = col_mode or "merge_all"
        # Rename transformed columns.
        df_out = df_out.rename(columns=col_rename_func)
        self._transformed_col_names = df_out.columns.tolist()
        # Select columns to return.
        if col_mode == "merge_all":
            shared_columns = df_out.columns.intersection(df_in.columns)
            dbg.dassert(
                shared_columns.empty,
                "Transformed column names `%s` conflict with existing column "
                "names `%s`.",
                df_out.columns,
                df_in.columns,
            )
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
        :param cols: columns to transform; `None` defaults to all available.
        :param col_rename_func: function for naming transformed columns, e.g.,
            lambda x: "zscore_" + x
        :param col_mode: `merge_all`, `replace_selected`, or `replace_all`.
            Determines what columns are propagated by the node.
        :param nan_mode: `leave_unchanged` or `drop`. If `drop`, applies to all
            columns simultaneously.
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
            col_rename_func=self._col_rename_func,
            col_mode=self._col_mode,
        )
        #
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


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
        :param nid: unique node id
        :param transformer_func: srs -> df. The keyword `info` (if present) is
            assumed to have a specific semantic meaning. If present,
                - An empty dict is passed in to this `info`
                - The resulting (populated) dict is included in the node's
                  `_info`
        :param transformer_kwargs: transformer_func kwargs
        :param cols: columns to transform; `None` defaults to all available.
        :param col_rename_func: function for naming transformed columns, e.g.,
            lambda x: "zscore_" + x
        :param col_mode: `merge_all`, `replace_selected`, or `replace_all`.
            Determines what columns are propagated by the node.
        :param nan_mode: `leave_unchanged` or `drop`. If `drop`, applies to
            columns individually.
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


class MultiindexSeriesTransformer(Transformer, ColModeMixin):
    """
    Perform non-index modifying changes of columns.

    When operating on multiple columns, this applies the transformer function
    one series at a time. Additionally, NaN-handling is performed "locally"
    (one series at a time, without regard to NaNs in other columns).
    """

    def __init__(
        self,
        nid: str,
        in_col_group: Tuple[_COL_TYPE],
        out_col_group: Tuple[_COL_TYPE],
        transformer_func: Callable[..., pd.DataFrame],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        nan_mode: Optional[str] = None,
    ) -> None:
        """
        For reference, let
          - N = df.columns.nlevels
          - leaf_cols = df[in_col_group].columns

        :param nid: unique node id
        :param in_col_group: a group of cols specified by the first N - 1
            levels
        :param out_col_group: new output col group names
        :param transformer_func: srs -> df
        :param transformer_kwargs: transformer_func kwargs
        :param nan_mode: `leave_unchanged` or `drop`. If `drop`, applies to
            columns individually.
        """
        super().__init__(nid)
        dbg.dassert_isinstance(in_col_group, tuple)
        dbg.dassert_isinstance(out_col_group, tuple)
        dbg.dassert_eq(len(in_col_group), len(out_col_group),
                       msg="Column hierarchy depth must be preserved.")
        self._in_col_group = in_col_group
        self._out_col_group = out_col_group
        self._transformer_func = transformer_func
        self._transformer_kwargs = transformer_kwargs or {}
        # Store the list of columns after the transformation.
        self._nan_mode = nan_mode or "leave_unchanged"
        self._leaf_cols = None

    def _transform(
            self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        # After indexing by `self._in_col_group`, we should have a flat column
        # index.
        dbg.dassert_eq(len(self._in_col_group), df.columns.nlevels - 1,
                       "Dataframe multiindex column depth incompatible with config.")
        dbg.dassert_not_in(self._out_col_group, df.columns,
                           "Desired column names already present in dataframe.")
        df_in = df
        df = df[self._in_col_group].copy()
        self._leaf_cols = df.columns.tolist()
        idx = df.index
        if self._nan_mode == "leave_unchanged":
            pass
        elif self._nan_mode == "drop":
            df = df.dropna()
        else:
            raise ValueError(f"Unrecognized `nan_mode` {self._nan_mode}")
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
            srs.name = col
            srs_list.append(srs)
        info["func_info"] = func_info
        df = pd.concat(srs_list, axis=1)
        df = pd.concat([df], axis=1, keys=self._out_col_group)
        df = df.reindex(index=idx)
        # TODO(Paul): Consider supporting the option of relaxing or
        # foregoing this check.
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
    def __init__(
        self,
        nid: str,
        method: str,
        method_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(nid)
        dbg.dassert(method)
        # TODO(Paul): Ensure that this is a valid method.
        self._method = method
        self._method_kwargs = method_kwargs or {}

    def _transform(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, collections.OrderedDict]:
        df = df.copy()
        df = getattr(df, self._method)(**self._method_kwargs)
        # Not all methods return DataFrames. We want to restrict to those that
        # do.
        dbg.dassert_isinstance(df, pd.DataFrame)
        #
        info = collections.OrderedDict()
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


class Resample(Transformer):
    def __init__(
        self,
        nid: str,
        rule: Union[pd.DateOffset, pd.Timedelta, str],
        agg_func: str,
        resample_kwargs: Optional[Dict[str, Any]] = None,
        agg_func_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        :param nid: node identifier
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
        df = df.copy()
        resampler = csigna.resample(df, rule=self._rule, **self._resample_kwargs)
        df = getattr(resampler, self._agg_func)(**self._agg_func_kwargs)
        #
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

        This function wraps `resample_time_bars()`. Params as in that function.

        :param nid: node identifier
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
        #
        info: collections.OrderedDict[str, Any] = collections.OrderedDict()
        info["df_transformed_info"] = get_df_info_as_string(df)
        return df, info


class TwapVwapComputer(Transformer):
    def __init__(
        self,
        nid: str,
        rule: Union[pd.DateOffset, pd.Timedelta, str],
        price_col: Any,
        volume_col: Any,
    ) -> None:
        """
        Calculate TWAP and VWAP prices from price and volume columns.

        This function wraps `compute_twap_vwap()`. Params as in that function.

        :param nid: node identifier
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
        #
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

        :param nid: node identifier
        :param col: name of column to rescale
        :param target_volatility: target volatility as a proportion
        :param col_mode: `merge_all` or `replace_all`. If `replace_all`, return
            only the rescaled column, if `merge_all`, append the rescaled
            column to input dataframe
        """
        super().__init__(nid)
        self._col = col
        self._target_volatility = target_volatility
        self._col_mode = col_mode or "merge_all"
        dbg.dassert_in(
            self._col_mode,
            ["merge_all", "replace_all"],
            "Invalid `col_mode`='%s'",
            self._col_mode,
        )
        self._scale_factor: Optional[float] = None

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        dbg.dassert_in(self._col, df_in.columns)
        self._scale_factor = cfinan.compute_volatility_normalization_factor(
            df_in[self._col], self._target_volatility
        )
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
