# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.2'
#       jupytext_version: 1.2.4
#   kernelspec:
#     display_name: Python [conda env:.conda-p1_develop] *
#     language: python
#     name: conda-env-.conda-p1_develop-py
# ---

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
import logging
import os

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt

# %%
from pylab import rcParams

import core.signal_processing as sp
import helpers.dbg as dbg
import vendors.kibot.utils as kut
# import vendors.particle_one.PartTask269_liquidity_analysis_utils as lau

sns.set()

rcParams["figure.figsize"] = (20, 5)

# %%
TAU = 2


# %%
def get_zscored_prices_diff(price_dict_df, symbol, tau=TAU):
    prices_symbol = price_dict_df[symbol]
    prices_diff = prices_symbol['close'] - prices_symbol['open']
    zscored_prices_diff = sp.rolling_zscore(prices_diff, tau)
    zscored_prices_diff.head()
    abs_zscored_prices_diff = zscored_prices_diff.abs()
    return abs_zscored_prices_diff


def get_top_movements_by_group(price_dict_df,
                               commodity_symbols_kibot,
                               group,
                               n_movements=100):
    zscored_diffs = []
    for symbol in commodity_symbols_kibot[group]:
        zscored_diff = get_zscored_prices_diff(price_dict_df, symbol)
        zscored_diffs.append(zscored_diff)
    zscored_diffs = pd.concat(zscored_diffs, axis=1)
    mean_zscored_diffs = zscored_diffs.mean(axis=1, skipna=True)
    return mean_zscored_diffs.sort_values(ascending=False).head(n_movements)


def get_top_movements_for_symbol(price_dict_df,
                                 symbol,
                                 tau=TAU,
                                 n_movements=100):
    zscored_diffs = get_zscored_prices_diff(price_dict_df, symbol, tau=tau)
    return zscored_diffs.sort_values(ascending=False).head(n_movements)


# %% [markdown]
# # Load CME metadata

# %%
# Change this to library code from #269 once it is merged into master

# %%
_PRODUCT_SPECS_PATH = "/data/prices/product_slate_export_with_contract_specs_20190905.csv"
product_list = pd.read_csv(_PRODUCT_SPECS_PATH)

# %%
product_list.head()

# %%
product_list['Product Group'].value_counts()

# %%
product_list.set_index('Product Group', inplace=True)

# %%
commodity_groups = ['Energy', 'Agriculture', 'Metals']

# %%
commodity_symbols = {
    group: product_list.loc[group]['Globex'].values
    for group in commodity_groups
}

# %%
commodity_symbols

# %% [markdown]
# # Load kibot commodity daily prices

# %%
daily_metadata = kut.read_metadata2()
daily_metadata.head(3)

# %%
len(daily_metadata['Symbol'])

# %%
daily_metadata['Symbol'].nunique()

# %%
len(commodity_symbols['Energy'])

# %%
energy_symbols_kibot = np.intersect1d(daily_metadata['Symbol'].values,
                                      commodity_symbols['Energy'])
energy_symbols_kibot

# %%
len(energy_symbols_kibot)

# %%
commodity_symbols_kibot = {
    group: np.intersect1d(daily_metadata['Symbol'].values,
                          commodity_symbols[group])
    for group in commodity_symbols.keys()
}

# %%
commodity_symbols_kibot

# %%
{
    group: len(commodity_symbols_kibot[group])
    for group in commodity_symbols_kibot.keys()
}

# %%
comm_list = []
for comm_group in commodity_symbols_kibot.values():
    comm_list.extend(list(comm_group))
comm_list[:5]

# %%
file_name = "/data/kibot/All_Futures_Continuous_Contracts_daily/%s.csv.gz"

daily_price_dict_df = kut.read_multiple_symbol_data(comm_list,
                                                    file_name,
                                                    nrows=None)

daily_price_dict_df["CL"].tail(2)

# %% [markdown]
# # Largest movements for a specific symbol

# %%
symbol = "CL"

# %%
cl_prices = daily_price_dict_df[symbol]

# %%
cl_prices_diff = cl_prices['close'] - cl_prices['open']

# %%
zscored_cl_prices_diff = sp.rolling_zscore(cl_prices_diff, TAU)
zscored_cl_prices_diff.head()

# %%
abs_zscored_cl_prices_diff = zscored_cl_prices_diff.abs()

# %%
abs_zscored_cl_prices_diff.max()

# %%
top_100_movemets_cl = abs_zscored_cl_prices_diff.sort_values(
    ascending=False).head(100)

# %%
top_100_movemets_cl.plot(kind='bar')
ax = plt.gca()
xlabels = [item.get_text()[:10] for item in ax.get_xticklabels()]
ax.set_xticklabels(xlabels)
plt.title(
    f'Largest price movements in a single day (in z-score space) for {symbol} symbol'
)
plt.show()

# %%
top_100_movemets_cl.index.year.value_counts(sort=False).plot(kind='bar')
plt.title("How many of the top-100 price movements occured during each year")
plt.show()

# %% [markdown]
# # Largest movement for energy group

# %%
group = 'Energy'

# %%
commodity_symbols_kibot[group]

# %%
zscored_diffs = []
for symbol in commodity_symbols_kibot[group]:
    zscored_diff = get_zscored_prices_diff(daily_price_dict_df, symbol)
    zscored_diffs.append(zscored_diff)

# %%
zscored_diffs = pd.concat(zscored_diffs, axis=1)
zscored_diffs.head()

# %%
mean_zscored_diffs = zscored_diffs.mean(axis=1, skipna=True)

# %%
mean_zscored_diffs.head()

# %%
mean_zscored_diffs.tail()

# %%
mean_zscored_diffs.sort_values(ascending=False).head(100)

# %% [markdown]
# # Get largest movements for each group

# %%
top_100_movements_by_group = {
    group: get_top_movements_by_group(daily_price_dict_df,
                                      commodity_symbols_kibot, group)
    for group in commodity_symbols_kibot.keys()
}

# %%
top_100_movements_by_group.keys()

# %%
top_100_movements_by_group['Energy'].head()

# %%
top_100_movements_by_group['Agriculture'].head()

# %%
top_100_movements_by_group['Metals'].head()

# %% [markdown]
# # 5-minute movements

# %%
minutely_metadata = kut.read_metadata1()

# %%
minutely_metadata.head()

# %%
np.array_equal(minutely_metadata['Symbol'].values, minutely_metadata['Symbol'].values)

# %%
file_name = "/data/kibot/All_Futures_Continuous_Contracts_1min/%s.csv.gz"

minutely_price_dict_df = kut.read_multiple_symbol_data(comm_list,
                                                       file_name,
                                                       nrows=None)

minutely_price_dict_df["CL"].tail(2)

# %%
minutely_price_dict_df['CL'].head()

# %%
five_min_prices = minutely_price_dict_df['CL'].set_index('datetime').resample('5Min').sum()
