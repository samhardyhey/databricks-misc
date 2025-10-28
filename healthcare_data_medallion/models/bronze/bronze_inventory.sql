{{
  config(
    materialized='table',
    schema='bronze',
    tags=['bronze', 'raw_data']
  )
}}

-- Bronze layer: Raw inventory data ingestion
-- This model ingests raw inventory data with minimal transformations
-- Focus: Data lineage, ingestion tracking, basic data type standardization

select
    inventory_id,
    pharmacy_id,
    product_id,
    current_stock,
    reorder_level,
    max_stock,
    needs_reorder,
    last_restocked,
    expiry_date,
    batch_number,
    storage_location,
    cost_per_unit,
    last_movement_date,
    movement_type,
    movement_quantity,
    updated_timestamp,

    -- Metadata columns for data lineage
    _ingestion_timestamp,
    _source,
    _batch_id,

    -- Bronze layer transformations
    current_timestamp() as bronze_processed_at,
    'bronze_inventory' as bronze_model_name

from {{ source('healthcare_raw', 'inventory') }}
