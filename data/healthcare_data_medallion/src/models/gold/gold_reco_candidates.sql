{{
  config(
    materialized='table',
    schema='gold',
    tags=['gold', 'analytics', 'reco']
  )
}}

-- Recommendation engine: batch-scored top recommendations per customer.
-- Populated by use_cases/recommendation_engine jobs/2_batch_scoring.py.
-- Stub: empty schema; job overwrites or appends with (customer_id, product_id, score, reason, margin, rank).
select
    cast(null as varchar) as customer_id,
    cast(null as varchar) as product_id,
    cast(null as double) as score,
    cast(null as varchar) as reason,
    cast(null as double) as margin,
    cast(null as bigint) as rank
where 1 = 0
