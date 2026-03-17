"""
Inventory optimisation – demand forecasting components.

This module contains the core demand forecasting building blocks
for the inventory optimisation use-case (data prep, models,
comparison, MLflow logging).
"""

import warnings
from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import mlflow
import mlflow.prophet
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from loguru import logger
from prophet import Prophet
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
)
from sklearn.model_selection import TimeSeriesSplit
from statsmodels.tsa.api import ExponentialSmoothing, Holt, SimpleExpSmoothing

warnings.filterwarnings("ignore")


# --- Data preparation ---


def prepare_forecasting_data(
    orders_df: pd.DataFrame,
    target_column: str = "quantity",
    time_column: str = "order_date",
    group_by: Optional[str] = None,
    frequency: str = "D",
    forecast_horizon: int = 30,
    test_size: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    logger.info(f"Preparing forecasting data for {target_column}")

    orders_df[time_column] = pd.to_datetime(orders_df[time_column])

    if group_by:
        agg_data = (
            orders_df.groupby([group_by, time_column])[target_column]
            .sum()
            .reset_index()
        )
        agg_data = agg_data.set_index(time_column)
        grouped_series: dict[str, pd.Series] = {}
        for group_id in agg_data[group_by].unique():
            group_data = agg_data[agg_data[group_by] == group_id][target_column]
            group_data = group_data.resample(frequency).sum().fillna(0)
            grouped_series[group_id] = group_data
        full_data = pd.concat(grouped_series, axis=1)
        full_data.columns = [f"{group_by}_{col}" for col in full_data.columns]
    else:
        agg_data = orders_df.groupby(time_column)[target_column].sum()
        full_data = agg_data.resample(frequency).sum().fillna(0)
        full_data = full_data.to_frame(target_column)

    full_data = add_time_features(full_data)
    full_data = add_lag_features(full_data, target_column, lags=[1, 7, 14, 30])
    full_data = add_rolling_features(full_data, target_column, windows=[7, 14, 30])
    full_data = full_data.dropna()

    split_idx = int(len(full_data) * (1 - test_size))
    train_data = full_data.iloc[:split_idx]
    test_data = full_data.iloc[split_idx:]

    logger.info(
        "Data prepared: {} train samples, {} test samples",
        len(train_data),
        len(test_data),
    )
    logger.info("Features: {}", list(full_data.columns))
    return train_data, test_data, full_data


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["year"] = df.index.year
    df["month"] = df.index.month
    df["day"] = df.index.day
    df["dayofweek"] = df.index.dayofweek
    df["dayofyear"] = df.index.dayofyear
    df["week"] = df.index.isocalendar().week
    df["quarter"] = df.index.quarter
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["dayofweek_sin"] = np.sin(2 * np.pi * df["dayofweek"] / 7)
    df["dayofweek_cos"] = np.cos(2 * np.pi * df["dayofweek"] / 7)
    return df


def add_lag_features(
    df: pd.DataFrame, target_column: str, lags: list[int]
) -> pd.DataFrame:
    df = df.copy()
    for lag in lags:
        df[f"{target_column}_lag_{lag}"] = df[target_column].shift(lag)
    return df


def add_rolling_features(
    df: pd.DataFrame, target_column: str, windows: list[int]
) -> pd.DataFrame:
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
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1), periods=forecast_horizon, freq=frequency
    )
    future_df = pd.DataFrame(index=future_dates)
    future_df = add_time_features(future_df)
    return future_df


# --- XGBoost forecaster ---


class XGBoostForecaster:
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
    ):
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_state,
            "n_jobs": -1,
        }
        self.model: xgb.XGBRegressor | None = None
        self.feature_columns: list[str] | None = None
        self.target_column: str | None = None

    def prepare_features(
        self, df: pd.DataFrame, target_column: str
    ) -> Tuple[pd.DataFrame, pd.Series]:
        exclude_cols = [
            target_column,
            "year",
            "month",
            "day",
            "dayofweek",
            "dayofyear",
            "week",
            "quarter",
        ]
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        X = df[feature_cols].fillna(0)
        y = df[target_column]
        return X, y

    def train(self, train_data: pd.DataFrame, target_column: str) -> Dict[str, Any]:
        logger.info("Training XGBoost model...")
        X_train, y_train = self.prepare_features(train_data, target_column)
        self.feature_columns = X_train.columns.tolist()
        self.target_column = target_column
        self.model = xgb.XGBRegressor(**self.params)
        self.model.fit(X_train, y_train)
        tscv = TimeSeriesSplit(n_splits=3)
        cv_scores = []
        for train_idx, val_idx in tscv.split(X_train):
            X_tr, X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
            temp_model = xgb.XGBRegressor(**self.params)
            temp_model.fit(X_tr, y_tr)
            y_pred = temp_model.predict(X_val)
            mae = mean_absolute_error(y_val, y_pred)
            cv_scores.append(mae)
        cv_mae = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))
        logger.info("XGBoost training completed. CV MAE: {} ± {}", cv_mae, cv_std)
        return {
            "cv_mae_mean": cv_mae,
            "cv_mae_std": cv_std,
            "n_features": len(self.feature_columns),
            "n_samples": len(X_train),
        }

    def predict(self, test_data: pd.DataFrame) -> np.ndarray:
        if self.model is None or self.target_column is None:
            raise ValueError("Model must be trained before making predictions")
        X_test, _ = self.prepare_features(test_data, self.target_column)
        return self.model.predict(X_test)

    def forecast(self, future_data: pd.DataFrame) -> np.ndarray:
        if self.model is None or self.target_column is None:
            raise ValueError("Model must be trained before making forecasts")
        X_future, _ = self.prepare_features(future_data, self.target_column)
        return self.model.predict(X_future)

    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        predictions = self.predict(test_data)
        actual = test_data[self.target_column]
        mae = mean_absolute_error(actual, predictions)
        mse = mean_squared_error(actual, predictions)
        rmse = float(np.sqrt(mse))
        mape = mean_absolute_percentage_error(actual, predictions)
        return {"mae": mae, "mse": mse, "rmse": rmse, "mape": mape}


def run_xgboost_experiment(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    target_column: str,
    experiment_name: str = "demand_forecasting_xgboost",
) -> Dict[str, Any]:
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="xgboost_demand_forecast"):
        forecaster = XGBoostForecaster()
        mlflow.log_params(forecaster.params)
        train_metrics = forecaster.train(train_data, target_column)
        mlflow.log_metrics(train_metrics)
        test_metrics = forecaster.evaluate(test_data)
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})
        mlflow.xgboost.log_model(forecaster.model, "model")
        feature_importance = dict(
            zip(forecaster.feature_columns, forecaster.model.feature_importances_)
        )
        mlflow.log_dict(feature_importance, "feature_importance.json")
        logger.info(
            "XGBoost experiment completed. Test MAE: {:.2f}",
            test_metrics["mae"],
        )
        return {
            "model": forecaster,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "feature_importance": feature_importance,
        }


# --- ETS forecaster ---


class ETSForecaster:
    def __init__(
        self,
        trend: Optional[str] = "add",
        seasonal: Optional[str] = "add",
        seasonal_periods: int = 7,
        damped_trend: bool = False,
        initialization_method: str = "estimated",
        use_boxcox: bool = False,
    ):
        self.params = {
            "trend": trend,
            "seasonal": seasonal,
            "seasonal_periods": seasonal_periods,
            "damped_trend": damped_trend,
            "initialization_method": initialization_method,
            "use_boxcox": use_boxcox,
        }
        self.model = None
        self.fitted_model = None
        self.target_column = None

    def detect_seasonality(self, data: pd.Series, max_periods: int = 30) -> int:
        if len(data) < 14:
            return 7
        best_period = 7
        best_aic = np.inf
        for period in [7, 14, 30]:
            if len(data) >= 2 * period:
                try:
                    model = ExponentialSmoothing(
                        data,
                        trend="add",
                        seasonal="add",
                        seasonal_periods=period,
                        initialization_method="estimated",
                    ).fit()
                    if model.aic < best_aic:
                        best_aic = model.aic
                        best_period = period
                except Exception as e:
                    logger.debug("Failed to fit model with period {}: {}", period, e)
                    continue
        logger.info("Detected seasonal period: {}", best_period)
        return best_period

    def train(self, train_data: pd.DataFrame, target_column: str) -> Dict[str, Any]:
        logger.info("Training ETS model...")
        self.target_column = target_column
        ts_data = train_data[target_column]
        seasonal_periods = self.detect_seasonality(ts_data)
        self.params["seasonal_periods"] = seasonal_periods
        if len(ts_data) < 2 * seasonal_periods:
            self.params["seasonal"] = None
            logger.info("Insufficient data for seasonality, using trend-only model")
        try:
            if self.params["seasonal"] is None:
                if self.params["trend"] is None:
                    self.model = SimpleExpSmoothing(
                        ts_data,
                        initialization_method=self.params["initialization_method"],
                    )
                else:
                    self.model = Holt(
                        ts_data,
                        exponential=(self.params["trend"] == "mul"),
                        damped_trend=self.params["damped_trend"],
                        initialization_method=self.params["initialization_method"],
                    )
            else:
                self.model = ExponentialSmoothing(
                    ts_data,
                    trend=self.params["trend"],
                    seasonal=self.params["seasonal"],
                    seasonal_periods=self.params["seasonal_periods"],
                    damped_trend=self.params["damped_trend"],
                    use_boxcox=self.params["use_boxcox"],
                    initialization_method=self.params["initialization_method"],
                )
            self.fitted_model = self.model.fit()
            fitted_values = self.fitted_model.fittedvalues
            train_mae = mean_absolute_error(ts_data, fitted_values)
            train_rmse = float(np.sqrt(mean_squared_error(ts_data, fitted_values)))
            aic = self.fitted_model.aic
            bic = self.fitted_model.bic
            logger.info(
                "ETS training completed. Train MAE: {:.2f}, AIC: {:.2f}",
                train_mae,
                aic,
            )
            return {
                "train_mae": train_mae,
                "train_rmse": train_rmse,
                "aic": aic,
                "bic": bic,
                "seasonal_periods": seasonal_periods,
                "n_samples": len(ts_data),
                "sse": getattr(self.fitted_model, "sse", np.nan),
            }
        except Exception as e:
            logger.warning("ETS training failed: {}. Trying simpler model...", e)
            try:
                self.model = SimpleExpSmoothing(
                    ts_data, initialization_method="estimated"
                )
                self.fitted_model = self.model.fit()
                fitted_values = self.fitted_model.fittedvalues
                train_mae = mean_absolute_error(ts_data, fitted_values)
                return {
                    "train_mae": train_mae,
                    "train_rmse": float(
                        np.sqrt(mean_squared_error(ts_data, fitted_values))
                    ),
                    "aic": self.fitted_model.aic,
                    "bic": self.fitted_model.bic,
                    "seasonal_periods": 0,
                    "n_samples": len(ts_data),
                    "sse": getattr(self.fitted_model, "sse", np.nan),
                }
            except Exception as e2:
                logger.error("All ETS models failed: {}", e2)
                raise

    def predict(self, test_data: pd.DataFrame) -> np.ndarray:
        if self.fitted_model is None:
            raise ValueError("Model must be trained before making predictions")
        last_train_date = self.fitted_model.model.endog.index[-1]
        test_start = test_data.index[0]
        steps = (test_start - last_train_date).days
        if steps <= 0:
            try:
                predictions = self.fitted_model.fittedvalues[test_data.index]
            except (KeyError, IndexError):
                forecast = self.fitted_model.forecast(steps=len(test_data))
                predictions = forecast.values
        else:
            forecast = self.fitted_model.forecast(steps=len(test_data))
            predictions = forecast.values
        return predictions

    def forecast(self, forecast_horizon: int) -> np.ndarray:
        if self.fitted_model is None:
            raise ValueError("Model must be trained before making forecasts")
        forecast = self.fitted_model.forecast(steps=forecast_horizon)
        return forecast.values

    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        predictions = self.predict(test_data)
        actual = test_data[self.target_column]
        mae = mean_absolute_error(actual, predictions)
        mse = mean_squared_error(actual, predictions)
        rmse = float(np.sqrt(mse))
        mape = mean_absolute_percentage_error(actual, predictions)
        return {"mae": mae, "mse": mse, "rmse": rmse, "mape": mape}


def run_ets_experiment(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    target_column: str,
    experiment_name: str = "demand_forecasting_ets",
) -> Dict[str, Any]:
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="ets_demand_forecast"):
        forecaster = ETSForecaster()
        mlflow.log_params(forecaster.params)
        train_metrics = forecaster.train(train_data, target_column)
        mlflow.log_metrics(train_metrics)
        test_metrics = forecaster.evaluate(test_data)
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})
        mlflow.sklearn.log_model(forecaster, "model")
        logger.info(
            "ETS experiment completed. Test MAE: {:.2f}",
            test_metrics["mae"],
        )
        return {
            "model": forecaster,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
        }


# --- Prophet forecaster ---


class ProphetForecaster:
    def __init__(
        self,
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
        daily_seasonality: bool = False,
        seasonality_mode: str = "additive",
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        holidays_prior_scale: float = 10.0,
        seasonality_prior_scale_yearly: float = 10.0,
        seasonality_prior_scale_weekly: float = 10.0,
        seasonality_prior_scale_daily: float = 10.0,
    ):
        self.params = {
            "yearly_seasonality": yearly_seasonality,
            "weekly_seasonality": weekly_seasonality,
            "daily_seasonality": daily_seasonality,
            "seasonality_mode": seasonality_mode,
            "changepoint_prior_scale": changepoint_prior_scale,
            "seasonality_prior_scale": seasonality_prior_scale,
            "holidays_prior_scale": holidays_prior_scale,
            "seasonality_prior_scale_yearly": seasonality_prior_scale_yearly,
            "seasonality_prior_scale_weekly": seasonality_prior_scale_weekly,
            "seasonality_prior_scale_daily": seasonality_prior_scale_daily,
        }
        self.model: Prophet | None = None
        self.target_column: str | None = None

    def prepare_prophet_data(
        self, data: pd.DataFrame, target_column: str
    ) -> pd.DataFrame:
        prophet_data = pd.DataFrame(
            {"ds": data.index, "y": data[target_column]}
        ).reset_index(drop=True)
        prophet_data = prophet_data.dropna()
        return prophet_data

    def add_holidays(self, model: Prophet) -> Prophet:
        holidays = pd.DataFrame(
            {
                "holiday": [
                    "New Year",
                    "Australia Day",
                    "Good Friday",
                    "Easter Monday",
                    "Anzac Day",
                    "Queen Birthday",
                    "Christmas Day",
                    "Boxing Day",
                ],
                "ds": pd.to_datetime(
                    [
                        "2023-01-01",
                        "2023-01-26",
                        "2023-04-07",
                        "2023-04-10",
                        "2023-04-25",
                        "2023-06-12",
                        "2023-12-25",
                        "2023-12-26",
                    ]
                ),
            }
        )
        holiday_list = []
        for year in range(2020, 2026):
            year_holidays = holidays.copy()
            year_holidays["ds"] = year_holidays["ds"] + pd.DateOffset(years=year - 2023)
            holiday_list.append(year_holidays)
        all_holidays = pd.concat(holiday_list, ignore_index=True)
        model.holidays = all_holidays
        model.add_country_holidays(country_name="AU")
        return model

    def train(self, train_data: pd.DataFrame, target_column: str) -> Dict[str, Any]:
        logger.info("Training Prophet model...")
        self.target_column = target_column
        prophet_data = self.prepare_prophet_data(train_data, target_column)
        self.model = Prophet(
            yearly_seasonality=self.params["yearly_seasonality"],
            weekly_seasonality=self.params["weekly_seasonality"],
            daily_seasonality=self.params["daily_seasonality"],
            seasonality_mode=self.params["seasonality_mode"],
            changepoint_prior_scale=self.params["changepoint_prior_scale"],
            seasonality_prior_scale=self.params["seasonality_prior_scale"],
            holidays_prior_scale=self.params["holidays_prior_scale"],
        )
        self.model = self.add_holidays(self.model)
        if len(prophet_data) > 365:
            self.model.add_seasonality(name="monthly", period=30.5, fourier_order=5)
        self.model.fit(prophet_data)
        future = self.model.make_future_dataframe(periods=0)
        forecast = self.model.predict(future)
        fitted_values = forecast["yhat"][: len(prophet_data)]
        actual_values = prophet_data["y"]
        train_mae = mean_absolute_error(actual_values, fitted_values)
        train_rmse = float(np.sqrt(mean_squared_error(actual_values, fitted_values)))
        logger.info("Prophet training completed. Train MAE: {:.2f}", train_mae)
        return {
            "train_mae": train_mae,
            "train_rmse": train_rmse,
            "n_changepoints": len(self.model.changepoints),
            "n_samples": len(prophet_data),
            "seasonality_mode": self.params["seasonality_mode"],
        }

    def predict(self, test_data: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model must be trained before making predictions")
        test_dates = test_data.index
        future = pd.DataFrame({"ds": test_dates})
        forecast = self.model.predict(future)
        return forecast["yhat"].values

    def forecast(
        self, forecast_horizon: int, start_date: Optional[pd.Timestamp] = None
    ) -> Tuple[np.ndarray, pd.DataFrame]:
        if self.model is None:
            raise ValueError("Model must be trained before making forecasts")
        if start_date is None:
            last_date = self.model.history["ds"].max()
        else:
            last_date = start_date
        future = self.model.make_future_dataframe(periods=forecast_horizon, freq="D")
        future = future[future["ds"] > last_date].head(forecast_horizon)
        forecast = self.model.predict(future)
        return (
            forecast["yhat"].values,
            forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]],
        )

    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        predictions = self.predict(test_data)
        actual = test_data[self.target_column]
        mae = mean_absolute_error(actual, predictions)
        mse = mean_squared_error(actual, predictions)
        rmse = float(np.sqrt(mse))
        mape = mean_absolute_percentage_error(actual, predictions)
        return {"mae": mae, "mse": mse, "rmse": rmse, "mape": mape}

    def get_components(self) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model must be trained before getting components")
        future = self.model.make_future_dataframe(periods=365)
        forecast = self.model.predict(future)
        return forecast[["ds", "trend", "yearly", "weekly", "daily"]]


def run_prophet_experiment(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    target_column: str,
    experiment_name: str = "demand_forecasting_prophet",
) -> Dict[str, Any]:
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="prophet_demand_forecast"):
        forecaster = ProphetForecaster()
        mlflow.log_params(forecaster.params)
        train_metrics = forecaster.train(train_data, target_column)
        mlflow.log_metrics(train_metrics)
        test_metrics = forecaster.evaluate(test_data)
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})
        mlflow.prophet.log_model(forecaster.model, "model")
        components = forecaster.get_components()
        mlflow.log_dict(
            {
                "trend_mean": float(components["trend"].mean()),
                "yearly_std": float(components["yearly"].std()),
                "weekly_std": float(components["weekly"].std()),
            },
            "components_stats.json",
        )
        changepoints = forecaster.model.changepoints
        if len(changepoints) > 0:
            mlflow.log_dict(
                {
                    "n_changepoints": len(changepoints),
                    "changepoint_dates": changepoints.dt.strftime("%Y-%m-%d").tolist(),
                },
                "changepoints.json",
            )
        logger.info(
            "Prophet experiment completed. Test MAE: {:.2f}",
            test_metrics["mae"],
        )
        return {
            "model": forecaster,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "components": components,
        }


# --- Comparison & utilities ---


def compare_forecasting_models(
    orders_df: pd.DataFrame,
    target_column: str = "quantity",
    time_column: str = "order_date",
    group_by: Optional[str] = None,
    experiment_name: str = "demand_forecasting_comparison",
) -> Dict[str, Any]:
    logger.info("Starting comprehensive model comparison...")
    train_data, test_data, full_data = prepare_forecasting_data(
        orders_df, target_column, time_column, group_by
    )
    mlflow.set_experiment(experiment_name)
    results: Dict[str, Any] = {}
    logger.info("Running XGBoost experiment...")
    try:
        xgb_results = run_xgboost_experiment(
            train_data, test_data, target_column, f"{experiment_name}_xgboost"
        )
        results["xgboost"] = xgb_results
        logger.info("XGBoost completed successfully")
    except Exception as e:
        logger.error("XGBoost failed: {}", e)
        results["xgboost"] = None
    logger.info("Running ETS experiment...")
    try:
        ets_results = run_ets_experiment(
            train_data, test_data, target_column, f"{experiment_name}_ets"
        )
        results["ets"] = ets_results
        logger.info("ETS completed successfully")
    except Exception as e:
        logger.error("ETS failed: {}", e)
        results["ets"] = None
    logger.info("Running Prophet experiment...")
    try:
        prophet_results = run_prophet_experiment(
            train_data, test_data, target_column, f"{experiment_name}_prophet"
        )
        results["prophet"] = prophet_results
        logger.info("Prophet completed successfully")
    except Exception as e:
        logger.error("Prophet failed: {}", e)
        results["prophet"] = None
    comparison_summary = create_comparison_summary(results, test_data, target_column)
    with mlflow.start_run(run_name="model_comparison_summary"):
        mlflow.log_dict(comparison_summary, "comparison_summary.json")
        best_model = min(
            [
                (k, v["test_metrics"]["mae"])
                for k, v in results.items()
                if v is not None
            ],
            key=lambda x: x[1],
        )
        mlflow.log_param("best_model", best_model[0])
        mlflow.log_metric("best_mae", best_model[1])
    logger.info("Model comparison completed!")
    return {
        "results": results,
        "comparison_summary": comparison_summary,
        "train_data": train_data,
        "test_data": test_data,
        "full_data": full_data,
    }


def create_comparison_summary(
    results: Dict[str, Any], test_data: pd.DataFrame, target_column: str
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "models": {},
        "rankings": {},
        "best_model": None,
        "test_data_info": {
            "n_samples": len(test_data),
            "date_range": f"{test_data.index.min()} to {test_data.index.max()}",
            "target_mean": float(test_data[target_column].mean()),
            "target_std": float(test_data[target_column].std()),
        },
    }
    model_metrics: Dict[str, float] = {}
    for model_name, model_results in results.items():
        if model_results is not None:
            test_metrics = model_results["test_metrics"]
            train_metrics = model_results["train_metrics"]
            summary["models"][model_name] = {
                "test_metrics": test_metrics,
                "train_metrics": train_metrics,
                "status": "success",
            }
            model_metrics[model_name] = test_metrics["mae"]
        else:
            summary["models"][model_name] = {"status": "failed"}
    if model_metrics:
        sorted_models = sorted(model_metrics.items(), key=lambda x: x[1])
        summary["rankings"]["by_mae"] = [
            {"model": model, "mae": mae} for model, mae in sorted_models
        ]
        summary["best_model"] = sorted_models[0][0]
        best_mae = sorted_models[0][1]
        for model, mae in sorted_models:
            summary["models"][model]["relative_performance"] = mae / best_mae
    return summary


def create_comparison_plots(
    results: Dict[str, Any],
    test_data: pd.DataFrame,
    target_column: str,
    save_path: Optional[str] = None,
) -> Dict[str, plt.Figure]:
    figures: Dict[str, plt.Figure] = {}
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(
        test_data.index, test_data[target_column], "k-", label="Actual", linewidth=2
    )
    colors = ["red", "blue", "green"]
    for i, (model_name, model_results) in enumerate(results.items()):
        if model_results is not None:
            predictions = model_results["model"].predict(test_data)
            ax.plot(
                test_data.index,
                predictions,
                color=colors[i % len(colors)],
                label=f'{model_name.title()} (MAE: {model_results["test_metrics"]["mae"]:.2f})',
                alpha=0.7,
            )
    ax.set_title("Model Predictions vs Actual")
    ax.set_xlabel("Date")
    ax.set_ylabel(target_column.title())
    ax.legend()
    ax.grid(True, alpha=0.3)
    figures["predictions_vs_actual"] = fig

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for i, (model_name, model_results) in enumerate(results.items()):
        if model_results is not None:
            predictions = model_results["model"].predict(test_data)
            errors = test_data[target_column] - predictions
            axes[i].hist(errors, bins=20, alpha=0.7, edgecolor="black")
            axes[i].set_title(f"{model_name.title()} Error Distribution")
            axes[i].set_xlabel("Prediction Error")
            axes[i].set_ylabel("Frequency")
            axes[i].grid(True, alpha=0.3)
    figures["error_distributions"] = fig

    fig, ax = plt.subplots(figsize=(10, 6))
    model_names: list[str] = []
    mae_scores: list[float] = []
    rmse_scores: list[float] = []
    for model_name, model_results in results.items():
        if model_results is not None:
            model_names.append(model_name.title())
            mae_scores.append(model_results["test_metrics"]["mae"])
            rmse_scores.append(model_results["test_metrics"]["rmse"])
    x = np.arange(len(model_names))
    width = 0.35
    ax.bar(x - width / 2, mae_scores, width, label="MAE", alpha=0.8)
    ax.bar(x + width / 2, rmse_scores, width, label="RMSE", alpha=0.8)
    ax.set_xlabel("Models")
    ax.set_ylabel("Error Score")
    ax.set_title("Model Performance Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(model_names)
    ax.legend()
    ax.grid(True, alpha=0.3)
    figures["metrics_comparison"] = fig
    if save_path:
        for plot_name, fig in figures.items():
            fig.savefig(f"{save_path}/{plot_name}.png", dpi=300, bbox_inches="tight")
    return figures


def run_full_comparison(
    orders_df: pd.DataFrame,
    target_column: str = "quantity",
    time_column: str = "order_date",
    group_by: Optional[str] = None,
    experiment_name: str = "demand_forecasting_comparison",
    save_plots: bool = True,
) -> Dict[str, Any]:
    logger.info("Starting full demand forecasting model comparison...")
    comparison_results = compare_forecasting_models(
        orders_df, target_column, time_column, group_by, experiment_name
    )
    if save_plots:
        logger.info("Creating comparison plots...")
        plots = create_comparison_plots(
            comparison_results["results"],
            comparison_results["test_data"],
            target_column,
        )
        comparison_results["plots"] = plots
    print_comparison_summary(comparison_results["comparison_summary"])
    logger.info("Full comparison completed!")
    return comparison_results


def print_comparison_summary(summary: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("DEMAND FORECASTING MODEL COMPARISON SUMMARY")
    print("=" * 60)
    print(f"\nTest Data: {summary['test_data_info']['n_samples']} samples")
    print(f"Date Range: {summary['test_data_info']['date_range']}")
    print(f"Target Mean: {summary['test_data_info']['target_mean']:.2f}")
    print(f"Target Std: {summary['test_data_info']['target_std']:.2f}")
    print("\nModel Performance:")
    print("-" * 40)
    for model_name, model_info in summary["models"].items():
        if model_info["status"] == "success":
            mae = model_info["test_metrics"]["mae"]
            rmse = model_info["test_metrics"]["rmse"]
            mape = model_info["test_metrics"]["mape"]
            rel_perf = model_info.get("relative_performance", 1.0)
            print(
                f"{model_name.upper():>10}: MAE={mae:6.2f}, RMSE={rmse:6.2f}, MAPE={mape:5.1f}%, Rel={rel_perf:.2f}"
            )
        else:
            print(f"{model_name.upper():>10}: FAILED")
    if summary["best_model"]:
        print(f"\nBest Model: {summary['best_model'].upper()}")
    print("=" * 60)


__all__ = [
    "prepare_forecasting_data",
    "add_time_features",
    "add_lag_features",
    "add_rolling_features",
    "create_forecast_dataframe",
    "XGBoostForecaster",
    "ETSForecaster",
    "ProphetForecaster",
    "run_xgboost_experiment",
    "run_ets_experiment",
    "run_prophet_experiment",
    "compare_forecasting_models",
    "create_comparison_plots",
    "run_full_comparison",
]
