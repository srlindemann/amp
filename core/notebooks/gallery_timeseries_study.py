# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.2'
#       jupytext_version: 1.2.4
#   kernelspec:
#     display_name: Python [conda env:.conda-develop] *
#     language: python
#     name: conda-env-.conda-develop-py
# ---

# %% [markdown]
# ## Imports

# %%
# %load_ext autoreload
# %autoreload 2
import logging

import numpy as np
import pandas as pd

import core.timeseries_study as tss
import helpers.dbg as dbg
import helpers.env as env
import helpers.printing as pri

# %%
print(env.get_system_signature())
pri.config_notebook()
dbg.init_logger(verbosity=logging.INFO)
_LOG = logging.getLogger(__name__)

# %% [markdown]
# # Generate time series

# %% [markdown]
# ## Daily

# %%
idx = pd.date_range("2018-12-31", "2019-01-31")
vals = np.random.randn(len(idx))
ts_daily = pd.Series(vals, index=idx)
ts_daily.name = "ts"
ts_daily.head()

# %%
ts_daily.plot()

# %% [markdown]
# ## Minutely

# %%
idx = pd.date_range("2018-12-31", "2019-01-31", freq="5T")
vals = np.random.randn(len(idx))
ts_minutely = pd.Series(vals, index=idx)
ts_minutely.name = "ts"
ts_minutely.head()

# %%
ts_minutely.plot()

# %% [markdown]
# # Examples

# %% [markdown]
# ## Daily

# %%
tsds = tss.TimeSeriesDailyStudy(ts_daily)
tsds.execute()

# %% [markdown]
# ## Minutely

# %%
tsms = tss.TimeSeriesMinutelyStudy(ts_minutely)
tsms.execute()

# %%
