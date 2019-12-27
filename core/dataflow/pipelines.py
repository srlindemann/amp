import logging
from typing import Optional

import sklearn

import core.config as cfg
import core.event_study as esf
import core.signal_processing as sigp
from core.dataflow.builder import DagBuilder
from core.dataflow.core import DAG
from core.dataflow.nodes import (
    ColumnTransformer,
    DataframeMethodRunner,
    Resample,
    SkLearnModel,
    YConnector,
)

_LOG = logging.getLogger(__name__)


class EventStudyBuilder(DagBuilder):
    """
    Configurable pipeline for running event studies.
    """

    def get_config_template(self) -> cfg.Config:
        """
        Return a reference configuration for the event study pipeline.
        """
        config = cfg.Config()
        #
        stage = "resample_events"
        config_tmp = config.add_subconfig(self._get_nid(stage))
        config_tmp["rule"] = "T"
        config_tmp["agg_func"] = "mean"
        #
        stage = "generate_event_signal"
        config_tmp = config.add_subconfig(self._get_nid(stage))
        config_kwargs = config_tmp.add_subconfig("transformer_kwargs")
        config_kwargs["tau"] = 8
        config_kwargs["max_depth"] = 3
        #
        stage = "shift"
        config_tmp = config.add_subconfig(self._get_nid(stage))
        config_kwargs = config_tmp.add_subconfig("method_kwargs")
        config_kwargs["periods"] = 1
        #
        stage = "build_local_ts"
        config_tmp = config.add_subconfig(self._get_nid(stage))
        config_kwargs = config_tmp.add_subconfig("connector_kwargs")
        config_kwargs["relative_grid_indices"] = range(-10, 50)
        #
        stage = "model"
        config_tmp = config.add_subconfig(self._get_nid(stage))
        config_tmp["x_vars"] = ["_DUMMY_"]
        config_tmp["y_vars"] = ["_DUMMY_"]
        config_kwargs = config_tmp.add_subconfig("model_kwargs")
        config_kwargs["alpha"] = 0.5
        return config

    def get_dag(self, config: cfg.Config, dag: Optional[DAG] = None) -> DAG:
        """
        Implement a pipeline for running event studies.

        WARNING: Modifies `dag` in-place.

        :param config: Must be compatible with pipeline construction
            implemented by this function.
        :param dag: May or may not already contain nodes. If `None`, then
            returns a new DAG.
        """
        dag = dag or DAG()
        _LOG.debug("%s", config)
        # Dummy node for grid data input.
        # - The dataframe with timestamps along a frequency should connect to
        #   this node
        # - It is a no-op node but added so that the grid data connectivity can
        #   be encapsulated
        stage = "grid_data_input_socket"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=lambda x: x,
            col_mode="replace_all",
        )
        dag.add_node(node)
        # Dummy node for events data.
        # - The dataframe containing timestamp-indexed events and any feature
        #   columns should connect to this node
        # - It is a no-op node but added so that the event study connectivity
        #   can be encapsulated
        stage = "events_input_socket"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=lambda x: x,
            col_mode="replace_all",
        )
        dag.add_node(node)
        # Resample events data to uniform grid specified by config.
        # TODO(Paul): Add a check to ensure alignment with grid data.
        stage = "resample_events"
        node = Resample(
            self._get_nid(stage), **config[self._get_nid(stage)].to_dict()
        )
        dag.add_node(node)
        dag.connect(self._get_nid("events_input_socket"), self._get_nid(stage))
        # Drop NaNs from resampled events.
        # - This node is used because resampling places events on a uniform
        #   time grid, and most of these times will not actually represent
        #   events
        # - The output of this node represents the `normalized` event times
        #   and features
        stage = "dropna_from_resampled_events"
        # TODO(Paul): Might want to expose "how".
        node = DataframeMethodRunner(
            self._get_nid(stage), method="dropna", method_kwargs={"how": "all"}
        )
        dag.add_node(node)
        dag.connect(self._get_nid("resample_events"), self._get_nid(stage))
        # Reindex events according to grid data.
        # - Effectively a restriction
        # - TODO(Paul): Decide whether we instead want "resample_events" to
        #   directly feed into this node (there may be some corner cases of
        #   interest)
        stage = "reindex_events"
        node = YConnector(
            self._get_nid(stage), connector_func=esf.reindex_event_features
        )
        dag.add_node(node)
        dag.connect(
            (self._get_nid("dropna_from_resampled_events"), "df_out"),
            (self._get_nid(stage), "df_in1"),
        )
        dag.connect(
            (self._get_nid("grid_data_input_socket"), "df_out"),
            (self._get_nid(stage), "df_in2"),
        )
        # Fill NaNs with zero (before signal processing).
        # - This node is used because we assume that event data is sparse
        #   compared to the grid data, and because of how NaNs are handled by
        #   `sigp` functions
        stage = "fillna_with_zero"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=lambda x: x.fillna(0),
            col_mode="replace_all",
        )
        dag.add_node(node)
        dag.connect(self._get_nid("reindex_events"), self._get_nid(stage))
        # Generate event signal.
        # - There is opportunity here for problem-specific customization
        # - Here we use a smooth moving average (which can be made equivalent
        #   to an EMA or made more rectangular-like if desired)
        stage = "generate_event_signal"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=sigp.compute_smooth_moving_average,
            **config[self._get_nid(stage)].to_dict(),
            col_mode="replace_all",
        )
        dag.add_node(node)
        dag.connect(self._get_nid("fillna_with_zero"), self._get_nid(stage))
        # Shift event signal (lag it).
        # - Use a positive integer to introduce a lag (e.g., to reflect
        #   ability to trade)
        stage = "shift"
        node = DataframeMethodRunner(
            self._get_nid(stage),
            "shift",
            **config[self._get_nid(stage)].to_dict(),
        )
        dag.add_node(node)
        dag.connect(self._get_nid("generate_event_signal"), self._get_nid(stage))
        # Merge signal with grid data.
        # - The output of this node adds columns from processed event features
        #   to the columns in the grid data
        stage = "merge_event_signal_with_grid"
        node = YConnector(
            self._get_nid(stage),
            connector_func=lambda x, y, **kwargs: x.merge(y, **kwargs),
            connector_kwargs={
                "how": "right",
                "left_index": True,
                "right_index": True,
            },
        )
        dag.add_node(node)
        dag.connect(
            (self._get_nid("shift"), "df_out"), (self._get_nid(stage), "df_in1")
        )
        dag.connect(
            (self._get_nid("grid_data_input_socket"), "df_out"),
            (self._get_nid(stage), "df_in2"),
        )
        # Build local time series.
        # - The output of this node is of interest in exploratory work
        stage = "build_local_ts"
        node = YConnector(
            self._get_nid(stage),
            connector_func=esf.build_local_timeseries,
            **config[self._get_nid(stage)].to_dict(),
        )
        dag.add_node(node)
        dag.connect(
            (self._get_nid("dropna_from_resampled_events"), "df_out"),
            (self._get_nid(stage), "df_in1"),
        )
        dag.connect(
            (self._get_nid("merge_event_signal_with_grid"), "df_out"),
            (self._get_nid(stage), "df_in2"),
        )
        # Model.
        # - One may want to use different models in different situations
        # - As a placeholder, we use a regularized linear model
        # - A linear model is useful for performing a Bayesian analysis of any
        #   supposed event effect
        stage = "model"
        node = SkLearnModel(
            self._get_nid(stage),
            model_func=sklearn.linear_model.Ridge,
            **config[self._get_nid(stage)].to_dict(),
        )
        dag.add_node(node)
        dag.connect(self._get_nid("build_local_ts"), self._get_nid(stage))
        # Merge predictions into grid.
        # - The output of this node is the grid data with all event-related
        #   data added as well, e.g., processed event features and model
        #   predictions
        stage = "merge_predictions"
        node = YConnector(
            self._get_nid(stage),
            connector_func=lambda x, y, **kwargs: x.merge(y, **kwargs),
            connector_kwargs={"left_index": True, "right_index": True},
        )
        dag.add_node(node)
        dag.connect(
            (self._get_nid("build_local_ts"), "df_out"),
            (self._get_nid(stage), "df_in1"),
        )
        dag.connect(
            (self._get_nid("model"), "df_out"), (self._get_nid(stage), "df_in2")
        )
        # Unwrap augmented local time series.
        # - The main purpose of this node is to take model predictions
        #   generated from a model run on local time series and place them
        #   back in chronological order
        stage = "unwrap_local_ts"
        node = YConnector(
            self._get_nid(stage), connector_func=esf.unwrap_local_timeseries
        )
        dag.add_node(node)
        dag.connect(
            (self._get_nid("merge_predictions"), "df_out"),
            (self._get_nid(stage), "df_in1"),
        )
        dag.connect(
            (self._get_nid("grid_data_input_socket"), "df_out"),
            (self._get_nid(stage), "df_in2"),
        )
        return dag


class ContinuousSignalModelBuilder(DagBuilder):
    """
    Configurable pipeline for predicting market data using a continuous signal.

    Market data may also include x-vars and be processed.
    """

    def get_config_template(self) -> cfg.Config:
        """
        Return a reference configuration.
        """
        config = cfg.Config()
        return config

    def get_dag(self, config: cfg.Config, dag: Optional[DAG] = None) -> DAG:
        """
        Pipeline interface nodes:
        - "signal_input_socket"
            - continuous input signal should feed into this node
        - "market_data_input_socket"
            - market data should feed into this node
        - "model_input_socket"
            - modeling node should receive data from this node
        - "model_output_socket"
            - modeling node should send output data to this node
        - "output_socket"
            - pipeline output available from this node

        It is assumed that the input signal and market data have already been
        preprocessed, e.g., put on the same time scales, filtered, etc.
        """
        dag = dag or DAG()
        _LOG.debug("%s", config)
        stage = "signal_input_socket"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=lambda x: x,
            col_mode="replace_all",
        )
        dag.add_node(node)
        stage = "market_data_input_socket"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=lambda x: x,
            col_mode="replace_all",
        )
        dag.add_node(node)
        stage = "merge_signal_with_market_data"
        node = YConnector(
            self._get_nid(stage),
            connector_func=lambda x, y, **kwargs: x.merge(y, **kwargs),
            connector_kwargs={
                "how": "right",
                "left_index": True,
                "right_index": True,
            },
        )
        dag.add_node(node)
        dag.connect(
            (self._get_nid("signal_input_socket"), "df_out"),
            (self._get_nid(stage), "df_in1"),
        )
        dag.connect(
            (self._get_nid("market_data_input_socket"), "df_out"),
            (self._get_nid(stage), "df_in2"),
        )
        # Fill NaNs.
        stage = "fillna"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=lambda x: x.fillna(method="ffill"),
            col_mode="replace_all",
        )
        dag.add_node(node)
        dag.connect(
            self._get_nid("merge_signal_with_market_data"), self._get_nid(stage)
        )
        # Drop NaNs.
        stage = "dropna"
        node = DataframeMethodRunner(
            self._get_nid(stage), method="dropna", method_kwargs={"how": "any"}
        )
        dag.add_node(node)
        dag.connect(self._get_nid("fillna"), self._get_nid(stage))
        # Leave sockets for hooking up a model.
        stage = "model_input_socket"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=lambda x: x,
            col_mode="replace_all",
        )
        dag.add_node(node)
        dag.connect(self._get_nid("dropna"), self._get_nid(stage))
        stage = "model_output_socket"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=lambda x: x,
            col_mode="replace_all",
        )
        dag.add_node(node)
        # Merge predictions of model with xvars, yvars.
        stage = "merge_predictions"
        node = YConnector(
            self._get_nid(stage),
            connector_func=lambda x, y, **kwargs: x.merge(y, **kwargs),
            connector_kwargs={"left_index": True, "right_index": True},
        )
        dag.add_node(node)
        dag.connect(
            (self._get_nid("model_input_socket"), "df_out"),
            (self._get_nid(stage), "df_in1"),
        )
        dag.connect(
            (self._get_nid("model_output_socket"), "df_out"),
            (self._get_nid(stage), "df_in2"),
        )
        stage = "output_socket"
        node = ColumnTransformer(
            self._get_nid(stage),
            transformer_func=lambda x: x,
            col_mode="replace_all",
        )
        dag.add_node(node)
        dag.connect(
            self._get_nid("merge_predictions"), self._get_nid("output_socket"),
        )
        return dag