#!/bin/bash
# Initialize directories and set permissions inside containers
# This script is run after containers start to ensure directories exist

set -e

echo "Initializing directories in container..."

# Create output directory if it doesn't exist
mkdir -p /opt/bitnami/spark/data/output

# Set permissions (777 allows all users to read/write/execute)
chmod -R 777 /opt/bitnami/spark/data

echo "Directories initialized successfully"

