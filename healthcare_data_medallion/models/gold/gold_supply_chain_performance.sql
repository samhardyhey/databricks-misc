{{
  config(
    materialized='table',
    schema='gold',
    tags=['gold', 'analytics', 'supply_chain_analytics']
  )
}}

-- Gold layer: Supply Chain Analytics - Order Fulfillment and Logistics Metrics
-- This model provides comprehensive supply chain performance analytics
-- Focus: Order fulfillment, delivery performance, logistics optimization

with order_fulfillment as (
    select
        o.order_id,
        o.customer_id,
        o.customer_type,
        o.product_id,
        o.order_date,
        o.expected_delivery,
        o.actual_delivery,
        o.order_status,
        o.shipping_method,
        o.total_amount,
        o.quantity,
        o.delivery_performance,
        o.delivery_delay_days,
        o.volume_tier,
        o.order_value_tier,

        -- Calculate fulfillment metrics
        case
            when o.order_status = 'DELIVERED' then 1
            else 0
        end as is_delivered,

        case
            when o.order_status = 'DELIVERED' and o.delivery_delay_days <= 0 then 1
            else 0
        end as is_on_time_delivery,

        case
            when o.order_status = 'CANCELLED' then 1
            else 0
        end as is_cancelled,

        case
            when o.delivery_delay_days > 7 then 1
            else 0
        end as is_significantly_delayed
    from {{ ref('silver_orders') }} o
),

supply_chain_events_summary as (
    select 
        sce.order_id,
        count(distinct sce.event_id) as total_events,
        count(distinct case when sce.status = 'SUCCESS' then sce.event_id end) as successful_events,
        count(distinct case when sce.status = 'ERROR' then sce.event_id end) as failed_events,
        count(distinct case when sce.status = 'WARNING' then sce.event_id end) as warning_events,
        min(sce.event_timestamp) as first_event_timestamp,
        max(sce.event_timestamp) as last_event_timestamp,
        count(distinct sce.event_category) as event_categories_count,
        
        -- Calculate rates
        case 
            when count(distinct sce.event_id) > 0 then round(count(distinct case when sce.status = 'SUCCESS' then sce.event_id end) / count(distinct sce.event_id) * 100, 2)
            else 0
        end as event_success_rate,
        
        case 
            when count(distinct sce.event_id) > 0 then round(count(distinct case when sce.status = 'ERROR' then sce.event_id end) / count(distinct sce.event_id) * 100, 2)
            else 0
        end as event_failure_rate,
        
        case 
            when count(distinct sce.event_id) > 0 then round(count(distinct case when sce.status = 'WARNING' then sce.event_id end) / count(distinct sce.event_id) * 100, 2)
            else 0
        end as event_warning_rate
    from {{ ref('silver_supply_chain_events') }} sce
    group by sce.order_id
),

monthly_performance as (
    select
        date_trunc('month', of.order_date) as order_month,
        count(distinct of.order_id) as total_orders,
        count(distinct case when of.is_delivered = 1 then of.order_id end) as delivered_orders,
        count(distinct case when of.is_on_time_delivery = 1 then of.order_id end) as on_time_orders,
        count(distinct case when of.is_cancelled = 1 then of.order_id end) as cancelled_orders,
        count(distinct case when of.is_significantly_delayed = 1 then of.order_id end) as significantly_delayed_orders,
        sum(of.total_amount) as total_order_value,
        avg(of.delivery_delay_days) as avg_delivery_delay_days,
        count(distinct of.customer_id) as unique_customers,
        count(distinct of.product_id) as unique_products
    from order_fulfillment of
    group by date_trunc('month', of.order_date)
)

select
    of.order_id,
    of.customer_id,
    of.customer_type,
    of.product_id,
    of.order_date,
    of.expected_delivery,
    of.actual_delivery,
    of.order_status,
    of.shipping_method,
    of.total_amount,
    of.quantity,
    of.delivery_performance,
    of.delivery_delay_days,
    of.volume_tier,
    of.order_value_tier,

    -- Fulfillment flags
    of.is_delivered,
    of.is_on_time_delivery,
    of.is_cancelled,
    of.is_significantly_delayed,

    -- Supply chain event metrics
    coalesce(sce.total_events, 0) as total_events,
    coalesce(sce.successful_events, 0) as successful_events,
    coalesce(sce.failed_events, 0) as failed_events,
    coalesce(sce.warning_events, 0) as warning_events,
    coalesce(sce.event_categories_count, 0) as event_categories_count,

    -- Event timing
    sce.first_event_timestamp,
    sce.last_event_timestamp,
    case 
        when sce.first_event_timestamp is not null and sce.last_event_timestamp is not null then
            datediff(sce.last_event_timestamp, sce.first_event_timestamp) * 24
        else null
    end as fulfillment_duration_hours,
    
    -- Event rates (already calculated in CTE)
    sce.event_success_rate,
    sce.event_failure_rate,
    sce.event_warning_rate,

    -- Performance classifications
    case 
        when of.is_delivered = 1 and of.is_on_time_delivery = 1 then 'Excellent'
        when of.is_delivered = 1 and of.delivery_delay_days <= 2 then 'Good'
        when of.is_delivered = 1 and of.delivery_delay_days <= 7 then 'Fair'
        when of.is_delivered = 1 then 'Poor'
        when of.is_cancelled = 1 then 'Cancelled'
        else 'In Progress'
    end as overall_performance,

    case
        when sce.event_success_rate >= 90 then 'High Reliability'
        when sce.event_success_rate >= 70 then 'Medium Reliability'
        when sce.event_success_rate > 0 then 'Low Reliability'
        else 'No Event Data'
    end as reliability_tier,

    -- Risk indicators
    case 
        when of.is_significantly_delayed = 1 or sce.event_failure_rate > 20 then 'High Risk'
        when of.delivery_delay_days > 3 or sce.event_failure_rate > 10 then 'Medium Risk'
        when of.delivery_delay_days > 0 or sce.event_failure_rate > 0 then 'Low Risk'
        else 'No Risk'
    end as risk_level,

    -- Metadata
    current_timestamp() as gold_processed_at,
    'gold_supply_chain_performance' as gold_model_name

from order_fulfillment of
left join supply_chain_events_summary sce on of.order_id = sce.order_id
