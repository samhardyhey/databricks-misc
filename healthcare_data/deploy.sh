#!/bin/bash

# Healthcare Data Bundle Deployment Script

echo "🚀 Deploying Healthcare Data Bundle (Serverless with Runtime Dependencies)..."

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
    echo "   3. Check Unity Catalog for generated tables"
    echo ""
    echo "📊 Generated tables will be available at:"
    echo "   - workspace.default.healthcare_pharmacies"
    echo "   - workspace.default.healthcare_hospitals"
    echo "   - workspace.default.healthcare_products"
    echo "   - workspace.default.healthcare_orders"
    echo "   - workspace.default.healthcare_inventory"
    echo "   - workspace.default.healthcare_supply_chain_events"
else
    echo "❌ Deployment failed. Check the error messages above."
    exit 1
fi
