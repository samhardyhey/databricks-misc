{{
  config(
    materialized='table',
    schema='bronze',
    tags=['bronze', 'raw_data']
  )
}}

select
    *,
    {{ current_timestamp_expr() }} as bronze_processed_at,
    'bronze_store_attributes' as bronze_model_name
from {{ source('healthcare_raw', 'healthcare_store_attributes') }}
