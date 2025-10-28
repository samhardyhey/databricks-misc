{{
  config(
    materialized='table',
    schema='bronze',
    tags=['bronze', 'raw_data']
  )
}}

-- Bronze layer: Raw hospital data ingestion
-- This model ingests raw hospital data with minimal transformations
-- Focus: Data lineage, ingestion tracking, basic data type standardization

select
    hospital_id,
    name as hospital_name,
    hospital_type,
    address,
    suburb,
    state,
    postcode,
    phone,
    email,
    license_number,
    beds,
    emergency_department,
    icu_beds,
    specialties,
    accreditation_date,
    monthly_budget,
    procurement_contact,
    procurement_email,

    -- Metadata columns for data lineage
    _ingestion_timestamp,
    _source,
    _batch_id,

    -- Bronze layer transformations
    current_timestamp() as bronze_processed_at,
    'bronze_hospitals' as bronze_model_name

from {{ source('healthcare_raw', 'hospitals') }}
