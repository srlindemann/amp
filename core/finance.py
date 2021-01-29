import datetime
import logging
from typing import Any, Dict, Optional, Union, cast

import numpy as np
import pandas as pd
import statsmodels.api as sm

import core.signal_processing as sigp
import helpers.dataframe as hdf
import helpers.dbg as dbg
import helpers.printing as pri

_LOG = logging.getLogger(__name__)


def remove_dates_with_no_data(
    df: pd.DataFrame, report_stats: bool
) -> pd.DataFrame:
    """Given a df indexed with timestamps, scan the data by date and filter out
    all the data when it's all nans.

    :return: filtered df
    """
    # This is not strictly necessary.
    dbg.dassert_strictly_increasing_index(df)
    #
    removed_days = []
    df_out = []
    num_days = 0
    for date, df_tmp in df.groupby(df.index.date):
        if np.isnan(df_tmp).all(axis=1).all():
            _LOG.debug("No data on %s", date)
            removed_days.append(date)
        else:
            df_out.append(df_tmp)
        num_days += 1
    df_out = pd.concat(df_out)
    dbg.dassert_strictly_increasing_index(df_out)
    #
    if report_stats:
        _LOG.info("df.index in [%s, %s]", df.index.min(), df.index.max())
        removed_perc = pri.perc(df.shape[0] - df_out.shape[0], df.shape[0])
        _LOG.info("Rows removed: %s", removed_perc)
        #
        removed_perc = pri.perc(len(removed_days), num_days)
        _LOG.info("Number of removed days: %s", removed_perc)
        # Find week days.
        removed_weekdays = [d for d in removed_days if d.weekday() < 5]
        removed_perc = pri.perc(len(removed_weekdays), len(removed_days))
        _LOG.info("Number of removed weekdays: %s", removed_perc)
        _LOG.info("Weekdays removed: %s", ", ".join(map(str, removed_weekdays)))
        #
        removed_perc = pri.perc(
            len(removed_days) - len(removed_weekdays), len(removed_days)
        )
        _LOG.info("Number of removed weekend days: %s", removed_perc)
        #

    return df_out


def resample(
    df: pd.DataFrame, agg_interval: Union[str, pd.Timedelta, pd.DateOffset]
) -> pd.DataFrame:
    """Resample returns (using sum) using our timing convention."""
    dbg.dassert_strictly_increasing_index(df)
    resampler = sigp.resample(df, rule=agg_interval, closed="left")
    rets = resampler.sum()
    return rets


def set_non_ath_to_nan(
    df: pd.DataFrame,
    start_time: Optional[datetime.time] = None,
    end_time: Optional[datetime.time] = None,
) -> pd.DataFrame:
    """Filter according to active trading hours.

    We assume time intervals are left closed, right open, labeled right.

    Row is not set to `np.nan` iff its `time` satisifies
      - `start_time < time`, and
      - `time <= end_time`
    """
    dbg.dassert_isinstance(df.index, pd.DatetimeIndex)
    dbg.dassert_strictly_increasing_index(df)
    if start_time is None:
        start_time = datetime.time(9, 30)
    if end_time is None:
        end_time = datetime.time(16, 0)
    dbg.dassert_lte(start_time, end_time)
    #
    times = df.index.time
    mask = (start_time < times) & (times <= end_time)
    #
    df = df.copy()
    df[~mask] = np.nan
    return df


def set_weekends_to_nan(df: pd.DataFrame) -> pd.DataFrame:
    """Filter out weekends."""
    dbg.dassert_isinstance(df.index, pd.DatetimeIndex)
    # 5 = Saturday, 6 = Sunday.
    mask = df.index.dayofweek.isin([5, 6])
    df = df.copy()
    df[mask] = np.nan
    return df


# #############################################################################
# Returns calculation and helpers.
# #############################################################################


def resample_time_bars(
    df: pd.DataFrame,
    rule: str,
    *,
    return_cols: Optional[list] = None,
    return_agg_func: Optional[str] = None,
    return_agg_func_kwargs: Optional[dict] = None,
    price_cols: Optional[list] = None,
    price_agg_func: Optional[str] = None,
    price_agg_func_kwargs: Optional[list] = None,
    volume_cols: Optional[list] = None,
    volume_agg_func: Optional[str] = None,
    volume_agg_func_kwargs: Optional[list] = None,
) -> pd.DataFrame:
    """
    Convenience resampler for time bars.

    Features:
    - Respects causality
    - Chooses sensible defaults:
      - returns are summed
      - prices are averaged
      - volume is summed
    - NaN intervals remain NaN
    - Defaults may be overidden (e.g., choose `last` instead of `mean` for
      price)

    :param df: input dataframe with datetime index
    :param rule: resampling frequency
    :param return_cols: columns containing returns
    :param return_agg_func: aggregation function
    :param return_agg_func_kwargs: kwargs
    :param price_cols: columns containing price
    :param price_agg_func: aggregation function
    :param price_agg_func_kwargs: kwargs
    :param volume_cols: columns containing volume
    :param volume_agg_func: aggregation function
    :param volume_agg_func_kwargs: kwargs
    :return: dataframe of resampled time bars
    """
    dbg.dassert_isinstance(df, pd.DataFrame)
    # Helper
    def _resample_financial(df, rule, cols, agg_func, agg_func_kwargs):
        dbg.dassert(not df.empty)
        dbg.dassert_isinstance(cols, list)
        dbg.dassert(cols, msg="`cols` must be nonempty.")
        dbg.dassert_is_subset(cols, df.columns)
        resampler = sigp.resample(df[cols], rule=rule)
        resampled = resampler.agg(agg_func, **agg_func_kwargs)
        return resampled

    result_df = pd.DataFrame()
    # Maybe resample returns.
    if return_cols:
        return_agg_func = return_agg_func or "sum"
        return_agg_func_kwargs = return_agg_func_kwargs or {"min_count": 1}
        return_df = _resample_financial(
            df, rule, return_cols, return_agg_func, return_agg_func_kwargs
        )
        result_df = result_df.merge(
            return_df, how="outer", left_index=True, right_index=True
        )
        dbg.dassert(result_df.index.freq)
    # Maybe resample prices.
    if price_cols:
        price_agg_func = price_agg_func or "mean"
        price_agg_func_kwargs = price_agg_func_kwargs or {}
        price_df = _resample_financial(
            df, rule, price_cols, price_agg_func, price_agg_func_kwargs
        )
        result_df = result_df.merge(
            price_df, how="outer", left_index=True, right_index=True
        )
        dbg.dassert(result_df.index.freq)
    # Maybe resample volume.
    if volume_cols:
        volume_agg_func = volume_agg_func or "sum"
        volume_agg_func_kwargs = volume_agg_func_kwargs or {"min_count": 1}
        volume_df = _resample_financial(
            df, rule, volume_cols, volume_agg_func, volume_agg_func_kwargs
        )
        result_df = result_df.merge(
            volume_df, how="outer", left_index=True, right_index=True
        )
        dbg.dassert(result_df.index.freq)
    return result_df


def compute_twap_vwap(
    df: pd.DataFrame,
    rule: str,
    *,
    price_col: Any,
    volume_col: Any,
) -> pd.Series:
    """
    Compute VWAP from price and volume.

    :param df: input dataframe with datetime index
    :param rule: resampling frequency and vwap aggregation window
    :param price_col: price for bar
    :param volume_col: volume for bar
    :return: vwap series
    """
    dbg.dassert_isinstance(df, pd.DataFrame)
    dbg.dassert(df.index.freq)
    dbg.dassert_in(price_col, df.columns)
    dbg.dassert_in(volume_col, df.columns)
    price = df[price_col]
    volume = df[volume_col]
    # Weight price according to volume.
    volume_weighted_price = price.multiply(volume)
    # Resample using `rule`.
    resampled_volume_weighted_price = sigp.resample(
        volume_weighted_price, rule=rule
    ).sum(min_count=1)
    resampled_volume = sigp.resample(volume, rule=rule).sum(min_count=1)
    # Complete the VWAP calculation.
    vwap = resampled_volume_weighted_price.divide(resampled_volume)
    # Replace infs with NaNs.
    vwap = vwap.replace([-np.inf, np.inf], np.nan)
    vwap.name = "vwap"
    # Calculate TWAP, but preserve NaNs for all-NaN bars.
    twap = sigp.resample(price, rule=rule).mean()
    twap.loc[resampled_volume_weighted_price.isna()] = np.nan
    twap.name = "twap"
    #
    return pd.concat([vwap, twap], axis=1)


def compute_ret_0(
    prices: Union[pd.Series, pd.DataFrame], mode: str
) -> Union[pd.Series, pd.DataFrame]:
    if mode == "pct_change":
        ret_0 = prices.divide(prices.shift(1)) - 1
    elif mode == "log_rets":
        ret_0 = np.log(prices) - np.log(prices.shift(1))
    elif mode == "diff":
        # TODO(gp): Use shifts for clarity, e.g.,
        # ret_0 = prices - prices.shift(1)
        ret_0 = prices.diff()
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    if isinstance(ret_0, pd.Series):
        ret_0.name = "ret_0"
    return ret_0


def compute_ret_0_from_multiple_prices(
    prices: Dict[str, pd.DataFrame], col_name: str, mode: str
) -> pd.DataFrame:
    dbg.dassert_isinstance(prices, dict)
    rets = []
    for s, price_df in prices.items():
        _LOG.debug("Processing s=%s", s)
        rets_tmp = compute_ret_0(price_df[col_name], mode)
        rets_tmp = pd.DataFrame(rets_tmp)
        rets_tmp.columns = ["%s_ret_0" % s]
        rets.append(rets_tmp)
    rets = pd.concat(rets, sort=True, axis=1)
    return rets


# TODO(GPPJ): Add a decorator for handling multi-variate prices as in
#  https://github.com/ParticleDev/commodity_research/issues/568


def compute_prices_from_rets(
    price: pd.Series,
    rets: pd.Series,
    mode: str,
) -> pd.Series:
    """
    Compute price p_1 at moment t_1 with given price p_0 at t_0 and return ret_1
    
    This implies that input has ret_1 at moment t_1 and uses price p_0 from 
    previous step t_0. If we have forward returns instead (ret_1 and p_0 are at 
    t_0), we need to shift input returns index one step ahead. 

    :param price: series with prices
    :param rets: series with returns
    :param mode: returns mode as in compute_ret_0 
    :return: series with computed prices
    """
    dbg.dassert_isinstance(price, pd.Series)
    dbg.dassert_isinstance(rets, pd.Series)
    price = price.reindex(rets.index).shift(1)
    if mode == "pct_change":
        price_pred = price * (rets + 1)
    elif mode == "log_rets":
        price_pred = price * np.exp(rets)
    elif mode == "diff":
        price_pred = price + rets
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    return price_pred


def convert_log_rets_to_pct_rets(
    log_rets: Union[float, pd.Series, pd.DataFrame]
) -> Union[float, pd.Series, pd.DataFrame]:
    """Convert log returns to percentage returns.

    :param log_rets: time series of log returns
    :return: time series of percentage returns
    """
    return np.exp(log_rets) - 1


def convert_pct_rets_to_log_rets(
    pct_rets: Union[float, pd.Series, pd.DataFrame]
) -> Union[float, pd.Series, pd.DataFrame]:
    """Convert percentage returns to log returns.

    :param pct_rets: time series of percentage returns
    :return: time series of log returns
    """
    return np.log(pct_rets + 1)


def rescale_to_target_annual_volatility(
    srs: pd.Series, volatility: float
) -> pd.Series:
    """Rescale srs to achieve target annual volatility.

    NOTE: This is not a causal rescaling, but SR is an invariant.

    :param srs: returns series. Index must have `freq`.
    :param volatility: annualized volatility as a proportion (e.g., `0.1`
        corresponds to 10% annual volatility)
    :return: rescaled returns series
    """
    dbg.dassert_isinstance(srs, pd.Series)
    scale_factor = compute_volatility_normalization_factor(
        srs, target_volatility=volatility
    )
    return scale_factor * srs


def compute_inverse_volatility_weights(df: pd.DataFrame) -> pd.Series:
    """Calculate inverse volatility relative weights.

    :param df: cols contain log returns
    :return: series of weights
    """
    dbg.dassert_isinstance(df, pd.DataFrame)
    dbg.dassert(not df.columns.has_duplicates)
    # Compute inverse volatility weights.
    # The result of `compute_volatility_normalization_factor()`
    # is independent of the `target_volatility`.
    weights = df.apply(
        lambda x: compute_volatility_normalization_factor(
            x, target_volatility=0.1
        )
    )
    # Replace inf's with 0's in weights.
    weights.replace([np.inf, -np.inf], np.nan, inplace=True)
    # Rescale weights to percentages.
    weights /= weights.sum()
    weights.name = "weights"
    # Replace NaN with zero for weights.
    weights = hdf.apply_nan_mode(weights, mode="fill_with_zero")
    return weights


def aggregate_log_rets(df: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Compute aggregate log returns.

    :param df: cols contain log returns
    :param weights: series of weights
    :return: series of log returns
    """
    dbg.dassert_isinstance(df, pd.DataFrame)
    dbg.dassert(not df.columns.has_duplicates)
    dbg.dassert(df.columns.equals(weights.index))
    df = df.apply(
        lambda x: rescale_to_target_annual_volatility(x, weights[x.name])
    )
    df = df.apply(convert_log_rets_to_pct_rets)
    df = df.mean(axis=1)
    srs = df.squeeze()
    srs = convert_pct_rets_to_log_rets(srs)
    return srs


def compute_volatility_normalization_factor(
    srs: pd.Series, target_volatility: float
) -> float:
    """Compute scale factor of a series according to a target volatility.

    :param srs: returns series. Index must have `freq`.
    :param target_volatility: target volatility as a proportion (e.g., `0.1`
        corresponds to 10% annual volatility)
    :return: scale factor
    """
    dbg.dassert_isinstance(srs, pd.Series)
    ppy = hdf.infer_sampling_points_per_year(srs)
    srs = hdf.apply_nan_mode(srs, mode="fill_with_zero")
    scale_factor = target_volatility / (np.sqrt(ppy) * srs.std())
    _LOG.debug("`scale_factor`=%f", scale_factor)
    scale_factor = cast(float, scale_factor)
    return scale_factor


# TODO(*): Consider moving to `statistics.py`.
# #############################################################################
# Returns stats.
# #############################################################################


def compute_kratio(log_rets: pd.Series) -> float:
    """Calculate K-Ratio of a time series of log returns.

    :param log_rets: time series of log returns
    :return: K-Ratio
    """
    dbg.dassert_isinstance(log_rets, pd.Series)
    dbg.dassert(log_rets.index.freq)
    log_rets = hdf.apply_nan_mode(log_rets, mode="fill_with_zero")
    cum_rets = log_rets.cumsum()
    # Fit the best line to the daily rets.
    x = range(len(cum_rets))
    x = sm.add_constant(x)
    reg = sm.OLS(cum_rets, x)
    model = reg.fit()
    # Compute k-ratio as slope / std err of slope.
    kratio = model.params[1] / model.bse[1]
    # Adjust k-ratio by the number of observations and points per year.
    ppy = hdf.infer_sampling_points_per_year(log_rets)
    kratio = kratio * np.sqrt(ppy) / len(log_rets)
    kratio = cast(float, kratio)
    return kratio


def compute_drawdown(log_rets: pd.Series) -> pd.Series:
    r"""Calculate drawdown of a time series of log returns.

    Define the drawdown at index location j to be
        d_j := max_{0 \leq i \leq j} \log(p_i / p_j)
    where p_k is price. Though this definition is in terms of prices, we
    calculate the drawdown series using log returns.

    Using this definition, drawdown is always nonnegative.

    :param log_rets: time series of log returns
    :return: drawdown time series
    """
    dbg.dassert_isinstance(log_rets, pd.Series)
    log_rets = hdf.apply_nan_mode(log_rets, mode="fill_with_zero")
    cum_rets = log_rets.cumsum()
    running_max = np.maximum.accumulate(cum_rets)  # pylint: disable=no-member
    drawdown = running_max - cum_rets
    return drawdown


def compute_perc_loss_from_high_water_mark(log_rets: pd.Series) -> pd.Series:
    """Calculate drawdown in terms of percentage loss.

    :param log_rets: time series of log returns
    :return: drawdown time series as percentage loss
    """
    dd = compute_drawdown(log_rets)
    return 1 - np.exp(-dd)


def compute_time_under_water(log_rets: pd.Series) -> pd.Series:
    """Generate time under water series.

    :param log_rets: time series of log returns
    :return: series of number of consecutive time points under water
    """
    drawdown = compute_drawdown(log_rets)
    underwater_mask = drawdown != 0
    # Cumulatively count number of values in True/False groups.
    # Calculate the start of each underwater series.
    underwater_change = underwater_mask != underwater_mask.shift()
    # Assign each underwater series unique number, repeated inside each series.
    underwater_groups = underwater_change.cumsum()
    # Use `.cumcount()` on each underwater series.
    cumulative_count_groups = underwater_mask.groupby(
        underwater_groups
    ).cumcount()
    cumulative_count_groups += 1
    # Set zero drawdown counts to zero.
    n_timepoints_underwater = underwater_mask * cumulative_count_groups
    return n_timepoints_underwater


def compute_turnover(
    pos: pd.Series, unit: Optional[str] = None, nan_mode: Optional[str] = None
) -> pd.Series:
    """Compute turnover for a sequence of positions.

    :param pos: sequence of positions
    :param unit: desired output unit (e.g. 'B', 'W', 'M', etc.)
    :param nan_mode: argument for hdf.apply_nan_mode()
    :return: turnover
    """
    dbg.dassert_isinstance(pos, pd.Series)
    dbg.dassert(pos.index.freq)
    nan_mode = nan_mode or "ffill"
    pos = hdf.apply_nan_mode(pos, mode=nan_mode)
    numerator = pos.diff().abs()
    denominator = (pos.abs() + pos.shift().abs()) / 2
    if unit:
        numerator = sigp.resample(numerator, rule=unit).sum()
        denominator = sigp.resample(denominator, rule=unit).sum()
    turnover = numerator / denominator
    # Raise if we upsample.
    if len(turnover) > len(pos):
        raise ValueError("Upsampling is not allowed.")
    return turnover


def compute_average_holding_period(
    pos: pd.Series, unit: Optional[str] = None, nan_mode: Optional[str] = None
) -> pd.Series:
    """Compute average holding period for a sequence of positions.

    :param pos: sequence of positions
    :param unit: desired output unit (e.g. 'B', 'W', 'M', etc.)
    :param nan_mode: argument for hdf.apply_nan_mode()
    :return: average holding period in specified units
    """
    unit = unit or "B"
    dbg.dassert_isinstance(pos, pd.Series)
    dbg.dassert(pos.index.freq)
    pos_freq_in_year = hdf.infer_sampling_points_per_year(pos)
    unit_freq_in_year = hdf.infer_sampling_points_per_year(
        sigp.resample(pos, rule=unit).sum()
    )
    dbg.dassert_lte(
        unit_freq_in_year,
        pos_freq_in_year,
        msg=f"Upsampling pos freq={pd.infer_freq(pos.index)} to unit freq={unit} is not allowed",
    )
    nan_mode = nan_mode or "ffill"
    pos = hdf.apply_nan_mode(pos, mode=nan_mode)
    unit_coef = unit_freq_in_year / pos_freq_in_year
    average_holding_period = (
        pos.abs().mean() / pos.diff().abs().mean()
    ) * unit_coef
    return average_holding_period


def compute_bet_runs(
    positions: pd.Series, nan_mode: Optional[str] = None
) -> pd.Series:
    """Calculate runs of long/short bets.

    A bet "run" is a (maximal) series of positions on the same "side", e.g.,
    long or short.

    :param positions: series of long/short positions
    :return: series of -1/0/1 with 1's indicating long bets and -1 indicating
        short bets
    """
    dbg.dassert_monotonic_index(positions)
    # Forward fill NaN positions by default (e.g., do not assume they are
    # closed out).
    nan_mode = nan_mode or "ffill"
    positions = hdf.apply_nan_mode(positions, mode=nan_mode)
    # Locate zero positions so that we can avoid dividing by zero when
    # determining bet sign.
    zero_mask = positions == 0
    # Calculate bet "runs".
    bet_runs = positions.copy()
    bet_runs.loc[~zero_mask] /= np.abs(bet_runs.loc[~zero_mask])
    return bet_runs


def compute_bet_starts(
    positions: pd.Series, nan_mode: Optional[str] = None
) -> pd.Series:
    """Calculate the start of each new bet.

    :param positions: series of long/short positions
    :return: a series with a +1 at the start of each new long bet and a -1 at
        the start of each new short bet; 0 indicates continuation of bet and
        `NaN` indicates absence of bet.
    """
    bet_runs = compute_bet_runs(positions, nan_mode)
    # Determine start of bets.
    bet_starts = bet_runs.subtract(bet_runs.shift(1, fill_value=0), fill_value=0)
    # TODO(*): Consider factoring out this operation.
    # Locate zero positions so that we can avoid dividing by zero when
    # determining bet sign.
    bet_starts_zero_mask = bet_starts == 0
    bet_starts.loc[~bet_starts_zero_mask] /= np.abs(
        bet_starts.loc[~bet_starts_zero_mask]
    )
    # Set zero bet runs to `NaN`.
    bet_runs_zero_mask = bet_runs == 0
    bet_starts.loc[bet_runs_zero_mask] = np.nan
    bet_starts.loc[bet_runs.isna()] = np.nan
    return bet_starts


def compute_bet_ends(
    positions: pd.Series, nan_mode: Optional[str] = None
) -> pd.Series:
    """Calculate the end of each bet.

    NOTE: This function is not casual (because of our choice of indexing).

    :param positions: as in `compute_bet_starts()`
    :param nan_mode: as in `compute_bet_starts()`
    :return: as in `compute_bet_starts()`, but with long/short bet indicator at
        the last time of the bet. Note that this is not casual.
    """
    # Apply the NaN mode casually (e.g., `ffill` is not time reversible).
    nan_mode = nan_mode or "ffill"
    positions = hdf.apply_nan_mode(positions, mode=nan_mode)
    # Calculate bet ends by calculating the bet starts of the reversed series.
    reversed_positions = positions.iloc[::-1]
    reversed_bet_starts = compute_bet_starts(reversed_positions, nan_mode=None)
    bet_ends = reversed_bet_starts.iloc[::-1]
    return bet_ends


def compute_signed_bet_lengths(
    positions: pd.Series,
    nan_mode: Optional[str] = None,
) -> pd.Series:
    """Calculate lengths of bets (in sampling freq).

    :param positions: series of long/short positions
    :param nan_mode: argument for hdf.apply_nan_mode()
    :return: signed lengths of bets, i.e., the sign indicates whether the
        length corresponds to a long bet or a short bet. Index corresponds to
        end of bet (not causal).
    """
    bet_runs = compute_bet_runs(positions, nan_mode)
    bet_starts = compute_bet_starts(positions, nan_mode)
    bet_ends = compute_bet_ends(positions, nan_mode)
    # Sanity check indices.
    dbg.dassert(bet_runs.index.equals(bet_starts.index))
    dbg.dassert(bet_starts.index.equals(bet_ends.index))
    # Get starts of bets or zero positions runs (zero positions are filled with
    # `NaN`s in `compute_bet_runs`).
    bet_starts_idx = bet_starts.loc[bet_starts != 0].dropna().index
    bet_ends_idx = bet_ends.loc[bet_ends != 0].dropna().index
    # To calculate lengths of bets, we take a running cumulative sum of
    # absolute values so that bet lengths can be calculated by subtracting
    # the value at the beginning of each bet from its value at the end.
    bet_runs_abs_cumsum = bet_runs.abs().cumsum()
    # Align bet starts and ends for vectorized subtraction.
    t0s = bet_runs_abs_cumsum.loc[bet_starts_idx].reset_index(drop=True)
    t1s = bet_runs_abs_cumsum.loc[bet_ends_idx].reset_index(drop=True)
    # Subtract and correct for off-by-one.
    bet_lengths = t1s - t0s + 1
    # Recover bet signs (positive for long, negative for short).
    bet_lengths = bet_lengths * bet_starts.loc[bet_starts_idx].reset_index(
        drop=True
    )
    # Reindex according to the bet ends index.
    bet_length_srs = pd.Series(
        index=bet_ends_idx, data=bet_lengths.values, name=positions.name
    )
    return bet_length_srs


def compute_returns_per_bet(
    positions: pd.Series, log_rets: pd.Series, nan_mode: Optional[str] = None
) -> pd.Series:
    """Calculate returns for each bet.

    :param positions: series of long/short positions
    :param log_rets: log returns
    :param nan_mode: argument for hdf.apply_nan_mode()
    :return: signed returns for each bet, index corresponds to the last date of
        bet
    """
    dbg.dassert(positions.index.equals(log_rets.index))
    dbg.dassert_strictly_increasing_index(log_rets)
    bet_ends = compute_bet_ends(positions, nan_mode)
    # Retrieve locations of bet starts and bet ends.
    bet_ends_idx = bet_ends.loc[bet_ends != 0].dropna().index
    pnl_bets = log_rets * positions
    bet_rets_cumsum = pnl_bets.cumsum().ffill()
    # Select rets cumsum for periods when bets end.
    bet_rets_cumsum_ends = bet_rets_cumsum.loc[bet_ends_idx].reset_index(
        drop=True
    )
    # Difference between rets cumsum of bet ends is equal to the rets cumsum
    # for the time between these bet ends i.e. rets cumsum per bet.
    rets_per_bet = bet_rets_cumsum_ends.diff()
    # The 1st element of rets_per_bet equals the 1st one of bet_rets_cumsum_ends
    # because it is the first bet so nothing to subtract from it.
    rets_per_bet[0] = bet_rets_cumsum_ends[0]
    rets_per_bet = pd.Series(
        data=rets_per_bet.values, index=bet_ends_idx, name=log_rets.name
    )
    return rets_per_bet


def compute_annualized_return(srs: pd.Series) -> float:
    """Annualize mean return.

    :param srs: series with datetimeindex with `freq`
    :return: annualized return; pct rets if `srs` consists of pct rets,
        log rets if `srs` consists of log rets.
    """
    srs = hdf.apply_nan_mode(srs, mode="fill_with_zero")
    ppy = hdf.infer_sampling_points_per_year(srs)
    mean_rets = srs.mean()
    annualized_mean_rets = ppy * mean_rets
    annualized_mean_rets = cast(float, annualized_mean_rets)
    return annualized_mean_rets


def compute_annualized_volatility(srs: pd.Series) -> float:
    """Annualize sample volatility.

    :param srs: series with datetimeindex with `freq`
    :return: annualized volatility (stdev)
    """
    srs = hdf.apply_nan_mode(srs, mode="fill_with_zero")
    ppy = hdf.infer_sampling_points_per_year(srs)
    std = srs.std()
    annualized_volatility = np.sqrt(ppy) * std
    annualized_volatility = cast(float, annualized_volatility)
    return annualized_volatility
