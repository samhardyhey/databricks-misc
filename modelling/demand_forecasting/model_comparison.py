"""
Model Comparison and Evaluation

Compares XGBoost, ETS, and Prophet models for demand forecasting.
Provides comprehensive evaluation metrics and visualizations.
"""

import warnings
from typing import Any, Dict

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from loguru import logger

warnings.filterwarnings("ignore")

from data_preparation import prepare_forecasting_data
from ets_forecaster import run_ets_experiment
from prophet_forecaster import run_prophet_experiment
from xgboost_forecaster import run_xgboost_experiment


def compare_forecasting_models(
    orders_df: pd.DataFrame,
    target_column: str = "quantity",
    time_column: str = "order_date",
    group_by: Optional[str] = None,
    experiment_name: str = "demand_forecasting_comparison",
) -> Dict[str, Any]:
    """
    Compare all three forecasting models on the same dataset.

    Args:
        orders_df: DataFrame with order data
        target_column: Column to forecast
        time_column: Time column name
        group_by: Column to group by (optional)
        experiment_name: MLflow experiment name

    Returns:
        Dictionary with comparison results
    """
    logger.info("Starting comprehensive model comparison...")

    # Prepare data
    train_data, test_data, full_data = prepare_forecasting_data(
        orders_df, target_column, time_column, group_by
    )

    # Set up MLflow experiment
    mlflow.set_experiment(experiment_name)

    results = {}

    # Run XGBoost experiment
    logger.info("Running XGBoost experiment...")
    try:
        xgb_results = run_xgboost_experiment(
            train_data, test_data, target_column, f"{experiment_name}_xgboost"
        )
        results["xgboost"] = xgb_results
        logger.info("✅ XGBoost completed successfully")
    except Exception as e:
        logger.error(f"❌ XGBoost failed: {e}")
        results["xgboost"] = None

    # Run ETS experiment
    logger.info("Running ETS experiment...")
    try:
        ets_results = run_ets_experiment(
            train_data, test_data, target_column, f"{experiment_name}_ets"
        )
        results["ets"] = ets_results
        logger.info("✅ ETS completed successfully")
    except Exception as e:
        logger.error(f"❌ ETS failed: {e}")
        results["ets"] = None

    # Run Prophet experiment
    logger.info("Running Prophet experiment...")
    try:
        prophet_results = run_prophet_experiment(
            train_data, test_data, target_column, f"{experiment_name}_prophet"
        )
        results["prophet"] = prophet_results
        logger.info("✅ Prophet completed successfully")
    except Exception as e:
        logger.error(f"❌ Prophet failed: {e}")
        results["prophet"] = None

    # Create comparison summary
    comparison_summary = create_comparison_summary(results, test_data, target_column)

    # Log comparison results
    with mlflow.start_run(run_name="model_comparison_summary"):
        mlflow.log_dict(comparison_summary, "comparison_summary.json")

        # Log best model
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
    """Create a summary comparison of all models."""

    summary = {
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

    # Collect metrics for each model
    model_metrics = {}

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

    # Create rankings
    if model_metrics:
        sorted_models = sorted(model_metrics.items(), key=lambda x: x[1])

        summary["rankings"]["by_mae"] = [
            {"model": model, "mae": mae} for model, mae in sorted_models
        ]

        summary["best_model"] = sorted_models[0][0]

        # Calculate relative performance
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
    """Create comparison plots for all models."""

    figures = {}

    # 1. Predictions vs Actual
    fig, ax = plt.subplots(figsize=(12, 8))

    # Plot actual values
    ax.plot(
        test_data.index, test_data[target_column], "k-", label="Actual", linewidth=2
    )

    # Plot predictions for each model
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

    # 2. Error distribution
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

    # 3. Metrics comparison
    fig, ax = plt.subplots(figsize=(10, 6))

    model_names = []
    mae_scores = []
    rmse_scores = []

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

    # Save plots if path provided
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
    """Run complete model comparison with plots and analysis."""

    logger.info("🚀 Starting full demand forecasting model comparison...")

    # Run comparison
    comparison_results = compare_forecasting_models(
        orders_df, target_column, time_column, group_by, experiment_name
    )

    # Create plots
    if save_plots:
        logger.info("Creating comparison plots...")
        plots = create_comparison_plots(
            comparison_results["results"],
            comparison_results["test_data"],
            target_column,
        )
        comparison_results["plots"] = plots

    # Print summary
    print_comparison_summary(comparison_results["comparison_summary"])

    logger.info("✅ Full comparison completed!")
    return comparison_results


def print_comparison_summary(summary: Dict[str, Any]):
    """Print a formatted comparison summary."""

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
        print(f"\n🏆 Best Model: {summary['best_model'].upper()}")

    print("=" * 60)


if __name__ == "__main__":
    # Example usage
    logger.info("Model Comparison Module")
    logger.info("This script should be imported and used with prepared data")
