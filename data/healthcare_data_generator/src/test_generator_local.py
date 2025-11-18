"""
Test script for the healthcare data generator.

This script demonstrates both simple single-table and complex multi-table
dataset generation with proper relationships for pharmaceutical distribution scenarios.
"""

from pathlib import Path

import pandas as pd
from healthcare_data_generator import DEFAULT_SIZES, HealthcareDataGenerator
from loguru import logger


def test_simple_dataset():
    """Test generation of a simple single-table dataset."""
    logger.info("=== SIMPLE DATASET TEST ===")

    generator = HealthcareDataGenerator(seed=42)

    # Generate a simple dataset - just products
    products = generator.generate_products(n_products=50)

    print(f"\n📊 Simple Dataset - Products")
    print(f"Records: {len(products):,}")
    print(f"Columns: {len(products.columns)}")
    print(f"Memory: {products.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

    print(f"\n🔍 Sample Data:")
    sample_cols = ["product_id", "name", "category", "unit_price", "is_prescription"]
    print(products[sample_cols].head(10).to_string(index=False))

    print(f"\n📈 Data Quality Check:")
    print(f"Unique products: {products['product_id'].nunique()}")
    print(
        f"Prescription vs OTC: {products['is_prescription'].value_counts().to_dict()}"
    )
    print(f"Categories: {products['category'].value_counts().head()}")

    return products


def test_complex_dataset():
    """Test generation of a complex multi-table dataset with relationships."""
    logger.info("=== COMPLEX DATASET TEST ===")

    generator = HealthcareDataGenerator(seed=42)

    # Generate a comprehensive dataset using default sizes
    datasets = generator.generate_all_datasets(
        n_pharmacies=DEFAULT_SIZES["pharmacies"],
        n_hospitals=DEFAULT_SIZES["hospitals"],
        n_products=DEFAULT_SIZES["products"],
        n_orders=DEFAULT_SIZES["orders"],
        n_inventory=DEFAULT_SIZES["inventory"],
        n_events=DEFAULT_SIZES["events"],
    )

    print(f"\n📊 Complex Dataset Summary:")
    total_records = 0
    for name, df in datasets.items():
        records = len(df)
        total_records += records
        print(f"  {name:20}: {records:6,} records")
    print(f"  {'TOTAL':20}: {total_records:6,} records")

    # Test relationships
    orders = datasets["orders"]
    products = datasets["products"]
    pharmacies = datasets["pharmacies"]
    hospitals = datasets["hospitals"]

    print(f"\n🔗 Relationship Analysis:")
    print(
        f"  Orders → Products: {orders['product_id'].isin(products['product_id']).sum()}/{len(orders)} ({100*orders['product_id'].isin(products['product_id']).mean():.1f}%)"
    )
    print(
        f"  Orders → Pharmacies: {orders[orders['customer_type'] == 'Pharmacy']['customer_id'].isin(pharmacies['pharmacy_id']).sum()}/{len(orders[orders['customer_type'] == 'Pharmacy'])}"
    )
    print(
        f"  Orders → Hospitals: {orders[orders['customer_type'] == 'Hospital']['customer_id'].isin(hospitals['hospital_id']).sum()}/{len(orders[orders['customer_type'] == 'Hospital'])}"
    )

    # Business insights
    print(f"\n💼 Business Insights:")
    print(f"  Average order value: ${orders['discounted_amount'].mean():.2f}")
    print(f"  Total revenue: ${orders['discounted_amount'].sum():,.2f}")
    print(
        f"  Pharmacy vs Hospital orders: {orders['customer_type'].value_counts().to_dict()}"
    )
    print(
        f"  Order status distribution: {orders['order_status'].value_counts().to_dict()}"
    )

    # Show sample with joins
    print(f"\n🔍 Sample Order with Full Details:")
    sample_order = orders.head(1)
    order_id = sample_order["order_id"].iloc[0]
    product_id = sample_order["product_id"].iloc[0]
    customer_id = sample_order["customer_id"].iloc[0]
    customer_type = sample_order["customer_type"].iloc[0]

    # Get related data
    product_info = products[products["product_id"] == product_id].iloc[0]
    if customer_type == "Pharmacy":
        customer_info = pharmacies[pharmacies["pharmacy_id"] == customer_id].iloc[0]
    else:
        customer_info = hospitals[hospitals["hospital_id"] == customer_id].iloc[0]

    print(f"  Order: {order_id}")
    print(f"  Customer: {customer_info['name']} ({customer_type})")
    print(f"  Product: {product_info['name']} - {product_info['category']}")
    print(f"  Quantity: {sample_order['quantity'].iloc[0]}")
    print(f"  Total: ${sample_order['discounted_amount'].iloc[0]:.2f}")

    return datasets


def test_data_export():
    """Test data export functionality."""
    logger.info("=== DATA EXPORT TEST ===")

    generator = HealthcareDataGenerator(seed=42)

    # Generate a smaller dataset for export
    datasets = generator.generate_all_datasets(
        n_pharmacies=10,
        n_hospitals=5,
        n_products=50,
        n_orders=100,
        n_inventory=200,
        n_events=50,
    )

    # Create output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)

    # Save datasets
    generator.save_datasets(datasets, output_dir=str(output_dir))

    print(f"\n💾 Data Export Test Complete!")
    print(f"  Output directory: {output_dir.absolute()}")
    print(f"  Files created:")
    for file_path in output_dir.glob("*.csv"):
        file_size = file_path.stat().st_size / 1024  # KB
        print(f"    {file_path.name}: {file_size:.1f} KB")

    return datasets


def test_analytics_queries():
    """Test analytical queries on the generated data."""
    logger.info("=== ANALYTICS TEST ===")

    generator = HealthcareDataGenerator(seed=42)
    datasets = generator.generate_all_datasets(
        n_pharmacies=30,
        n_hospitals=15,
        n_products=200,
        n_orders=1000,
        n_inventory=500,
        n_events=200,
    )

    orders = datasets["orders"]
    products = datasets["products"]
    datasets["pharmacies"]

    print(f"\n📊 Analytics Test Results:")

    # Top products by revenue
    product_revenue = (
        orders.groupby("product_id")["discounted_amount"]
        .sum()
        .sort_values(ascending=False)
    )
    top_products = product_revenue.head(3)
    print(f"\n  Top 3 Products by Revenue:")
    for product_id, revenue in top_products.items():
        product_name = products[products["product_id"] == product_id]["name"].iloc[0]
        print(f"    {product_name}: ${revenue:,.2f}")

    # Monthly sales trend
    orders["order_month"] = pd.to_datetime(orders["order_date"]).dt.to_period("M")
    monthly_sales = orders.groupby("order_month")["discounted_amount"].sum()
    print(f"\n  Monthly Sales Trend (last 3 months):")
    for month, sales in monthly_sales.tail(3).items():
        print(f"    {month}: ${sales:,.2f}")

    # Product category analysis
    category_analysis = orders.merge(
        products[["product_id", "category"]], on="product_id"
    )
    category_revenue = (
        category_analysis.groupby("category")["discounted_amount"]
        .sum()
        .sort_values(ascending=False)
    )
    print(f"\n  Top 3 Categories by Revenue:")
    for category, revenue in category_revenue.head(3).items():
        print(f"    {category}: ${revenue:,.2f}")


def main():
    """Run all tests."""
    logger.info("Starting comprehensive healthcare data generator tests...")

    try:
        # Test 1: Simple dataset
        test_simple_dataset()

        # Test 2: Complex dataset
        test_complex_dataset()

        # Test 3: Data export
        test_data_export()

        # Test 4: Analytics
        test_analytics_queries()

        logger.info("All tests completed successfully!")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
