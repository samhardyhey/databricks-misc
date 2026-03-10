"""
Main script to run demand forecasting experiments

This script demonstrates how to use the forecasting models with real data.
It loads data from Unity Catalog and runs all three models for comparison.
"""

import numpy as np
import pandas as pd
from data_preparation import prepare_forecasting_data
from loguru import logger
from model_comparison import run_full_comparison
from pyspark.sql import SparkSession


def load_healthcare_data(spark: SparkSession) -> pd.DataFrame:
    """Load healthcare order data from Unity Catalog."""
    logger.info("Loading healthcare data from Unity Catalog...")

    try:
        # Load orders data
        orders_df = spark.table("workspace.default.healthcare_orders").toPandas()

        # Convert order_date to datetime
        orders_df["order_date"] = pd.to_datetime(orders_df["order_date"])

        # Filter out any invalid dates
        orders_df = orders_df[orders_df["order_date"].notna()]

        # Sort by date
        orders_df = orders_df.sort_values("order_date")

        logger.info(
            f"Loaded {len(orders_df)} orders from {orders_df['order_date'].min()} to {orders_df['order_date'].max()}"
        )

        return orders_df

    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise


def create_sample_data() -> pd.DataFrame:
    """Create sample data for testing if Unity Catalog data is not available."""
    logger.info("Creating sample healthcare order data...")

    # Generate sample data
    np.random.seed(42)
    n_orders = 1000

    # Create date range
    start_date = pd.Timestamp("2023-01-01")
    end_date = pd.Timestamp("2024-01-01")
    dates = pd.date_range(start_date, end_date, freq="D")

    # Sample dates
    order_dates = np.random.choice(dates, n_orders)

    # Create sample orders with some seasonality and trend
    base_demand = 100
    trend = np.linspace(0, 50, n_orders)
    seasonal = 20 * np.sin(2 * np.pi * np.arange(n_orders) / 365)  # Yearly seasonality
    weekly = 10 * np.sin(2 * np.pi * np.arange(n_orders) / 7)  # Weekly seasonality
    noise = np.random.normal(0, 15, n_orders)

    quantities = base_demand + trend + seasonal + weekly + noise
    quantities = np.maximum(quantities, 1)  # Ensure positive quantities

    # Create DataFrame
    orders_df = pd.DataFrame(
        {
            "order_id": range(n_orders),
            "pharmacy_id": np.random.randint(1, 51, n_orders),
            "product_id": np.random.randint(1, 101, n_orders),
            "order_date": order_dates,
            "quantity": quantities.astype(int),
            "unit_price": np.random.uniform(10, 100, n_orders),
            "total_amount": quantities * np.random.uniform(10, 100, n_orders),
        }
    )

    logger.info(f"Created {len(orders_df)} sample orders")
    return orders_df


def run_pharmacy_level_forecasting(orders_df: pd.DataFrame) -> dict:
    """Run forecasting at pharmacy level (aggregated demand)."""
    logger.info("Running pharmacy-level demand forecasting...")

    # Aggregate by pharmacy and date
    pharmacy_demand = (
        orders_df.groupby(["pharmacy_id", "order_date"])["quantity"].sum().reset_index()
    )

    # Run comparison for each pharmacy (or sample a few)
    pharmacy_ids = pharmacy_demand["pharmacy_id"].unique()[
        :5
    ]  # Sample first 5 pharmacies

    results = {}

    for pharmacy_id in pharmacy_ids:
        logger.info(f"Forecasting for pharmacy {pharmacy_id}...")

        # Filter data for this pharmacy
        pharmacy_data = pharmacy_demand[
            pharmacy_demand["pharmacy_id"] == pharmacy_id
        ].copy()
        pharmacy_data = pharmacy_data.set_index("order_date")

        # Prepare data
        train_data, test_data, full_data = prepare_forecasting_data(
            pharmacy_data,
            target_column="quantity",
            time_column="order_date",
            group_by=None,
        )

        # Run comparison
        try:
            comparison_results = run_full_comparison(
                pharmacy_data,
                target_column="quantity",
                time_column="order_date",
                group_by=None,
                experiment_name=f"pharmacy_{pharmacy_id}_forecasting",
                save_plots=False,
            )

            results[f"pharmacy_{pharmacy_id}"] = comparison_results

        except Exception as e:
            logger.error(f"Failed to forecast for pharmacy {pharmacy_id}: {e}")
            results[f"pharmacy_{pharmacy_id}"] = None

    return results


def run_product_level_forecasting(orders_df: pd.DataFrame) -> dict:
    """Run forecasting at product level (individual product demand)."""
    logger.info("Running product-level demand forecasting...")

    # Aggregate by product and date
    product_demand = (
        orders_df.groupby(["product_id", "order_date"])["quantity"].sum().reset_index()
    )

    # Run comparison for top products by volume
    product_volumes = (
        product_demand.groupby("product_id")["quantity"]
        .sum()
        .sort_values(ascending=False)
    )
    top_products = product_volumes.head(3).index  # Top 3 products

    results = {}

    for product_id in top_products:
        logger.info(f"Forecasting for product {product_id}...")

        # Filter data for this product
        product_data = product_demand[product_demand["product_id"] == product_id].copy()
        product_data = product_data.set_index("order_date")

        # Prepare data
        train_data, test_data, full_data = prepare_forecasting_data(
            product_data,
            target_column="quantity",
            time_column="order_date",
            group_by=None,
        )

        # Run comparison
        try:
            comparison_results = run_full_comparison(
                product_data,
                target_column="quantity",
                time_column="order_date",
                group_by=None,
                experiment_name=f"product_{product_id}_forecasting",
                save_plots=False,
            )

            results[f"product_{product_id}"] = comparison_results

        except Exception as e:
            logger.error(f"Failed to forecast for product {product_id}: {e}")
            results[f"product_{product_id}"] = None

    return results


def main():
    """Main function to run forecasting experiments."""
    logger.info("🚀 Starting Demand Forecasting Experiments")

    # Initialize Spark session
    spark = SparkSession.builder.appName("DemandForecasting").getOrCreate()

    try:
        # Try to load real data first
        try:
            orders_df = load_healthcare_data(spark)
            logger.info("✅ Loaded real healthcare data from Unity Catalog")
        except:
            logger.warning("⚠️ Could not load real data, using sample data")
            orders_df = create_sample_data()

        # Run overall demand forecasting
        logger.info("Running overall demand forecasting...")
        overall_results = run_full_comparison(
            orders_df,
            target_column="quantity",
            time_column="order_date",
            group_by=None,
            experiment_name="overall_demand_forecasting",
        )

        # Run pharmacy-level forecasting
        pharmacy_results = run_pharmacy_level_forecasting(orders_df)

        # Run product-level forecasting
        product_results = run_product_level_forecasting(orders_df)

        # Summary
        logger.info("=" * 60)
        logger.info("EXPERIMENT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Overall forecasting: {'✅' if overall_results else '❌'}")
        logger.info(
            f"Pharmacy-level forecasting: {len([r for r in pharmacy_results.values() if r is not None])} successful"
        )
        logger.info(
            f"Product-level forecasting: {len([r for r in product_results.values() if r is not None])} successful"
        )
        logger.info("=" * 60)

        return {
            "overall": overall_results,
            "pharmacy_level": pharmacy_results,
            "product_level": product_results,
        }

    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    results = main()
    logger.info("🎯 Demand forecasting experiments completed!")
