{{
  config(
    materialized='table',
    schema='gold',
    tags=['gold', 'analytics', 'reco']
  )
}}

-- Recommendation engine: slim training base (customer, product, label).
-- ML code reads this and adds negatives, features, splits in Python.
with interactions_labeled as (
    select
        customer_id,
        product_id,
        case when action_type = 'purchased' then 1 else 0 end as label,
        interaction_timestamp,
        interaction_id
    from {{ ref('silver_reco_interactions') }}
)
select
    customer_id,
    product_id,
    max(label) as label,
    max(interaction_timestamp) as last_interaction_timestamp,
    count(*) as interaction_count
from interactions_labeled
group by customer_id, product_id
