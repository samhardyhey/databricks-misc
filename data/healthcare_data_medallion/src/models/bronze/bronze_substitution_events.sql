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
    'bronze_substitution_events' as bronze_model_name
from {{ source('healthcare_raw', 'healthcare_substitution_events') }}
