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
    'bronze_purchase_orders' as bronze_model_name
from {{ source('healthcare_raw', 'healthcare_purchase_orders') }}
