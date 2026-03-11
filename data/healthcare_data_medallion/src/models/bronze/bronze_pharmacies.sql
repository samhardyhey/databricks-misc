{{
  config(
    materialized='table',
    schema='bronze',
    tags=['bronze', 'raw_data']
  )
}}

-- Bronze layer: Raw pharmacy data ingestion
-- This model ingests raw pharmacy data with minimal transformations
-- Focus: Data lineage, ingestion tracking, basic data type standardization

select
    pharmacy_id,
    name as pharmacy_name,
    is_chain,
    address,
    suburb,
    state,
    postcode,
    phone,
    email,
    license_number,
    established_date,
    pharmacist_in_charge,
    trading_hours,
    has_consultation_room,
    has_vaccination_service,
    monthly_revenue,
    customer_count,
    
    -- Metadata columns for data lineage
    _ingestion_timestamp,
    _source,
    _batch_id,
    
    -- Bronze layer transformations
    {{ current_timestamp_expr() }} as bronze_processed_at,
    'bronze_pharmacies' as bronze_model_name

from {{ source('healthcare_raw', 'healthcare_pharmacies') }}
