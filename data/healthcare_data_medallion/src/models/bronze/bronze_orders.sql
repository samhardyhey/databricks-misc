{{
  config(
    materialized='table',
    schema='bronze',
    tags=['bronze', 'raw_data']
  )
}}

-- Bronze layer: Raw orders data ingestion
-- This model ingests raw orders data with minimal transformations
-- Focus: Data lineage, ingestion tracking, basic data type standardization

select
    order_id,
    customer_id,
    customer_type,
    product_id,
    order_date,
    quantity,
    unit_price,
    total_amount,
    discount_rate,
    discounted_amount,
    order_status,
    payment_terms,
    shipping_method,
    expected_delivery,
    actual_delivery,
    special_instructions,
    sales_rep,
    created_timestamp,
    
    -- Metadata columns for data lineage
    _ingestion_timestamp,
    _source,
    _batch_id,
    
    -- Bronze layer transformations
    {{ current_timestamp_expr() }} as bronze_processed_at,
    'bronze_orders' as bronze_model_name

from {{ source('healthcare_raw', 'healthcare_orders') }}
