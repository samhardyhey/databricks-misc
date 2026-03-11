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
    'bronze_product_interactions' as bronze_model_name
from {{ source('healthcare_raw', 'healthcare_product_interactions') }}
