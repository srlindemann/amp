import logging

import pandas as pd

import core.signal_processing as sigp
import helpers.dbg as dbg
import helpers.printing as prnt
import vendors.kibot.utils as kut

_LOG = logging.getLogger(__name__)


# TODO(GP, Paul): Consider separating higher-level dataflow classes from
# source-specific inherited extensions.
class Node:
    def __init__(self, name, num_inputs=1):
        dbg.dassert_isinstance(name, str)
        self._name = name
        #
        dbg.dassert_lte(0, num_inputs)
        self._num_inputs = num_inputs
        # List of parent nodes.
        self._input_nodes = []
        self._reset()

    def connect(self, *nodes):
        if self._is_connected:
            msg = "Node '%s': already connected to %s" % (
                self._name,
                ", " "".join(self._input_nodes),
            )
            _LOG.error(msg)
            raise ValueError(msg)
        dbg.dassert_eq(
            len(nodes),
            self._num_inputs,
            "Node '%s': invalid number of " "connections",
            self._name,
        )
        for node in nodes:
            dbg.dassert_isinstance(node, Node)
            self._input_nodes.append(node)
        self._is_connected = True

    def fit(self):
        if self._is_fit:
            msg = "Node '%s': already fit" % self._name
            _LOG.error(msg)
        for node in self._input_nodes:
            self._fit_inputs_values.append(node.fit())
        self._is_fit = True

    def predict(self):
        # We can predict multiple times, so every time we need to re-evaluate.
        self._predict_inputs_values = []
        for node in self._input_nodes:
            self._predict_inputs_values.append(node.predict())

    def _reset(self):
        self._is_connected = False
        #
        self._fit_inputs_values = []
        self._is_fit = False
        #
        self._predict_input_values = []
        self._output_values = None

    def __str__(self):
        # TODO(gp): Specify also the format like %s.
        info = [
            ("name", self._name),
            ("num_inputs", self._num_inputs),
            ("is_connected", self._is_connected),
            ("is_fit", self._is_fit),
        ]
        ret = self._to_string(info)
        return ret

    def dag_to_string(self):
        ret = []
        ret.append(str(self))
        for n in self._input_nodes:
            ret.append(prnt.space(n.dag_to_string()))
        ret = "\n".join(ret)
        return ret

    @staticmethod
    def _to_string(info):
        ret = ", ".join(["%s=%s" % (i[0], i[1]) for i in info])
        return ret


# ##############################################################################


class ReadData(Node):
    def __init__(self, name):
        super().__init__(name, num_inputs=0)
        #
        self.df = None

    def fit(self, train_idxs):
        """
        :param train_idxs: indices of the df to use for fitting
        :return: training set as df
        """
        super().fit()
        train_df = self.df.iloc[train_idxs]
        return train_df

    def predict(self, test_idxs):
        """
        :param test_idxs: indices of the df to use for predicting
        :return: test set as df
        """
        super().predict()
        test_df = self.df.iloc[test_idxs]
        return test_df


class ReadDataFromDf(ReadData):
    def __init__(self, name, df):
        super().__init__(name)
        dbg.dassert_isinstance(df, pd.DataFrame)
        self.df = df


class KibotReadData(ReadData):
    def __init__(self, name, file_name, nrows):
        super().__init__(name)
        dbg.dassert_exists(file_name)
        self.file_name = file_name
        self.nrows = nrows
        #
        self.df = None

    def _lazy_load(self):
        if not self.df:
            self.df = kut.read_data_memcached(self.file_name, self.nrows)

    # TODO(gp): Make it streamable so that it reads only the needed data if
    # possible.
    def fit(self, train_idxs):
        """
        :param train_idxs: indices of the df to use for fitting
        :return: training set as df
        """
        self._lazy_load()
        super().fit()


# ##############################################################################


class Zscore(Node):
    def __init__(self, name, tau):
        super().__init__(name, num_inputs=1)
        self.tau = tau

    def _transform(self, df):
        df_out = sigp.rolling_zscore(df, self.tau)
        return df_out

    def fit(self):
        super().fit()
        df_in = self._fit_inputs_values[0]
        df_out = self._transform(df_in)
        return df_out

    def predict(self):
        super().predict()
        df_in = self._predict_inputs_values[0]
        df_out = self._transform(df_in)
        return df_out


# class ComputeFeatures(Node):
#
#     def __init__(self, name, target_y, num_lags):
#         pass
#
#     def connect(self, input1):
#         super().connect(input1)
#
#     def get_x_vars(self):
#         x_vars = ["x0", "x1"]
#         return x_var
#
#     def fit(self, df):
#         df_out = df
#         x_vars = ["x0", "x1"]
#         return df_out
#
#
# class Model(Node):
#
#     def __init__(self, name, y_var, x_vars):
#         self._params = None
#
#     def connect(self, input1):
#         super().connect(input1)
#
#     def fit(self, df):
#         """
#         A model doesn't return anything since it's a sink.
#         """
#         return None
#
#     def predict(self, df):
#         return df + self._params
