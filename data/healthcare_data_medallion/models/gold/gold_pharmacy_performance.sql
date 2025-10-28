{{
  config(
    materialized='table',
    schema='gold',
    tags=['gold', 'analytics', 'customer_analytics']
  )
}}

-- Gold layer: Customer Analytics - Pharmacy Performance Metrics
-- This model provides comprehensive pharmacy performance analytics
-- Focus: Business intelligence, KPI tracking, performance metrics

with pharmacy_orders as (
    select 
        o.customer_id,
        o.customer_type,
        count(distinct o.order_id) as total_orders,
        sum(o.quantity) as total_quantity_ordered,
        sum(o.total_amount) as total_order_value,
        sum(o.discounted_amount) as total_discounted_value,
        avg(o.total_amount) as avg_order_value,
        avg(o.discount_rate) as avg_discount_rate,
        min(o.order_date) as first_order_date,
        max(o.order_date) as last_order_date,
        count(distinct o.product_id) as unique_products_ordered,
        count(distinct date_trunc('month', o.order_date)) as active_months
    from {{ ref('silver_orders') }} o
    where o.customer_type = 'PHARMACY'
    group by o.customer_id, o.customer_type
),

pharmacy_inventory as (
    select 
        i.pharmacy_id,
        count(distinct i.product_id) as total_products_in_stock,
        sum(i.current_stock) as total_current_stock,
        sum(i.current_stock * i.cost_per_unit) as total_inventory_value,
        count(case when i.reorder_alert then 1 end) as products_needing_reorder,
        count(case when i.expiry_alert then 1 end) as products_expiring_soon,
        avg(i.stock_percentage) as avg_stock_percentage
    from {{ ref('silver_inventory') }} i
    group by i.pharmacy_id
)

select 
    p.pharmacy_id,
    p.pharmacy_name,
    p.pharmacy_type,
    p.state,
    p.suburb,
    p.years_in_operation,
    p.revenue_tier,
    p.customer_volume_tier,
    p.monthly_revenue,
    p.customer_count,
    p.has_consultation_room,
    p.has_vaccination_service,
    
    -- Order performance metrics
    coalesce(po.total_orders, 0) as total_orders,
    coalesce(po.total_quantity_ordered, 0) as total_quantity_ordered,
    coalesce(po.total_order_value, 0) as total_order_value,
    coalesce(po.total_discounted_value, 0) as total_discounted_value,
    coalesce(po.avg_order_value, 0) as avg_order_value,
    coalesce(po.avg_discount_rate, 0) as avg_discount_rate,
    coalesce(po.unique_products_ordered, 0) as unique_products_ordered,
    coalesce(po.active_months, 0) as active_months,
    
    -- Inventory performance metrics
    coalesce(pi.total_products_in_stock, 0) as total_products_in_stock,
    coalesce(pi.total_current_stock, 0) as total_current_stock,
    coalesce(pi.total_inventory_value, 0) as total_inventory_value,
    coalesce(pi.products_needing_reorder, 0) as products_needing_reorder,
    coalesce(pi.products_expiring_soon, 0) as products_expiring_soon,
    coalesce(pi.avg_stock_percentage, 0) as avg_stock_percentage,
    
    -- Calculated KPIs
    case 
        when po.total_orders > 0 then round(po.total_order_value / po.total_orders, 2)
        else 0
    end as revenue_per_order,
    
    case 
        when p.customer_count > 0 then round(po.total_order_value / p.customer_count, 2)
        else 0
    end as revenue_per_customer,
    
    case 
        when po.total_orders > 0 then round(po.total_quantity_ordered / po.total_orders, 2)
        else 0
    end as avg_quantity_per_order,
    
    case 
        when pi.total_products_in_stock > 0 then round(pi.products_needing_reorder / pi.total_products_in_stock * 100, 2)
        else 0
    end as reorder_percentage,
    
    case 
        when pi.total_products_in_stock > 0 then round(pi.products_expiring_soon / pi.total_products_in_stock * 100, 2)
        else 0
    end as expiry_risk_percentage,
    
    -- Performance classifications
    case 
        when po.total_order_value >= 100000 then 'High Performer'
        when po.total_order_value >= 50000 then 'Medium Performer'
        when po.total_order_value > 0 then 'Low Performer'
        else 'No Orders'
    end as performance_tier,
    
    case 
        when pi.avg_stock_percentage >= 70 then 'Well Stocked'
        when pi.avg_stock_percentage >= 30 then 'Adequately Stocked'
        when pi.avg_stock_percentage > 0 then 'Under Stocked'
        else 'No Inventory Data'
    end as inventory_health,
    
    -- Metadata
    current_timestamp() as gold_processed_at,
    'gold_pharmacy_performance' as gold_model_name

from {{ ref('silver_pharmacies') }} p
left join pharmacy_orders po on p.pharmacy_id = po.customer_id
left join pharmacy_inventory pi on p.pharmacy_id = pi.pharmacy_id
