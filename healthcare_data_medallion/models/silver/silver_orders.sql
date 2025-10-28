{{
  config(
    materialized='table',
    schema='silver',
    tags=['silver', 'business_logic']
  )
}}

-- Silver layer: Cleaned and validated orders data
-- This model applies business logic, data quality checks, and standardization
-- Focus: Data quality, business rules, standardized naming

with order_cleaned as (
    select
        order_id,
        customer_id,
        trim(upper(customer_type)) as customer_type,
        product_id,
        
        -- Dates
        order_date,
        expected_delivery,
        actual_delivery,
        created_timestamp,
        
        -- Order metrics
        quantity,
        round(unit_price, 2) as unit_price,
        round(total_amount, 2) as total_amount,
        round(discount_rate, 4) as discount_rate,
        round(discounted_amount, 2) as discounted_amount,
        
        -- Order details
        trim(upper(order_status)) as order_status,
        trim(upper(payment_terms)) as payment_terms,
        trim(upper(shipping_method)) as shipping_method,
        special_instructions,
        sales_rep,
        
        -- Calculated fields
        case 
            when actual_delivery is not null then datediff(actual_delivery, order_date)
            else null
        end as actual_delivery_days,
        
        case 
            when expected_delivery is not null then datediff(expected_delivery, order_date)
            else null
        end as expected_delivery_days,
        
        case 
            when actual_delivery is not null and expected_delivery is not null then 
                datediff(actual_delivery, expected_delivery)
            else null
        end as delivery_delay_days,
        
        -- Data quality flags
        case 
            when quantity < 0 then true
            else false
        end as has_negative_quantity,
        
        case 
            when unit_price < 0 then true
            else false
        end as has_negative_unit_price,
        
        case 
            when total_amount < 0 then true
            else false
        end as has_negative_total_amount,
        
        case 
            when discount_rate < 0 or discount_rate > 1 then true
            else false
        end as has_invalid_discount_rate,
        
        case 
            when actual_delivery_days < 0 then true
            else false
        end as has_negative_delivery_days,
        
        -- Business classifications
        case 
            when quantity >= {{ var('business_rules')['high_volume_discount_threshold'] }} then 'High Volume'
            when quantity >= {{ var('business_rules')['medium_volume_discount_threshold'] }} then 'Medium Volume'
            else 'Low Volume'
        end as volume_tier,
        
        case 
            when total_amount >= 10000 then 'High Value'
            when total_amount >= 1000 then 'Medium Value'
            else 'Low Value'
        end as order_value_tier,
        
        case 
            when order_status = 'DELIVERED' and delivery_delay_days <= 0 then 'On Time'
            when order_status = 'DELIVERED' and delivery_delay_days > 0 then 'Late'
            when order_status = 'DELIVERED' and delivery_delay_days is null then 'Delivered'
            else 'In Progress'
        end as delivery_performance,
        
        case 
            when discount_rate > 0.1 then 'High Discount'
            when discount_rate > 0.05 then 'Medium Discount'
            when discount_rate > 0 then 'Low Discount'
            else 'No Discount'
        end as discount_tier,
        
        -- Metadata
        _ingestion_timestamp,
        _source,
        _batch_id,
        bronze_processed_at,
        current_timestamp() as silver_processed_at,
        'silver_orders' as silver_model_name
        
    from {{ ref('bronze_orders') }}
)

select *
from order_cleaned
where 
    -- Data quality filters
    not has_negative_quantity
    and not has_negative_unit_price
    and not has_negative_total_amount
    and not has_invalid_discount_rate
    and not has_negative_delivery_days
    and order_id is not null
    and customer_id is not null
    and product_id is not null
