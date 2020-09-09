import logging
import os
import pprint

import core.artificial_signal_generators as sig_gen
import core.config as cfg
import core.config_builders as cfgb
import core.dataflow as dtf
import core.finance as fin
import core.signal_processing as sigp
import helpers.printing as prnt
import helpers.unit_test as hut
import mxnet
import numpy as np
import pandas as pd
import pytest
import sklearn.decomposition as sld
import sklearn.linear_model as slm

_LOG = logging.getLogger(__name__)


# #############################################################################
# Abstract Node classes with sklearn-style interfaces
# #############################################################################


class TestDiskDataSource(hut.TestCase):
    def test_datetime_index_csv1(self) -> None:
        """
        Test CSV file using timestamps in the index.
        """
        df = TestDiskDataSource._generate_df()
        file_path = self._save_df(df, ".csv")
        timestamp_col = None
        rdfd = dtf.DiskDataSource("read_data", file_path, timestamp_col)
        loaded_df = rdfd.fit()["df_out"]
        self.check_string(loaded_df.to_string())

    def test_datetime_col_csv1(self) -> None:
        """
        Test CSV file using timestamps in a column.
        """
        df = TestDiskDataSource._generate_df()
        df = df.reset_index()
        file_path = self._save_df(df, ".csv")
        timestamp_col = "timestamp"
        rdfd = dtf.DiskDataSource("read_data", file_path, timestamp_col)
        loaded_df = rdfd.fit()["df_out"]
        self.check_string(loaded_df.to_string())

    def test_datetime_index_parquet1(self) -> None:
        """
        Test Parquet file using timestamps in the index.
        """
        df = TestDiskDataSource._generate_df()
        file_path = self._save_df(df, ".pq")
        timestamp_col = None
        rdfd = dtf.DiskDataSource("read_data", file_path, timestamp_col)
        loaded_df = rdfd.fit()["df_out"]
        self.check_string(loaded_df.to_string())

    def test_datetime_col_parquet1(self) -> None:
        """
        Test Parquet file using timestamps in a column.
        """
        df = TestDiskDataSource._generate_df()
        df = df.reset_index()
        file_path = self._save_df(df, ".pq")
        timestamp_col = "timestamp"
        rdfd = dtf.DiskDataSource("read_data", file_path, timestamp_col)
        loaded_df = rdfd.fit()["df_out"]
        self.check_string(loaded_df.to_string())

    def test_filter_dates1(self) -> None:
        """
        Test date filtering with both boundaries specified for CSV file using
        timestamps in the index.
        """
        df = TestDiskDataSource._generate_df()
        file_path = self._save_df(df, ".csv")
        timestamp_col = None
        rdfd = dtf.DiskDataSource(
            "read_data",
            file_path,
            timestamp_col,
            start_date="2010-01-02",
            end_date="2010-01-05",
        )
        loaded_df = rdfd.fit()["df_out"]
        self.check_string(loaded_df.to_string())

    def test_filter_dates_open_boundary1(self) -> None:
        """
        Test date filtering with one boundary specified for CSV file using
        timestamps in the index.
        """
        df = TestDiskDataSource._generate_df()
        file_path = self._save_df(df, ".csv")
        timestamp_col = None
        rdfd = dtf.DiskDataSource(
            "read_data", file_path, timestamp_col, start_date="2010-01-02",
        )
        loaded_df = rdfd.fit()["df_out"]
        self.check_string(loaded_df.to_string())

    @staticmethod
    def _generate_df(num_periods: int = 10) -> pd.DataFrame:
        idx = pd.date_range("2010-01-01", periods=num_periods, name="timestamp")
        df = pd.DataFrame(range(num_periods), index=idx, columns=["0"])
        return df

    def _save_df(self, df: pd.DataFrame, ext: str) -> str:
        scratch_space = self.get_scratch_space()
        file_path = os.path.join(scratch_space, f"df{ext}")
        if ext == ".csv":
            df.to_csv(file_path)
        elif ext == ".pq":
            df.to_parquet(file_path)
        else:
            raise ValueError("Invalid extension='%s'" % ext)
        return file_path


# #############################################################################
# Models
# #############################################################################


class TestContinuousSkLearnModel(hut.TestCase):
    def test_fit_dag1(self) -> None:
        pred_lag = 1
        # Load test data.
        data = self._get_data(pred_lag)
        data_source_node = dtf.ReadDataFromDf("data", data)
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Load sklearn config and create modeling node.
        config = self._get_config(pred_lag)
        node = dtf.ContinuousSkLearnModel(
            "sklearn", model_func=slm.Ridge, **config.to_dict(),
        )
        dag.add_node(node)
        dag.connect("data", "sklearn")
        #
        output_df = dag.run_leq_node("sklearn", "fit")["df_out"]
        self.check_string(output_df.to_string())

    def test_fit_dag2(self) -> None:
        pred_lag = 2
        # Load test data.
        data = self._get_data(pred_lag)
        data_source_node = dtf.ReadDataFromDf("data", data)
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Load sklearn config and create modeling node.
        config = self._get_config(pred_lag)
        node = dtf.ContinuousSkLearnModel(
            "sklearn", model_func=slm.Ridge, **config.to_dict(),
        )
        dag.add_node(node)
        dag.connect("data", "sklearn")
        #
        output_df = dag.run_leq_node("sklearn", "fit")["df_out"]
        self.check_string(output_df.to_string())

    def test_predict_dag1(self) -> None:
        pred_lag = 1
        # Load test data.
        data = self._get_data(pred_lag)
        fit_interval = ("1776-07-04 12:00:00", "2010-01-01 00:29:00")
        predict_interval = ("2010-01-01 00:30:00", "2100")
        data_source_node = dtf.ReadDataFromDf("data", data)
        data_source_node.set_fit_intervals([fit_interval])
        data_source_node.set_predict_intervals([predict_interval])
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Load sklearn config and create modeling node.
        config = self._get_config(pred_lag)
        node = dtf.ContinuousSkLearnModel(
            "sklearn", model_func=slm.Ridge, **config.to_dict(),
        )
        dag.add_node(node)
        dag.connect("data", "sklearn")
        #
        dag.run_leq_node("sklearn", "fit")
        output_df = dag.run_leq_node("sklearn", "predict")["df_out"]
        self.check_string(output_df.to_string())

    def test_predict_dag2(self) -> None:
        pred_lag = 2
        # Load test data.
        data = self._get_data(pred_lag)
        fit_interval = ("1776-07-04 12:00:00", "2010-01-01 00:29:00")
        predict_interval = ("2010-01-01 00:30:00", "2100")
        data_source_node = dtf.ReadDataFromDf("data", data)
        data_source_node.set_fit_intervals([fit_interval])
        data_source_node.set_predict_intervals([predict_interval])
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Load sklearn config and create modeling node.
        config = self._get_config(pred_lag)
        node = dtf.ContinuousSkLearnModel(
            "sklearn", model_func=slm.Ridge, **config.to_dict(),
        )
        dag.add_node(node)
        dag.connect("data", "sklearn")
        #
        dag.run_leq_node("sklearn", "fit")
        output_df = dag.run_leq_node("sklearn", "predict")["df_out"]
        self.check_string(output_df.to_string())

    def _get_config(self, steps_ahead: int) -> cfg.Config:
        config = cfg.Config()
        config["x_vars"] = ["x"]
        config["y_vars"] = ["y"]
        config["steps_ahead"] = steps_ahead
        config_kwargs = config.add_subconfig("model_kwargs")
        config_kwargs["alpha"] = 0.5
        return config

    def _get_data(self, lag: int) -> pd.DataFrame:
        """
        Generate "random returns". Use lag + noise as predictor.
        """
        num_periods = 50
        total_steps = num_periods + lag + 1
        rets = sig_gen.get_gaussian_walk(0, 0.2, total_steps, seed=10).diff()
        noise = sig_gen.get_gaussian_walk(0, 0.02, total_steps, seed=1).diff()
        pred = rets.shift(-lag).loc[1:num_periods] + noise.loc[1:num_periods]
        resp = rets.loc[1:num_periods]
        idx = pd.date_range("2010-01-01", periods=num_periods, freq="T")
        df = pd.DataFrame.from_dict({"x": pred, "y": resp}).set_index(idx)
        return df


class TestUnsupervisedSkLearnModel(hut.TestCase):
    def test_fit_dag1(self) -> None:
        # Load test data.
        data = self._get_data()
        data_source_node = dtf.ReadDataFromDf("data", data)
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Load sklearn config and create modeling node.
        config = cfgb.get_config_from_nested_dict(
            {
                "x_vars": [0, 1, 2, 3],
                "model_func": sld.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtf.UnsupervisedSkLearnModel("sklearn", **config.to_dict())
        dag.add_node(node)
        dag.connect("data", "sklearn")
        #
        output_df = dag.run_leq_node("sklearn", "fit")["df_out"]
        self.check_string(output_df.to_string())

    def test_predict_dag1(self) -> None:
        # Load test data.
        data = self._get_data()
        data_source_node = dtf.ReadDataFromDf("data", data)
        fit_interval = ("2000-01-03", "2000-01-31")
        predict_interval = ("2000-02-01", "2000-02-25")
        data_source_node.set_fit_intervals([fit_interval])
        data_source_node.set_predict_intervals([predict_interval])
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Load sklearn config and create modeling node.
        config = cfgb.get_config_from_nested_dict(
            {
                "x_vars": [0, 1, 2, 3],
                "model_func": sld.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtf.UnsupervisedSkLearnModel("sklearn", **config.to_dict())
        dag.add_node(node)
        dag.connect("data", "sklearn")
        #
        dag.run_leq_node("sklearn", "fit")
        output_df = dag.run_leq_node("sklearn", "predict")["df_out"]
        self.check_string(output_df.to_string())

    def _get_data(self) -> pd.DataFrame:
        """
        Generate multivariate normal returns.
        """
        mn_process = sig_gen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=4, seed=0)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=0
        )
        return realization


class TestResidualizer(hut.TestCase):
    def test_fit_dag1(self) -> None:
        # Load test data.
        data = self._get_data()
        data_source_node = dtf.ReadDataFromDf("data", data)
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Load sklearn config and create modeling node.
        config = cfgb.get_config_from_nested_dict(
            {
                "x_vars": [0, 1, 2, 3],
                "model_func": sld.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtf.Residualizer("sklearn", **config.to_dict())
        dag.add_node(node)
        dag.connect("data", "sklearn")
        #
        output_df = dag.run_leq_node("sklearn", "fit")["df_out"]
        self.check_string(output_df.to_string())

    def test_predict_dag1(self) -> None:
        # Load test data.
        data = self._get_data()
        data_source_node = dtf.ReadDataFromDf("data", data)
        fit_interval = ("2000-01-03", "2000-01-31")
        predict_interval = ("2000-02-01", "2000-02-25")
        data_source_node.set_fit_intervals([fit_interval])
        data_source_node.set_predict_intervals([predict_interval])
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Load sklearn config and create modeling node.
        config = cfgb.get_config_from_nested_dict(
            {
                "x_vars": [0, 1, 2, 3],
                "model_func": sld.PCA,
                "model_kwargs": {"n_components": 2},
            }
        )
        node = dtf.Residualizer("sklearn", **config.to_dict())
        dag.add_node(node)
        dag.connect("data", "sklearn")
        #
        dag.run_leq_node("sklearn", "fit")
        output_df = dag.run_leq_node("sklearn", "predict")["df_out"]
        self.check_string(output_df.to_string())

    def _get_data(self) -> pd.DataFrame:
        """
        Generate multivariate normal returns.
        """
        mn_process = sig_gen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=4, seed=0)
        realization = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=0
        )
        return realization


class TestSmaModel(hut.TestCase):
    def test_fit_dag1(self) -> None:
        # Load test data.
        data = self._get_data()
        data_source_node = dtf.ReadDataFromDf("data", data)
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Specify config and create modeling node.
        config = cfg.Config()
        config["col"] = ["vol"]
        config["steps_ahead"] = 2
        config["nan_mode"] = "drop"
        node = dtf.SmaModel("sma", **config.to_dict())
        dag.add_node(node)
        dag.connect("data", "sma")
        #
        output_df = dag.run_leq_node("sma", "fit")["df_out"]
        self.check_string(output_df.to_string())

    def test_fit_dag2(self) -> None:
        """
        Specify `tau` parameter.
        """
        # Load test data.
        data = self._get_data()
        data_source_node = dtf.ReadDataFromDf("data", data)
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Specify config and create modeling node.
        config = cfg.Config()
        config["col"] = ["vol"]
        config["steps_ahead"] = 2
        config["tau"] = 8
        config["nan_mode"] = "drop"
        node = dtf.SmaModel("sma", **config.to_dict())
        dag.add_node(node)
        dag.connect("data", "sma")
        #
        output_df = dag.run_leq_node("sma", "fit")["df_out"]
        self.check_string(output_df.to_string())

    def test_predict_dag1(self) -> None:
        # Load test data.
        data = self._get_data()
        fit_interval = ("2000-01-01", "2000-02-10")
        predict_interval = ("2000-01-20", "2000-02-23")
        data_source_node = dtf.ReadDataFromDf("data", data)
        data_source_node.set_fit_intervals([fit_interval])
        data_source_node.set_predict_intervals([predict_interval])
        # Create DAG and test data node.
        dag = dtf.DAG(mode="strict")
        dag.add_node(data_source_node)
        # Specify config and create modeling node.
        config = cfg.Config()
        config["col"] = ["vol"]
        config["steps_ahead"] = 2
        config["nan_mode"] = "drop"
        node = dtf.SmaModel("sma", **config.to_dict())
        dag.add_node(node)
        dag.connect("data", "sma")
        #
        dag.run_leq_node("sma", "fit")
        output_df = dag.run_leq_node("sma", "predict")["df_out"]
        self.check_string(output_df.to_string())

    @staticmethod
    def _get_data() -> pd.DataFrame:
        """
        Generate "random returns". Use lag + noise as predictor.
        """
        arma_process = sig_gen.ArmaProcess([0.45], [0])
        date_range_kwargs = {"start": "2000-01-01", "periods": 40, "freq": "B"}
        date_range = pd.date_range(**date_range_kwargs)
        realization = arma_process.generate_sample(
            date_range_kwargs=date_range_kwargs, seed=0
        )
        vol = np.abs(realization) ** 2
        vol.name = "vol"
        df = pd.DataFrame(index=date_range, data=vol)
        return df


if True:

    class TestContinuousDeepArModel(hut.TestCase):
        @pytest.mark.skip("Disabled because of PartTask2440")
        def test_fit_dag1(self) -> None:
            dag = self._get_dag()
            #
            output_df = dag.run_leq_node("deepar", "fit")["df_out"]
            self.check_string(output_df.to_string())

        @pytest.mark.skip("Disabled because of PartTask2440")
        def test_predict_dag1(self) -> None:
            dag = self._get_dag()
            #
            dag.run_leq_node("deepar", "fit")
            output_df = dag.run_leq_node("deepar", "predict")["df_out"]
            self.check_string(output_df.to_string())

        def _get_dag(self) -> dtf.DAG:
            mxnet.random.seed(0)
            data, _ = sig_gen.get_gluon_dataset(
                dataset_name="m4_hourly", train_length=100, test_length=1,
            )
            fit_idxs = data.iloc[:70].index
            predict_idxs = data.iloc[70:].index
            data_source_node = dtf.ReadDataFromDf("data", data)
            data_source_node.set_fit_idxs(fit_idxs)
            data_source_node.set_predict_idxs(predict_idxs)
            # Create DAG and test data node.
            dag = dtf.DAG(mode="strict")
            dag.add_node(data_source_node)
            # Load deepar config and create modeling node.
            config = cfg.Config()
            config["x_vars"] = None
            config["y_vars"] = ["y"]
            config["trainer_kwargs"] = {"epochs": 1}
            config["estimator_kwargs"] = {"prediction_length": 2}
            node = dtf.ContinuousDeepArModel("deepar", **config.to_dict(),)
            dag.add_node(node)
            dag.connect("data", "deepar")
            return dag

    class TestDeepARGlobalModel(hut.TestCase):
        @pytest.mark.skip("Disabled because of PartTask2440")
        def test_fit1(self) -> None:
            mxnet.random.seed(0)
            local_ts = self._get_local_ts()
            num_entries = 100
            config = self._get_config()
            deepar = dtf.DeepARGlobalModel(**config.to_dict())
            output = deepar.fit(local_ts)
            info = deepar.get_info("fit")
            str_output = "\n".join(
                [
                    f"{key}:\n{val.head(num_entries).to_string()}"
                    for key, val in output.items()
                ]
            )
            output_shape = {
                str(key): str(val.shape) for key, val in output.items()
            }
            config_info_output = (
                f"{prnt.frame('config')}\n{config}\n"
                f"{prnt.frame('info')}\n{pprint.pformat(info)}\n"
                f"{prnt.frame('output')}\n{str_output}\n"
                f"{prnt.frame('output_shape')}\n{output_shape}\n"
            )
            self.check_string(config_info_output)

        @pytest.mark.skip("Disabled because of PartTask2440")
        def test_fit_dag1(self) -> None:
            mxnet.random.seed(0)
            dag = dtf.DAG(mode="strict")
            local_ts = self._get_local_ts()
            data_source_node = dtf.ReadDataFromDf("local_ts", local_ts)
            dag.add_node(data_source_node)
            config = self._get_config()
            deepar = dtf.DeepARGlobalModel(**config.to_dict())
            dag.add_node(deepar)
            dag.connect("local_ts", "deepar")
            output_df = dag.run_leq_node("deepar", "fit")["df_out"]
            expected_shape = (self._n_periods * (self._grid_len - 1), 1)
            self.assertEqual(output_df.shape, expected_shape)
            self.check_string(output_df.to_string())

        def _get_local_ts(self) -> pd.DataFrame:
            """
            Generate a dataframe of the following format:

                                  EVENT_SENTIMENT_SCORE    zret_0
            0 2010-01-01 00:00:00               0.496714 -0.138264
              2010-01-01 00:01:00               0.647689  1.523030
              2010-01-01 00:02:00              -0.234153 -0.234137
              2010-01-01 00:03:00               1.579213  0.767435
              2010-01-01 00:04:00              -0.469474  0.542560
            """
            np.random.seed(42)
            self._n_periods = 10
            self._grid_len = 3
            grid_idx = range(self._grid_len)
            idx = pd.date_range("2010-01-01", periods=self._n_periods, freq="T")
            idx = pd.MultiIndex.from_product([grid_idx, idx])
            local_ts = pd.DataFrame(
                np.random.randn(self._n_periods * self._grid_len, 2), index=idx
            )
            self._x_vars = ["EVENT_SENTIMENT_SCORE"]
            self._y_vars = ["zret_0"]
            local_ts.columns = self._x_vars + self._y_vars
            return local_ts

        def _get_config(self) -> cfg.Config:
            config = cfg.Config()
            config["nid"] = "deepar"
            config["trainer_kwargs"] = {"epochs": 1}
            config["estimator_kwargs"] = {
                "freq": "T",
                "use_feat_dynamic_real": False,
            }
            config["x_vars"] = self._x_vars
            config["y_vars"] = self._y_vars
            return config


# #############################################################################
# Results processing
# #############################################################################


class TestVolatilityNormalizer(hut.TestCase):
    @staticmethod
    def _get_series(seed: int, periods: int = 44) -> pd.Series:
        arma_process = sig_gen.ArmaProcess([0], [0])
        date_range = {"start": "2010-01-01", "periods": periods, "freq": "B"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        )
        return series

    def test_fit1(self) -> None:
        y = TestVolatilityNormalizer._get_series(42).rename("ret_0")
        y_hat = sigp.compute_smooth_moving_average(y, 28).rename("ret_0_hat")
        df_in = pd.concat([y, y_hat], axis=1)
        #
        vn = dtf.VolatilityNormalizer("normalize_volatility", "ret_0_hat", 0.1)
        df_out = vn.fit(df_in)["df_out"]
        #
        volatility = 100 * df_out.apply(fin.compute_annualized_volatility)
        output_str = (
            f"{prnt.frame('df_out')}\n"
            f"{hut.convert_df_to_string(df_out, index=True)}\n"
            f"{prnt.frame('df_out annualized volatility')}\n"
            f"{volatility}"
        )
        self.check_string(output_str)

    def test_fit2(self) -> None:
        """
        Test with `col_mode`="replace_all".
        """
        y = TestVolatilityNormalizer._get_series(42).rename("ret_0")
        y_hat = sigp.compute_smooth_moving_average(y, 28).rename("ret_0_hat")
        df_in = pd.concat([y, y_hat], axis=1)
        #
        vn = dtf.VolatilityNormalizer(
            "normalize_volatility", "ret_0_hat", 0.1, col_mode="replace_all",
        )
        df_out = vn.fit(df_in)["df_out"]
        #
        volatility = 100 * df_out.apply(fin.compute_annualized_volatility)
        output_str = (
            f"{prnt.frame('df_in')}\n"
            f"{hut.convert_df_to_string(df_in, index=True)}\n"
            f"{prnt.frame('df_out')}\n"
            f"{hut.convert_df_to_string(df_out, index=True)}\n"
            f"{prnt.frame('df_out annualized volatility')}\n"
            f"{volatility}"
        )
        self.check_string(output_str)

    def test_predict1(self) -> None:
        y = TestVolatilityNormalizer._get_series(42).rename("ret_0")
        y_hat = sigp.compute_smooth_moving_average(y, 28).rename("ret_0_hat")
        fit_df_in = pd.concat([y, y_hat], axis=1)
        predict_df_in = (
            TestVolatilityNormalizer._get_series(0).rename("ret_0_hat").to_frame()
        )
        predict_df_in = sigp.compute_smooth_moving_average(predict_df_in, 18)
        # Fit normalizer.
        vn = dtf.VolatilityNormalizer("normalize_volatility", "ret_0_hat", 0.1)
        fit_df_out = vn.fit(fit_df_in)["df_out"]
        # Predict.
        predict_df_out = vn.predict(predict_df_in)["df_out"]
        #
        fit_df_out_volatility = 100 * fit_df_out.apply(
            fin.compute_annualized_volatility
        )
        predict_df_out_volatility = 100 * predict_df_out.apply(
            fin.compute_annualized_volatility
        )
        output_str = (
            # Fit outputs.
            f"{prnt.frame('fit_df_out')}\n"
            f"{hut.convert_df_to_string(fit_df_out, index=True)}\n"
            f"{prnt.frame('fit_df_out annualized volatility')}\n"
            f"{fit_df_out_volatility}"
            # Predict outputs.
            f"{prnt.frame('predict_df_out')}\n"
            f"{hut.convert_df_to_string(predict_df_out, index=True)}\n"
            f"{prnt.frame('predict_df_out annualized volatility')}\n"
            f"{predict_df_out_volatility}"
        )
        self.check_string(output_str)
