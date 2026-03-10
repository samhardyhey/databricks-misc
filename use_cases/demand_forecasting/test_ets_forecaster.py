"""
Test script for the updated ETS forecaster

Tests the ETS forecaster with sample data to ensure it works correctly
with the latest statsmodels API.
"""

import pandas as pd
import numpy as np
from loguru import logger
from ets_forecaster import ETSForecaster, run_ets_experiment


def create_test_data():
    """Create sample time series data for testing."""
    # Create date range
    dates = pd.date_range('2023-01-01', '2024-01-01', freq='D')
    
    # Create sample data with trend and seasonality
    np.random.seed(42)
    n = len(dates)
    
    # Base trend
    trend = np.linspace(100, 150, n)
    
    # Weekly seasonality
    seasonal = 20 * np.sin(2 * np.pi * np.arange(n) / 7)
    
    # Random noise
    noise = np.random.normal(0, 5, n)
    
    # Combine components
    values = trend + seasonal + noise
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'quantity': values
    }).set_index('date')
    
    return df


def test_ets_forecaster():
    """Test the ETS forecaster with different configurations."""
    logger.info("Testing ETS Forecaster...")
    
    # Create test data
    data = create_test_data()
    logger.info(f"Created test data with {len(data)} samples")
    
    # Split data
    split_idx = int(len(data) * 0.8)
    train_data = data.iloc[:split_idx]
    test_data = data.iloc[split_idx:]
    
    logger.info(f"Train: {len(train_data)} samples, Test: {len(test_data)} samples")
    
    # Test 1: Simple Exponential Smoothing
    logger.info("\n=== Test 1: Simple Exponential Smoothing ===")
    forecaster1 = ETSForecaster(trend=None, seasonal=None)
    train_metrics1 = forecaster1.train(train_data, 'quantity')
    test_metrics1 = forecaster1.evaluate(test_data)
    
    logger.info(f"Train MAE: {train_metrics1['train_mae']:.2f}")
    logger.info(f"Test MAE: {test_metrics1['mae']:.2f}")
    logger.info(f"AIC: {train_metrics1['aic']:.2f}")
    
    # Test 2: Holt's Method
    logger.info("\n=== Test 2: Holt's Method ===")
    forecaster2 = ETSForecaster(trend="add", seasonal=None)
    train_metrics2 = forecaster2.train(train_data, 'quantity')
    test_metrics2 = forecaster2.evaluate(test_data)
    
    logger.info(f"Train MAE: {train_metrics2['train_mae']:.2f}")
    logger.info(f"Test MAE: {test_metrics2['mae']:.2f}")
    logger.info(f"AIC: {train_metrics2['aic']:.2f}")
    
    # Test 3: Holt-Winters with Seasonality
    logger.info("\n=== Test 3: Holt-Winters with Seasonality ===")
    forecaster3 = ETSForecaster(trend="add", seasonal="add", seasonal_periods=7)
    train_metrics3 = forecaster3.train(train_data, 'quantity')
    test_metrics3 = forecaster3.evaluate(test_data)
    
    logger.info(f"Train MAE: {train_metrics3['train_mae']:.2f}")
    logger.info(f"Test MAE: {test_metrics3['mae']:.2f}")
    logger.info(f"AIC: {train_metrics3['aic']:.2f}")
    
    # Test model components
    logger.info("\n=== Model Components ===")
    components = forecaster3.get_model_components()
    logger.info(f"Available components: {list(components.keys())}")
    
    # Test model parameters
    params = forecaster3.get_model_parameters()
    logger.info(f"Model parameters: {list(params.keys())}")
    
    # Test forecasting
    logger.info("\n=== Forecasting Test ===")
    forecast = forecaster3.forecast(7)
    logger.info(f"7-day forecast: {forecast}")
    
    logger.info("\n✅ All tests completed successfully!")


def test_mlflow_experiment():
    """Test the MLflow experiment function."""
    logger.info("\n=== Testing MLflow Experiment ===")
    
    # Create test data
    data = create_test_data()
    split_idx = int(len(data) * 0.8)
    train_data = data.iloc[:split_idx]
    test_data = data.iloc[split_idx:]
    
    try:
        # Run experiment
        results = run_ets_experiment(
            train_data, 
            test_data, 
            'quantity',
            'test_ets_experiment'
        )
        
        logger.info("✅ MLflow experiment completed successfully!")
        logger.info(f"Test MAE: {results['test_metrics']['mae']:.2f}")
        
    except Exception as e:
        logger.error(f"❌ MLflow experiment failed: {e}")


if __name__ == "__main__":
    # Set up logging
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    # Run tests
    test_ets_forecaster()
    test_mlflow_experiment()
    
    logger.info("\n🎯 ETS Forecaster testing completed!")
