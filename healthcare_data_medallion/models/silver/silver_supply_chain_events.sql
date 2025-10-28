{{
  config(
    materialized='table',
    schema='silver',
    tags=['silver', 'business_logic']
  )
}}

-- Silver layer: Cleaned and validated supply chain events data
-- This model applies business logic, data quality checks, and standardization
-- Focus: Data quality, business rules, standardized naming

with events_cleaned as (
    select
        event_id,
        order_id,
        trim(upper(event_type)) as event_type,
        event_timestamp,
        trim(upper(location)) as location,
        trim(upper(status)) as status,
        description,
        operator,
        equipment_id,
        temperature,
        notes,
        
        -- Calculated fields
        case 
            when temperature is not null then
                case 
                    when temperature < 0 then 'Frozen'
                    when temperature <= 8 then 'Refrigerated'
                    when temperature <= 25 then 'Room Temperature'
                    else 'Hot'
                end
            else null
        end as temperature_category,
        
        case 
            when status = 'SUCCESS' then 1
            when status = 'WARNING' then 2
            when status = 'ERROR' then 3
            when status = 'PENDING' then 4
            else 5
        end as status_priority,
        
        -- Data quality flags
        case 
            when temperature < -50 or temperature > 100 then true
            else false
        end as has_extreme_temperature,
        
        case 
            when event_timestamp > current_timestamp() then true
            else false
        end as has_future_timestamp,
        
        -- Business classifications
        case 
            when event_type in ('ORDER_RECEIVED', 'PAYMENT_CONFIRMED') then 'Order Processing'
            when event_type in ('PICKING_STARTED', 'PICKING_COMPLETED', 'QUALITY_CHECK', 'PACKAGING') then 'Fulfillment'
            when event_type in ('SHIPPED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY') then 'Shipping'
            when event_type in ('DELIVERED') then 'Delivery'
            when event_type in ('DELIVERY_FAILED', 'RETURNED', 'DAMAGED', 'LOST') then 'Issues'
            else 'Other'
        end as event_category,
        
        case 
            when status = 'SUCCESS' then 'Completed'
            when status = 'WARNING' then 'Attention Required'
            when status = 'ERROR' then 'Failed'
            when status = 'PENDING' then 'In Progress'
            else 'Unknown'
        end as status_description,
        
        -- Temperature monitoring flags
        case 
            when temperature is not null and temperature < 0 then true
            else false
        end as is_frozen_temperature,
        
        case 
            when temperature is not null and temperature between 2 and 8 then true
            else false
        end as is_refrigerated_temperature,
        
        case 
            when temperature is not null and temperature > 25 then true
            else false
        end as is_hot_temperature,
        
        -- Metadata
        _ingestion_timestamp,
        _source,
        _batch_id,
        bronze_processed_at,
        current_timestamp() as silver_processed_at,
        'silver_supply_chain_events' as silver_model_name
        
    from {{ ref('bronze_supply_chain_events') }}
)

select *
from events_cleaned
where 
    -- Data quality filters
    not has_extreme_temperature
    and not has_future_timestamp
    and event_id is not null
    and order_id is not null
    and event_type is not null
