#!/bin/bash

# Healthcare Data Medallion Bundle Deployment Script

echo "🚀 Deploying Healthcare Data Medallion Bundle (Bronze → Silver → Gold)..."

# Check if databricks CLI is installed
if ! command -v databricks &> /dev/null; then
    echo "❌ Databricks CLI not found. Please install it first."
    echo "   Visit: https://docs.databricks.com/dev-tools/cli/databricks-cli.html"
    exit 1
fi

# Deploy to development environment
echo "📦 Deploying to development environment..."
databricks bundle deploy --target dev

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo ""
    echo "🔧 Next steps:"
    echo "   1. Check the job in your Databricks workspace"
    echo "   2. Run the job: databricks bundle run"
    echo "   3. Check Unity Catalog for medallion layers"
    echo ""
    echo "📊 Medallion layers will be available at:"
    echo ""
    echo "   🥉 BRONZE LAYER (Raw Data):"
    echo "   - workspace.healthcare_dev_raw.healthcare_pharmacies"
    echo "   - workspace.healthcare_dev_raw.healthcare_hospitals"
    echo "   - workspace.healthcare_dev_raw.healthcare_products"
    echo "   - workspace.healthcare_dev_raw.healthcare_orders"
    echo "   - workspace.healthcare_dev_raw.healthcare_inventory"
    echo "   - workspace.healthcare_dev_raw.healthcare_supply_chain_events"
    echo ""
    echo "   🥈 SILVER LAYER (Cleaned Data):"
    echo "   - workspace.healthcare_medallion_dev_silver.silver_pharmacies"
    echo "   - workspace.healthcare_medallion_dev_silver.silver_hospitals"
    echo "   - workspace.healthcare_medallion_dev_silver.silver_products"
    echo "   - workspace.healthcare_medallion_dev_silver.silver_orders"
    echo "   - workspace.healthcare_medallion_dev_silver.silver_inventory"
    echo "   - workspace.healthcare_medallion_dev_silver.silver_supply_chain_events"
    echo ""
    echo "   🥇 GOLD LAYER (Analytics-Ready):"
    echo "   - workspace.healthcare_medallion_dev_gold.gold_pharmacy_performance"
    echo "   - workspace.healthcare_medallion_dev_gold.gold_product_performance"
    echo "   - workspace.healthcare_medallion_dev_gold.gold_financial_analytics"
    echo "   - workspace.healthcare_medallion_dev_gold.gold_ml_ready_dataset"
    echo "   - workspace.healthcare_medallion_dev_gold.gold_supply_chain_performance"
    echo ""
    echo "💡 To deploy to production:"
    echo "   databricks bundle deploy --target prod"
else
    echo "❌ Deployment failed. Check the error messages above."
    exit 1
fi
