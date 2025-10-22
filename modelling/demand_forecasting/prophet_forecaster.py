"""
Prophet Demand Forecasting Model

Implements Prophet-based demand forecasting with MLflow integration.
Handles seasonality, holidays, and trend changes automatically.
"""

import warnings
from typing import Any, Dict, Optional, Tuple

import mlflow
import mlflow.prophet
import numpy as np
import pandas as pd
from loguru import logger
from prophet import Prophet
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
)

warnings.filterwarnings("ignore")


class ProphetForecaster:
    """Prophet demand forecasting model."""

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
        """Initialize Prophet forecaster."""
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
        self.model = None
        self.target_column = None

    def prepare_prophet_data(
        self, data: pd.DataFrame, target_column: str
    ) -> pd.DataFrame:
        """Prepare data in Prophet format (ds, y)."""
        prophet_data = pd.DataFrame(
            {"ds": data.index, "y": data[target_column]}
        ).reset_index(drop=True)

        # Remove any NaN values
        prophet_data = prophet_data.dropna()

        return prophet_data

    def add_holidays(self, model: Prophet) -> Prophet:
        """Add common holidays that might affect demand."""
        # Australian holidays
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

        # Add holidays for multiple years
        holiday_list = []
        for year in range(2020, 2026):
            year_holidays = holidays.copy()
            year_holidays["ds"] = year_holidays["ds"] + pd.DateOffset(years=year - 2023)
            holiday_list.append(year_holidays)

        all_holidays = pd.concat(holiday_list, ignore_index=True)
        model.add_country_holidays(country_name="AU")

        return model

    def train(self, train_data: pd.DataFrame, target_column: str) -> Dict[str, Any]:
        """Train the Prophet model."""
        logger.info("Training Prophet model...")

        self.target_column = target_column
        prophet_data = self.prepare_prophet_data(train_data, target_column)

        # Initialize Prophet model
        self.model = Prophet(
            yearly_seasonality=self.params["yearly_seasonality"],
            weekly_seasonality=self.params["weekly_seasonality"],
            daily_seasonality=self.params["daily_seasonality"],
            seasonality_mode=self.params["seasonality_mode"],
            changepoint_prior_scale=self.params["changepoint_prior_scale"],
            seasonality_prior_scale=self.params["seasonality_prior_scale"],
            holidays_prior_scale=self.params["holidays_prior_scale"],
        )

        # Add holidays
        self.model = self.add_holidays(self.model)

        # Add custom seasonalities if needed
        if len(prophet_data) > 365:  # If we have more than a year of data
            self.model.add_seasonality(name="monthly", period=30.5, fourier_order=5)

        try:
            # Fit the model
            self.model.fit(prophet_data)

            # Get fitted values
            future = self.model.make_future_dataframe(periods=0)
            forecast = self.model.predict(future)

            # Calculate training metrics
            fitted_values = forecast["yhat"][: len(prophet_data)]
            actual_values = prophet_data["y"]

            train_mae = mean_absolute_error(actual_values, fitted_values)
            train_rmse = np.sqrt(mean_squared_error(actual_values, fitted_values))

            # Get model parameters
            self.model.params

            logger.info(f"Prophet training completed. Train MAE: {train_mae:.2f}")

            return {
                "train_mae": train_mae,
                "train_rmse": train_rmse,
                "n_changepoints": len(self.model.changepoints),
                "n_samples": len(prophet_data),
                "seasonality_mode": self.params["seasonality_mode"],
            }

        except Exception as e:
            logger.error(f"Prophet training failed: {e}")
            raise

    def predict(self, test_data: pd.DataFrame) -> np.ndarray:
        """Make predictions on test data."""
        if self.model is None:
            raise ValueError("Model must be trained before making predictions")

        # Create future dataframe for test period
        test_dates = test_data.index
        future = pd.DataFrame({"ds": test_dates})

        # Make predictions
        forecast = self.model.predict(future)
        predictions = forecast["yhat"].values

        return predictions

    def forecast(
        self, forecast_horizon: int, start_date: Optional[pd.Timestamp] = None
    ) -> Tuple[np.ndarray, pd.DataFrame]:
        """Make forecasts for future periods."""
        if self.model is None:
            raise ValueError("Model must be trained before making forecasts")

        # Create future dataframe
        if start_date is None:
            # Start from the last date in training data
            last_date = self.model.history["ds"].max()
        else:
            last_date = start_date

        future = self.model.make_future_dataframe(periods=forecast_horizon, freq="D")
        future = future[future["ds"] > last_date].head(forecast_horizon)

        # Make forecast
        forecast = self.model.predict(future)

        return (
            forecast["yhat"].values,
            forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]],
        )

    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        """Evaluate model performance on test data."""
        predictions = self.predict(test_data)
        actual = test_data[self.target_column]

        mae = mean_absolute_error(actual, predictions)
        mse = mean_squared_error(actual, predictions)
        rmse = np.sqrt(mse)
        mape = mean_absolute_percentage_error(actual, predictions)

        return {"mae": mae, "mse": mse, "rmse": rmse, "mape": mape}

    def get_components(self) -> pd.DataFrame:
        """Get forecast components (trend, seasonality, etc.)."""
        if self.model is None:
            raise ValueError("Model must be trained before getting components")

        # Create future dataframe for one year
        future = self.model.make_future_dataframe(periods=365)
        forecast = self.model.predict(future)

        return forecast[["ds", "trend", "yearly", "weekly", "daily"]]


def run_prophet_experiment(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    target_column: str,
    experiment_name: str = "demand_forecasting_prophet",
) -> Dict[str, Any]:
    """Run Prophet forecasting experiment with MLflow tracking."""

    # Set MLflow experiment
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="prophet_demand_forecast"):
        # Initialize model
        forecaster = ProphetForecaster()

        # Log parameters
        mlflow.log_params(forecaster.params)

        # Train model
        train_metrics = forecaster.train(train_data, target_column)
        mlflow.log_metrics(train_metrics)

        # Evaluate on test data
        test_metrics = forecaster.evaluate(test_data)
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})

        # Log model
        mlflow.prophet.log_model(forecaster.model, "model")

        # Get and log components
        components = forecaster.get_components()
        mlflow.log_dict(
            {
                "trend_mean": float(components["trend"].mean()),
                "yearly_std": float(components["yearly"].std()),
                "weekly_std": float(components["weekly"].std()),
            },
            "components_stats.json",
        )

        # Log changepoints
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
            f"Prophet experiment completed. Test MAE: {test_metrics['mae']:.2f}"
        )

        return {
            "model": forecaster,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "components": components,
        }


if __name__ == "__main__":
    # Example usage
    logger.info("Prophet Demand Forecasting Model")
    logger.info("This script should be imported and used with prepared data")
