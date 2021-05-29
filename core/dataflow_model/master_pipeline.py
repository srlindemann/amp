import logging
import os

import core.config_builders as ccbuild
import core.dataflow as cdataf
import helpers.dbg as dbg
import helpers.env as henv
import helpers.pickle_ as hpickl
import helpers.printing as hprint

_LOG = logging.getLogger(__name__)


# TODO(gp): -> run_dag, run_model?
# TODO(gp): if this was a script there would be more separation and easier
#  to save output to log. But then we need to pass the config in the same way
#  we pass it to a notebook but using command-line opts instead of env vars.
def run_pipeline(config_builder, config_idx, dst_dir):
    """
    Implement the master pipeline to:
    - create a DAG
    - run it
    - save the generated `ResultBundle`

    All parameters are passed through a `Config`.
    """
    config = ccbuild.get_config_from_params(config_builder, config_idx, dst_dir)

    dag_config = config.pop("DAG")

    dag_runner = cdataf.PredictionDagRunner(dag_config,
                                            config["meta"]["dag_builder"])
    # TODO(gp): Maybe save the drawing to file?
    #cdataf.draw(dag_runner.dag)

    # TODO(gp): Why passing function instead of the values directly?
    if "set_fit_intervals" in config["meta"].to_dict():
        dag_runner.set_fit_intervals(
            **config["meta", "set_fit_intervals", "func_kwargs"].to_dict()
        )
    if "set_predict_intervals" in config["meta"].to_dict():
        dag_runner.set_predict_intervals(
            **config["meta", "set_predict_intervals", "func_kwargs"].to_dict()
        )

    fit_result_bundle = dag_runner.fit()

    payload = ccbuild.get_config_from_nested_dict({"config": config})

    if "run_oos" in config["meta"].to_dict().keys() and config["meta"]:
        result_bundle = dag_runner.predict()
        payload["fit_result_bundle"] = fit_result_bundle.to_config()
    else:
        result_bundle = fit_result_bundle

    result_bundle.payload = payload

    # TODO(gp): We could pass the payload back and let _run_pipeline take care
    #  of that.
    # TODO(gp): Make sure that the meta part has the right info.
    #dbg.dassert_
    path = os.path.join(
        config["meta", "experiment_result_dir"], "result_bundle.pkl"
    )
    hpickl.to_pickle(result_bundle.to_config().to_dict(), path)