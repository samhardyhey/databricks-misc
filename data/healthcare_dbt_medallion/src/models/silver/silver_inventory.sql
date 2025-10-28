{{
  config(
    materialized='table',
    schema='silver',
    tags=['silver', 'business_logic']
  )
}}

-- Silver layer: Cleaned and validated inventory data
-- This model applies business logic, data quality checks, and standardization
-- Focus: Data quality, business rules, standardized naming

with inventory_cleaned as (
    select
        inventory_id,
        pharmacy_id,
        product_id,

        -- Stock levels
        current_stock,
        reorder_level,
        max_stock,
        needs_reorder,

        -- Dates
        last_restocked,
        expiry_date,
        last_movement_date,
        updated_timestamp,

        -- Inventory details
        batch_number,
        trim(upper(storage_location)) as storage_location,
        round(cost_per_unit, 2) as cost_per_unit,
        trim(upper(movement_type)) as movement_type,
        movement_quantity,

        -- Calculated fields
        case 
            when expiry_date is not null then datediff(expiry_date, current_date())
            else null
        end as days_until_expiry,

        case
            when max_stock > 0 then round(current_stock / max_stock * 100, 2)
            else 0
        end as stock_percentage,

        case
            when reorder_level > 0 then round(current_stock / reorder_level, 2)
            else null
        end as stock_to_reorder_ratio,

        case 
            when last_restocked is not null then datediff(current_date(), last_restocked)
            else null
        end as days_since_last_restock,

        -- Data quality flags
        case
            when current_stock < 0 then true
            else false
        end as has_negative_stock,

        case
            when reorder_level < 0 then true
            else false
        end as has_negative_reorder_level,

        case
            when max_stock < 0 then true
            else false
        end as has_negative_max_stock,

        case
            when days_until_expiry < 0 then true
            else false
        end as has_expired_product,

        case
            when days_since_last_restock < 0 then true
            else false
        end as has_future_restock_date,

        -- Business classifications
        case
            when current_stock <= reorder_level then 'Critical Stock'
            when current_stock <= reorder_level * 1.5 then 'Low Stock'
            when current_stock >= max_stock * 0.8 then 'High Stock'
            else 'Normal Stock'
        end as stock_status,

        case
            when days_until_expiry <= {{ var('business_rules')['expiry_warning_days'] }} then 'Expiring Soon'
            when days_until_expiry <= {{ var('business_rules')['expiry_warning_days'] }} * 2 then 'Approaching Expiry'
            else 'Fresh Stock'
        end as expiry_status,

        case
            when stock_percentage >= 80 then 'Overstocked'
            when stock_percentage >= 50 then 'Well Stocked'
            when stock_percentage >= 20 then 'Low Stock'
            else 'Critical Stock'
        end as stock_level_tier,

        -- Alert flags
        case
            when current_stock <= reorder_level then true
            else false
        end as reorder_alert,

        case
            when days_until_expiry <= {{ var('business_rules')['expiry_warning_days'] }} then true
            else false
        end as expiry_alert,

        case
            when stock_percentage <= {{ var('business_rules')['reorder_alert_threshold'] }} * 100 then true
            else false
        end as low_stock_alert,

        -- Metadata
        _ingestion_timestamp,
        _source,
        _batch_id,
        bronze_processed_at,
        current_timestamp() as silver_processed_at,
        'silver_inventory' as silver_model_name

    from {{ ref('bronze_inventory') }}
)

select *
from inventory_cleaned
where
    -- Data quality filters
    not has_negative_stock
    and not has_negative_reorder_level
    and not has_negative_max_stock
    and not has_future_restock_date
    and inventory_id is not null
    and pharmacy_id is not null
    and product_id is not null
