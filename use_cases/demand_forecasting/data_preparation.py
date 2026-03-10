"""
Data Preparation for Demand Forecasting

Prepares healthcare order data for forecasting models by:
- Aggregating orders by time periods
- Creating time series features
- Handling missing values and outliers
- Splitting into train/test sets
"""

from typing import Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


def prepare_forecasting_data(
    orders_df: pd.DataFrame,
    target_column: str = "quantity",
    time_column: str = "order_date",
    group_by: Optional[str] = None,
    frequency: str = "D",
    forecast_horizon: int = 30,
    test_size: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Prepare data for demand forecasting models.

    Args:
        orders_df: DataFrame with order data
        target_column: Column to forecast (e.g., 'quantity', 'total_amount')
        time_column: Time column name
        group_by: Column to group by (e.g., 'pharmacy_id', 'product_id')
        frequency: Time frequency for aggregation ('D', 'W', 'M')
        forecast_horizon: Number of periods to forecast
        test_size: Fraction of data to use for testing

    Returns:
        Tuple of (train_data, test_data, full_data)
    """
    logger.info(f"Preparing forecasting data for {target_column}")

    # Convert time column to datetime
    orders_df[time_column] = pd.to_datetime(orders_df[time_column])

    # Group and aggregate data
    if group_by:
        # Group by entity and time
        agg_data = (
            orders_df.groupby([group_by, time_column])[target_column]
            .sum()
            .reset_index()
        )
        agg_data = agg_data.set_index(time_column)

        # Create separate time series for each group
        grouped_series = {}
        for group_id in agg_data[group_by].unique():
            group_data = agg_data[agg_data[group_by] == group_id][target_column]
            group_data = group_data.resample(frequency).sum().fillna(0)
            grouped_series[group_id] = group_data

        # Combine all series
        full_data = pd.concat(grouped_series, axis=1)
        full_data.columns = [f"{group_by}_{col}" for col in full_data.columns]
    else:
        # Single time series
        agg_data = orders_df.groupby(time_column)[target_column].sum()
        full_data = agg_data.resample(frequency).sum().fillna(0)
        full_data = full_data.to_frame(target_column)

    # Add time-based features
    full_data = add_time_features(full_data)

    # Add lag features
    full_data = add_lag_features(full_data, target_column, lags=[1, 7, 14, 30])

    # Add rolling statistics
    full_data = add_rolling_features(full_data, target_column, windows=[7, 14, 30])

    # Remove rows with NaN values (from lag features)
    full_data = full_data.dropna()

    # Split into train/test
    split_idx = int(len(full_data) * (1 - test_size))
    train_data = full_data.iloc[:split_idx]
    test_data = full_data.iloc[split_idx:]

    logger.info(
        f"Data prepared: {len(train_data)} train samples, {len(test_data)} test samples"
    )
    logger.info(f"Features: {list(full_data.columns)}")

    return train_data, test_data, full_data


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time-based features to the dataframe."""
    df = df.copy()

    # Basic time features
    df["year"] = df.index.year
    df["month"] = df.index.month
    df["day"] = df.index.day
    df["dayofweek"] = df.index.dayofweek
    df["dayofyear"] = df.index.dayofyear
    df["week"] = df.index.isocalendar().week
    df["quarter"] = df.index.quarter

    # Cyclical encoding for periodic features
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["dayofweek_sin"] = np.sin(2 * np.pi * df["dayofweek"] / 7)
    df["dayofweek_cos"] = np.cos(2 * np.pi * df["dayofweek"] / 7)

    return df


def add_lag_features(df: pd.DataFrame, target_column: str, lags: list) -> pd.DataFrame:
    """Add lag features for the target variable."""
    df = df.copy()

    for lag in lags:
        df[f"{target_column}_lag_{lag}"] = df[target_column].shift(lag)

    return df


def add_rolling_features(
    df: pd.DataFrame, target_column: str, windows: list
) -> pd.DataFrame:
    """Add rolling window statistics."""
    df = df.copy()

    for window in windows:
        df[f"{target_column}_rolling_mean_{window}"] = (
            df[target_column].rolling(window=window).mean()
        )
        df[f"{target_column}_rolling_std_{window}"] = (
            df[target_column].rolling(window=window).std()
        )
        df[f"{target_column}_rolling_min_{window}"] = (
            df[target_column].rolling(window=window).min()
        )
        df[f"{target_column}_rolling_max_{window}"] = (
            df[target_column].rolling(window=window).max()
        )

    return df


def create_forecast_dataframe(
    last_date: pd.Timestamp, forecast_horizon: int, frequency: str = "D"
) -> pd.DataFrame:
    """Create a dataframe for future dates to make forecasts."""
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1), periods=forecast_horizon, freq=frequency
    )

    future_df = pd.DataFrame(index=future_dates)
    future_df = add_time_features(future_df)

    return future_df
