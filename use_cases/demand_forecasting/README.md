# Demand Forecasting Module

This module provides comprehensive demand forecasting capabilities for healthcare/pharmaceutical data using three different approaches:

## Models

### 1. XGBoost Forecaster (`xgboost_forecaster.py`)
- **Type**: Tree-based regression
- **Best for**: Non-linear patterns, feature interactions
- **Strengths**: Handles complex patterns, feature importance
- **CPU-friendly**: ✅ Optimized for serverless execution

### 2. ETS Forecaster (`ets_forecaster.py`)
- **Type**: Exponential Smoothing
- **Best for**: Trend and seasonality patterns
- **Strengths**: Automatic seasonality detection, interpretable
- **CPU-friendly**: ✅ Lightweight time series model

### 3. Prophet Forecaster (`prophet_forecaster.py`)
- **Type**: Additive time series model
- **Best for**: Robust forecasting with holidays and seasonality
- **Strengths**: Handles missing data, holiday effects, trend changes
- **CPU-friendly**: ✅ Designed for production use

## Features

- **MLflow Integration**: Complete experiment tracking and model comparison
- **Automatic Feature Engineering**: Time-based features, lags, rolling statistics
- **Multiple Aggregation Levels**: Overall, pharmacy-level, product-level forecasting
- **Comprehensive Evaluation**: MAE, RMSE, MAPE metrics with statistical significance
- **Visualization**: Prediction plots, error distributions, performance comparisons

## Quick Start

```python
from use_cases.demand_forecasting.run_forecasting_experiment import main

# Run complete forecasting experiment
results = main()
```

## Individual Model Usage

```python
from use_cases.demand_forecasting.xgboost_forecaster import run_xgboost_experiment
from use_cases.demand_forecasting.ets_forecaster import run_ets_experiment
from use_cases.demand_forecasting.prophet_forecaster import run_prophet_experiment
from use_cases.demand_forecasting.data_preparation import prepare_forecasting_data

# Prepare data
train_data, test_data, full_data = prepare_forecasting_data(orders_df)

# Run individual experiments
xgb_results = run_xgboost_experiment(train_data, test_data, 'quantity')
ets_results = run_ets_experiment(train_data, test_data, 'quantity')
prophet_results = run_prophet_experiment(train_data, test_data, 'quantity')
```

## Data Requirements

The module expects order data with:
- `order_date`: Timestamp column
- `quantity`: Target variable to forecast
- `pharmacy_id`: Optional grouping column
- `product_id`: Optional grouping column

## MLflow Experiments

All experiments are automatically logged to MLflow with:
- Model parameters and hyperparameters
- Training and test metrics
- Model artifacts and feature importance
- Comparison summaries

## Serverless Compatibility

All models are optimized for Databricks serverless execution:
- No GPU dependencies
- Efficient memory usage
- Parallel processing where possible
- Robust error handling

## Installation

```bash
pip install -r requirements.txt
```

## Example Output

```
DEMAND FORECASTING MODEL COMPARISON SUMMARY
============================================================

Test Data: 200 samples
Date Range: 2023-06-01 to 2023-12-31
Target Mean: 125.50
Target Std: 45.20

Model Performance:
----------------------------------------
   XGBOOST: MAE= 12.45, RMSE= 18.32, MAPE=  9.8%, Rel=1.00
       ETS: MAE= 15.67, RMSE= 22.18, MAPE= 12.4%, Rel=1.26
    PROPHET: MAE= 14.23, RMSE= 20.45, MAPE= 11.2%, Rel=1.14

🏆 Best Model: XGBOOST
============================================================
```
