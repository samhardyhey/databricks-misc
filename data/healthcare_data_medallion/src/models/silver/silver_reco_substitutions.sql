{{
  config(
    materialized='table',
    schema='silver',
    tags=['silver', 'business_logic', 'reco']
  )
}}

-- Recommendation engine: validated substitution events with order/product FK checks
with base as (
    select
        s.substitution_id,
        s.order_id,
        s.requested_product_id,
        s.substituted_product_id,
        trim(lower(cast(s.reason as varchar))) as reason,
        s.customer_accepted,
        round(cast(s.margin_delta as double), 4) as margin_delta,
        s.timestamp as substitution_timestamp,
        s.bronze_processed_at,
        {{ current_timestamp_expr() }} as silver_processed_at,
        'silver_reco_substitutions' as silver_model_name
    from {{ ref('bronze_reco_substitutions') }} s
    inner join {{ ref('bronze_orders') }} o on s.order_id = o.order_id
    inner join {{ ref('bronze_products') }} req on s.requested_product_id = req.product_id
    inner join {{ ref('bronze_products') }} sub on s.substituted_product_id = sub.product_id
    where s.substitution_id is not null
      and s.order_id is not null
      and s.requested_product_id is not null
      and s.substituted_product_id is not null
)
select * from base
