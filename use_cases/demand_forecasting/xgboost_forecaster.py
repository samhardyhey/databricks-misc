"""
XGBoost Demand Forecasting Model

Implements XGBoost-based demand forecasting with MLflow integration.
Suitable for serverless CPU execution.
"""

from typing import Any, Dict, Tuple

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from loguru import logger
from sklearn.metrics import (mean_absolute_error,
                             mean_absolute_percentage_error,
                             mean_squared_error)
from sklearn.model_selection import TimeSeriesSplit


class XGBoostForecaster:
    """XGBoost-based demand forecasting model."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
    ):
        """Initialize XGBoost forecaster."""
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_state,
            "n_jobs": -1,  # Use all available cores
        }
        self.model = None
        self.feature_columns = None
        self.target_column = None

    def prepare_features(
        self, df: pd.DataFrame, target_column: str
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features for XGBoost training."""
        # Select feature columns (exclude target and time-based columns that might cause issues)
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

        # Handle missing values
        X = df[feature_cols].fillna(0)
        y = df[target_column]

        return X, y

    def train(self, train_data: pd.DataFrame, target_column: str) -> Dict[str, Any]:
        """Train the XGBoost model."""
        logger.info("Training XGBoost model...")

        # Prepare features
        X_train, y_train = self.prepare_features(train_data, target_column)
        self.feature_columns = X_train.columns.tolist()
        self.target_column = target_column

        # Initialize and train model
        self.model = xgb.XGBRegressor(**self.params)
        self.model.fit(X_train, y_train)

        # Cross-validation for evaluation
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

        cv_mae = np.mean(cv_scores)
        cv_std = np.std(cv_scores)

        logger.info(f"XGBoost training completed. CV MAE: {cv_mae:.2f} ± {cv_std:.2f}")

        return {
            "cv_mae_mean": cv_mae,
            "cv_mae_std": cv_std,
            "n_features": len(self.feature_columns),
            "n_samples": len(X_train),
        }

    def predict(self, test_data: pd.DataFrame) -> np.ndarray:
        """Make predictions on test data."""
        if self.model is None:
            raise ValueError("Model must be trained before making predictions")

        X_test, _ = self.prepare_features(test_data, self.target_column)
        predictions = self.model.predict(X_test)

        return predictions

    def forecast(self, future_data: pd.DataFrame) -> np.ndarray:
        """Make forecasts for future periods."""
        if self.model is None:
            raise ValueError("Model must be trained before making forecasts")

        X_future, _ = self.prepare_features(future_data, self.target_column)
        forecasts = self.model.predict(X_future)

        return forecasts

    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        """Evaluate model performance on test data."""
        predictions = self.predict(test_data)
        actual = test_data[self.target_column]

        mae = mean_absolute_error(actual, predictions)
        mse = mean_squared_error(actual, predictions)
        rmse = np.sqrt(mse)
        mape = mean_absolute_percentage_error(actual, predictions)

        return {"mae": mae, "mse": mse, "rmse": rmse, "mape": mape}


def run_xgboost_experiment(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    target_column: str,
    experiment_name: str = "demand_forecasting_xgboost",
) -> Dict[str, Any]:
    """Run XGBoost forecasting experiment with MLflow tracking."""

    # Set MLflow experiment
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="xgboost_demand_forecast"):
        # Initialize model
        forecaster = XGBoostForecaster()

        # Log parameters
        mlflow.log_params(forecaster.params)

        # Train model
        train_metrics = forecaster.train(train_data, target_column)
        mlflow.log_metrics(train_metrics)

        # Evaluate on test data
        test_metrics = forecaster.evaluate(test_data)
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})

        # Log model
        mlflow.xgboost.log_model(forecaster.model, "model")

        # Log feature importance
        feature_importance = dict(
            zip(forecaster.feature_columns, forecaster.model.feature_importances_)
        )
        mlflow.log_dict(feature_importance, "feature_importance.json")

        logger.info(
            f"XGBoost experiment completed. Test MAE: {test_metrics['mae']:.2f}"
        )

        return {
            "model": forecaster,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "feature_importance": feature_importance,
        }


if __name__ == "__main__":
    # Example usage
    logger.info("XGBoost Demand Forecasting Model")
    logger.info("This script should be imported and used with prepared data")
