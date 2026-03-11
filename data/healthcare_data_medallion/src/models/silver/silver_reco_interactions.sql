{{
  config(
    materialized='table',
    schema='silver',
    tags=['silver', 'business_logic', 'reco']
  )
}}

-- Recommendation engine: cleaned product interactions; action_type standardized for ML
with base as (
    select
        i.interaction_id,
        i.customer_id,
        i.product_id,
        case
            when lower(trim(cast(i.action_type as varchar))) in ('added_to_cart', 'added') then 'added'
            when lower(trim(cast(i.action_type as varchar))) = 'viewed' then 'viewed'
            when lower(trim(cast(i.action_type as varchar))) = 'searched' then 'searched'
            when lower(trim(cast(i.action_type as varchar))) = 'purchased' then 'purchased'
            else lower(trim(cast(i.action_type as varchar)))
        end as action_type,
        i.timestamp as interaction_timestamp,
        i.session_id,
        i.bronze_processed_at,
        {{ current_timestamp_expr() }} as silver_processed_at,
        'silver_reco_interactions' as silver_model_name
    from {{ ref('bronze_reco_interactions') }} i
    inner join {{ ref('bronze_products') }} p on i.product_id = p.product_id
    where i.interaction_id is not null
      and i.customer_id is not null
      and i.product_id is not null
      and i.timestamp is not null
)
select * from base
