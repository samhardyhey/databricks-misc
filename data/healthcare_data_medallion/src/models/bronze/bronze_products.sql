{{
  config(
    materialized='table',
    schema='bronze',
    tags=['bronze', 'raw_data']
  )
}}

-- Bronze layer: Raw products data ingestion
-- This model ingests raw product data with minimal transformations
-- Focus: Data lineage, ingestion tracking, basic data type standardization

select
    product_id,
    name as product_name,
    generic_name,
    category,
    manufacturer,
    supplier,
    pbs_code,
    atc_code,
    unit_price,
    wholesale_price,
    retail_price,
    is_prescription,
    is_controlled_substance,
    requires_cold_chain,
    storage_type,
    expiry_months,
    batch_size,
    minimum_order_quantity,
    lead_time_days,
    active_ingredient,
    dosage_form,
    pack_size,
    created_date,
    last_updated,
    
    -- Metadata columns for data lineage
    _ingestion_timestamp,
    _source,
    _batch_id,
    
    -- Bronze layer transformations
    {{ current_timestamp_expr() }} as bronze_processed_at,
    'bronze_products' as bronze_model_name

from {{ source('healthcare_raw', 'healthcare_products') }}
