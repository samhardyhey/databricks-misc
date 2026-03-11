{{
  config(
    materialized='table',
    schema='bronze',
    tags=['bronze', 'raw_data', 'reco']
  )
}}

-- Recommendation engine: raw substitution events
select
    *,
    {{ current_timestamp_expr() }} as bronze_processed_at,
    'bronze_reco_substitutions' as bronze_model_name
from {{ source('healthcare_raw', 'healthcare_substitution_events') }}
