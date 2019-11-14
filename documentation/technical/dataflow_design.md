- This is a list of design principles for the `dataflow` component

# Building a DAG

## Invariants
- A DAG is completely represented by:
    - a `config` object
    - a `dag_builder` function

## Config
- The config:
    - Is hierarchical with one subconfig per DAG node
    - Can specify if a block is present or not in a DAG
    - Should only include DAG node configuration parameters, and not information
      about DAG connectivity, which is specified in the DAG builder

## Config builders
- Configs are built through functions that can complete a "template" config with
  some parameters passed from command line
- E.g.,
    ```python
    def get_kibot_returns_config(symbol: str) -> cfg.Config:
        """
        A template configuration for `get_kibot_returns_dag`.
        """
        ...
    ```

## DAG builder methods
- DAG builder methods accept a config and return a DAG
- E.g.,
    ```python
    def get_kibot_returns_dag(config: cfg.Config, dag: dtf.DAG) -> dtf.DAG:
        """
        Build a DAG (which in this case is a linear pipeline) for loading Kibot
        data and generating processed returns.

        The stages are:
          - read Kibot price data
          - compute returns
          - resample returns (optional)
          - zscore returns (optional)
          - filter returns by ATH (optional)

        - `config` must reference required stages and conform to specific node
           interfaces
        """
    ```
- Some DAG builders can also add nodes to user-specified or inferred nodes
  (e.g., a unique sink node) of an existing DAG. Thus builders allow one to
  build a complex DAG by adding in multiple steps subgraphs of nodes.

- The DAG and config builder functions are typically paired, e.g., a function to
  create a config with all and only the params needed by a `dag_builder`

## DAG and Nodes
- The DAG structure does not know about what data is exchanged between nodes.
  Structural assumptions, e.g., column names, can and should be expressed
  through the config
    - `dataflow_core.py` does not impose any constraints on the type of data
      that can be exchanged
    - In practice (e.g., all concrete classes for nodes in `dataflow.py`), we
      assume that `pd.DataFrame`s are propagated
    - The DAG `node`s are wrappers around pandas dataframes
        - E.g., if a node receives a column multi-index dataframe (e.g., with
          multiple instruments and multiple features per instruments), the node
          (should, assuming a well-defined DAG and config) knows how to melt and
          pivot columns

## Keeping `config` and `dag_builder` in sync
- `config` asserts if a `dag_builder` tries to access a hierarchical parameter
  that doesn't exist and reports a meaningful error of what the problem is
- `config` tracks what parameters are accessed by `dag_builder` function
    - a method `sanity_check` is called after the DAG is completely built
      and reports a warning for all the parameters that were not used
    - This is mostly for a sanity check and debugging, so we don't assert

# DAG behavior

## Invariants
- Nodes of the DAG propagate dataframes
    - Dataframes can be column multi-index to represent higher dimensionality
      datasets (e.g., multiple instruments, multiple features for each
      instrument)
    - The index of each dataframe is always composed of `datatime.datetime`
        - For performance reasons, we prefer to use a single time zone (e.g., ET)
          in the name of the columns rather than using `datetimes` with `tzinfo`

- We assume that dataframes are aligned in terms of time scale
    - I.e., the DAG has nodes that explicitly merge / align dataframes
    - When data sources have different time resolutions, typically we perform 
      outer merges either leaving nans or filling with forward fills

## Nodes
- We wrap pandas functions (e.g., from `signal_processing.py`) in Nodes
- `ColumnTransformer` is a very flexible `Node` class that can wrap a wide
  variety of functions
    - The function to use is passed to the `ColumnTransformer` constructor in
      the DAG builder
    - Arguments to forward to the function are passed through
      `transformer_kwargs`
    - Currently `ColumnTransformer` does not allow index-modifying changes (we
      may relax this constraint but continue to enforce it by default)
- `DataframeMethodRunner` can run any `pd.DataFrame` method supported and
  forwards kwargs

# Problems

## One vs multiple graphs

- We still don't have a final answer about this design issue

- Pros of one graph:
    - Everything is in one place
    - One config for the whole graph
- Pros of multiple graphs:
    - Easier to parallelize
    - Easier to manage memory
    - Simpler to configure (maybe), e.g., templatize config
    - One connected component (instead of a number depending upon the number of tickers)

## How to handle multiple features for a single instrument
- E.g., close and volume for a single futures instrument
- In this case we can use a dataframe with two columns `close_price` and
  `volume`
    - Maybe the solution is to keep columns in the same dataframe either if they
      are processed in the same way (i.e., vectorized) or if the computing node
      needs to have to have both features available (like sklearn model)
    - If close_price and volume are "independent", they should go in different
      branches of the graph using a "Y" split

## How to handle multiple instruments?
- E.g., close price for multiple futures

- We pass a dataframe with one column per instrument
- All the transformations are then performed on a column-basis
- We assume that the timeseries are aligned explicitly

## How to handle multiple features with multiple instruments
- E.g., close price, high price, volume for multiple energy futures instrument
- In this case we can use a dataframe with hierarchical columns, where the first
  dimension is the instrument, and the second dimension is the feature

## Irregular DAGs
- E.g., if we have 10 instruments that need to use different models, we could
  build a DAG, instantiating 10 different pipelines
- In general we try to use vectorization any time that is possible
    - E.g., if the computation is the same, instantiate a single DAG working on
      all the 10 instruments in a single dataframe (i.e., vectorization)
    - E.g,. if the computation is the same up to until a point, vectorize the
      common part, and then split the dataframe and use different pipelines

## Namespace vs hierarchical config
- We recognize that sometimes we might want to call the same `dag_builder`
  function multiple times (e.g., a DAG that is built with a loop)
- In this case it's not clear if it would be better to prefix the names of each
  node with a tag to make them unique or use hierarchical DAG
- It seems simpler to use prefix for the tags