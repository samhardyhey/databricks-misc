"""
ETS (Exponential Smoothing) Demand Forecasting Model

Implements ETS-based demand forecasting with MLflow integration.
Uses statsmodels for robust time series forecasting.
"""

import warnings
from typing import Any, Dict, Optional

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
)
from statsmodels.tsa.api import ExponentialSmoothing, Holt, SimpleExpSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose

warnings.filterwarnings("ignore")


class ETSForecaster:
    """ETS (Exponential Smoothing) demand forecasting model."""

    def __init__(
        self,
        trend: Optional[str] = "add",
        seasonal: Optional[str] = "add",
        seasonal_periods: int = 7,
        damped_trend: bool = False,
        initialization_method: str = "estimated",
        use_boxcox: bool = False,
    ):
        """Initialize ETS forecaster."""
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
        """Detect seasonal period in the data."""
        if len(data) < 14:  # Need at least 2 weeks of data
            return 7  # Default to weekly seasonality

        # Try different seasonal periods
        best_period = 7
        best_aic = np.inf

        for period in [7, 14, 30]:  # Daily, bi-weekly, monthly
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
                    logger.debug(f"Failed to fit model with period {period}: {e}")
                    continue

        logger.info(f"Detected seasonal period: {best_period}")
        return best_period

    def train(self, train_data: pd.DataFrame, target_column: str) -> Dict[str, Any]:
        """Train the ETS model."""
        logger.info("Training ETS model...")

        self.target_column = target_column
        ts_data = train_data[target_column]

        # Detect seasonality
        seasonal_periods = self.detect_seasonality(ts_data)
        self.params["seasonal_periods"] = seasonal_periods

        # Adjust seasonal parameter based on data length
        if len(ts_data) < 2 * seasonal_periods:
            self.params["seasonal"] = None
            logger.info("Insufficient data for seasonality, using trend-only model")

        try:
            # Try different model configurations based on data characteristics
            if self.params["seasonal"] is None:
                # No seasonality - use Holt's method or simple exponential smoothing
                if self.params["trend"] is None:
                    # Simple Exponential Smoothing
                    self.model = SimpleExpSmoothing(
                        ts_data,
                        initialization_method=self.params["initialization_method"],
                    )
                else:
                    # Holt's method
                    self.model = Holt(
                        ts_data,
                        exponential=(self.params["trend"] == "mul"),
                        damped_trend=self.params["damped_trend"],
                        initialization_method=self.params["initialization_method"],
                    )
            else:
                # Full Holt-Winters with seasonality
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

            # Calculate training metrics
            fitted_values = self.fitted_model.fittedvalues
            ts_data - fitted_values

            train_mae = mean_absolute_error(ts_data, fitted_values)
            train_rmse = np.sqrt(mean_squared_error(ts_data, fitted_values))

            # AIC and BIC
            aic = self.fitted_model.aic
            bic = self.fitted_model.bic

            logger.info(
                f"ETS training completed. Train MAE: {train_mae:.2f}, AIC: {aic:.2f}"
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
            logger.warning(f"ETS training failed: {e}. Trying simpler model...")

            # Fallback to simple exponential smoothing
            try:
                self.model = SimpleExpSmoothing(
                    ts_data, initialization_method="estimated"
                )
                self.fitted_model = self.model.fit()

                fitted_values = self.fitted_model.fittedvalues
                train_mae = mean_absolute_error(ts_data, fitted_values)

                return {
                    "train_mae": train_mae,
                    "train_rmse": np.sqrt(mean_squared_error(ts_data, fitted_values)),
                    "aic": self.fitted_model.aic,
                    "bic": self.fitted_model.bic,
                    "seasonal_periods": 0,
                    "n_samples": len(ts_data),
                    "sse": getattr(self.fitted_model, "sse", np.nan),
                }
            except Exception as e2:
                logger.error(f"All ETS models failed: {e2}")
                raise

    def predict(self, test_data: pd.DataFrame) -> np.ndarray:
        """Make predictions on test data."""
        if self.fitted_model is None:
            raise ValueError("Model must be trained before making predictions")

        # Get the last date from training data
        last_train_date = self.fitted_model.model.endog.index[-1]

        # Calculate the number of steps to forecast
        test_start = test_data.index[0]
        steps = (test_start - last_train_date).days

        if steps <= 0:
            # If test data overlaps with training, use fitted values
            try:
                predictions = self.fitted_model.fittedvalues[test_data.index]
            except (KeyError, IndexError):
                # If index doesn't match, use forecast instead
                forecast = self.fitted_model.forecast(steps=len(test_data))
                predictions = forecast.values
        else:
            # Forecast from the end of training data
            forecast = self.fitted_model.forecast(steps=len(test_data))
            predictions = forecast.values

        return predictions

    def forecast(self, forecast_horizon: int) -> np.ndarray:
        """Make forecasts for future periods."""
        if self.fitted_model is None:
            raise ValueError("Model must be trained before making forecasts")

        forecast = self.fitted_model.forecast(steps=forecast_horizon)
        return forecast.values

    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        """Evaluate model performance on test data."""
        predictions = self.predict(test_data)
        actual = test_data[self.target_column]

        mae = mean_absolute_error(actual, predictions)
        mse = mean_squared_error(actual, predictions)
        rmse = np.sqrt(mse)
        mape = mean_absolute_percentage_error(actual, predictions)

        return {"mae": mae, "mse": mse, "rmse": rmse, "mape": mape}

    def get_model_components(self) -> Dict[str, pd.Series]:
        """Get the internal components of the fitted ETS model."""
        if self.fitted_model is None:
            return {}

        components = {}

        # Get level component
        if hasattr(self.fitted_model, "level") and self.fitted_model.level is not None:
            components["level"] = self.fitted_model.level

        # Get trend component
        if hasattr(self.fitted_model, "trend") and self.fitted_model.trend is not None:
            components["trend"] = self.fitted_model.trend

        # Get seasonal component
        if (
            hasattr(self.fitted_model, "season")
            and self.fitted_model.season is not None
        ):
            components["seasonal"] = self.fitted_model.season

        # Get fitted values
        if hasattr(self.fitted_model, "fittedvalues"):
            components["fitted"] = self.fitted_model.fittedvalues

        return components

    def get_model_parameters(self) -> Dict[str, float]:
        """Get the fitted parameters of the ETS model."""
        if self.fitted_model is None:
            return {}

        params = {}

        # Get smoothing parameters
        if hasattr(self.fitted_model, "params"):
            fitted_params = self.fitted_model.params
            for param_name in [
                "smoothing_level",
                "smoothing_trend",
                "smoothing_seasonal",
                "damping_trend",
                "initial_level",
                "initial_trend",
            ]:
                if param_name in fitted_params:
                    params[param_name] = float(fitted_params[param_name])

        # Get model fit statistics
        if hasattr(self.fitted_model, "sse"):
            params["sse"] = float(self.fitted_model.sse)
        if hasattr(self.fitted_model, "aic"):
            params["aic"] = float(self.fitted_model.aic)
        if hasattr(self.fitted_model, "bic"):
            params["bic"] = float(self.fitted_model.bic)

        return params

    def get_decomposition(self, data: pd.Series) -> Dict[str, pd.Series]:
        """Get seasonal decomposition of the time series."""
        if len(data) < 14:
            return {}

        try:
            decomposition = seasonal_decompose(
                data, model="additive", period=min(7, len(data) // 2)
            )

            return {
                "trend": decomposition.trend,
                "seasonal": decomposition.seasonal,
                "residual": decomposition.resid,
            }
        except Exception as e:
            logger.debug(f"Seasonal decomposition failed: {e}")
            return {}


def run_ets_experiment(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    target_column: str,
    experiment_name: str = "demand_forecasting_ets",
) -> Dict[str, Any]:
    """Run ETS forecasting experiment with MLflow tracking."""

    # Set MLflow experiment
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="ets_demand_forecast"):
        # Initialize model
        forecaster = ETSForecaster()

        # Log parameters
        mlflow.log_params(forecaster.params)

        # Train model
        train_metrics = forecaster.train(train_data, target_column)
        mlflow.log_metrics(train_metrics)

        # Log fitted parameters
        fitted_params = forecaster.get_model_parameters()
        if fitted_params:
            mlflow.log_params({f"fitted_{k}": v for k, v in fitted_params.items()})

        # Evaluate on test data
        test_metrics = forecaster.evaluate(test_data)
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})

        # Log model (using sklearn wrapper for MLflow compatibility)
        from sklearn.base import BaseEstimator, RegressorMixin

        class ETSWrapper(BaseEstimator, RegressorMixin):
            def __init__(self, ets_model):
                self.ets_model = ets_model

            def predict(self, X):
                return self.ets_model.forecast(len(X))

        mlflow.sklearn.log_model(ETSWrapper(forecaster.fitted_model), "model")

        # Get model components for analysis
        components = forecaster.get_model_components()
        if components:
            component_stats = {}
            for name, series in components.items():
                if series is not None and len(series) > 0:
                    component_stats[f"{name}_mean"] = float(series.mean())
                    component_stats[f"{name}_std"] = float(series.std())

            if component_stats:
                mlflow.log_dict(component_stats, "component_stats.json")

        # Get decomposition for analysis
        decomposition = forecaster.get_decomposition(train_data[target_column])
        if decomposition:
            mlflow.log_dict(
                {
                    "trend_mean": float(decomposition["trend"].mean()),
                    "seasonal_std": float(decomposition["seasonal"].std()),
                    "residual_std": float(decomposition["residual"].std()),
                },
                "decomposition_stats.json",
            )

        logger.info(f"ETS experiment completed. Test MAE: {test_metrics['mae']:.2f}")

        return {
            "model": forecaster,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "decomposition": decomposition,
        }


if __name__ == "__main__":
    # Example usage
    logger.info("ETS Demand Forecasting Model")
    logger.info("This script should be imported and used with prepared data")
