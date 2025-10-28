{{
  config(
    materialized='table',
    schema='bronze',
    tags=['bronze', 'raw_data']
  )
}}

-- Bronze layer: Raw supply chain events data ingestion
-- This model ingests raw supply chain events data with minimal transformations
-- Focus: Data lineage, ingestion tracking, basic data type standardization

select
    event_id,
    order_id,
    event_type,
    event_timestamp,
    location,
    status,
    description,
    operator,
    equipment_id,
    temperature,
    notes,
    
    -- Metadata columns for data lineage
    _ingestion_timestamp,
    _source,
    _batch_id,
    
    -- Bronze layer transformations
    current_timestamp() as bronze_processed_at,
    'bronze_supply_chain_events' as bronze_model_name

from {{ source('healthcare_raw', 'healthcare_supply_chain_events') }}
