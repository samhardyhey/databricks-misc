{{
  config(
    materialized='table',
    schema='gold',
    tags=['gold', 'analytics', 'product_analytics']
  )
}}

-- Gold layer: Product Analytics - Product Performance Metrics
-- This model provides comprehensive product performance analytics
-- Focus: Product performance, demand patterns, profitability analysis

with product_orders as (
    select 
        o.product_id,
        count(distinct o.order_id) as total_orders,
        count(distinct o.customer_id) as unique_customers,
        sum(o.quantity) as total_quantity_sold,
        sum(o.total_amount) as total_revenue,
        sum(o.discounted_amount) as total_discounted_revenue,
        avg(o.quantity) as avg_quantity_per_order,
        avg(o.total_amount) as avg_order_value,
        avg(o.discount_rate) as avg_discount_rate,
        min(o.order_date) as first_order_date,
        max(o.order_date) as last_order_date,
        count(distinct date_trunc('month', o.order_date)) as active_months,
        count(distinct o.customer_type) as customer_types_count
    from {{ ref('silver_orders') }} o
    group by o.product_id
),

product_inventory as (
    select 
        i.product_id,
        count(distinct i.pharmacy_id) as pharmacies_stocking,
        sum(i.current_stock) as total_stock_across_pharmacies,
        sum(i.current_stock * i.cost_per_unit) as total_inventory_value,
        avg(i.current_stock) as avg_stock_per_pharmacy,
        avg(i.stock_percentage) as avg_stock_percentage,
        count(case when i.reorder_alert then 1 end) as pharmacies_needing_reorder,
        count(case when i.expiry_alert then 1 end) as pharmacies_with_expiring_stock,
        avg(i.days_until_expiry) as avg_days_until_expiry
    from {{ ref('silver_inventory') }} i
    group by i.product_id
)

select 
    p.product_id,
    p.product_name,
    p.generic_name,
    p.category,
    p.manufacturer,
    p.supplier,
    p.regulatory_class,
    p.price_tier,
    p.storage_classification,
    p.unit_price,
    p.wholesale_price,
    p.retail_price,
    p.profit_margin,
    p.profit_margin_percentage,
    p.is_prescription,
    p.is_controlled_substance,
    p.requires_cold_chain,
    p.expiry_months,
    p.minimum_order_quantity,
    p.lead_time_days,
    
    -- Order performance metrics
    coalesce(po.total_orders, 0) as total_orders,
    coalesce(po.unique_customers, 0) as unique_customers,
    coalesce(po.total_quantity_sold, 0) as total_quantity_sold,
    coalesce(po.total_revenue, 0) as total_revenue,
    coalesce(po.total_discounted_revenue, 0) as total_discounted_revenue,
    coalesce(po.avg_quantity_per_order, 0) as avg_quantity_per_order,
    coalesce(po.avg_order_value, 0) as avg_order_value,
    coalesce(po.avg_discount_rate, 0) as avg_discount_rate,
    coalesce(po.active_months, 0) as active_months,
    coalesce(po.customer_types_count, 0) as customer_types_count,
    
    -- Inventory performance metrics
    coalesce(pi.pharmacies_stocking, 0) as pharmacies_stocking,
    coalesce(pi.total_stock_across_pharmacies, 0) as total_stock_across_pharmacies,
    coalesce(pi.total_inventory_value, 0) as total_inventory_value,
    coalesce(pi.avg_stock_per_pharmacy, 0) as avg_stock_per_pharmacy,
    coalesce(pi.avg_stock_percentage, 0) as avg_stock_percentage,
    coalesce(pi.pharmacies_needing_reorder, 0) as pharmacies_needing_reorder,
    coalesce(pi.pharmacies_with_expiring_stock, 0) as pharmacies_with_expiring_stock,
    coalesce(pi.avg_days_until_expiry, 0) as avg_days_until_expiry,
    
    -- Calculated KPIs
    case 
        when po.total_orders > 0 then round(po.total_revenue / po.total_orders, 2)
        else 0
    end as revenue_per_order,
    
    case 
        when po.unique_customers > 0 then round(po.total_orders / po.unique_customers, 2)
        else 0
    end as orders_per_customer,
    
    case 
        when po.total_quantity_sold > 0 then round(po.total_revenue / po.total_quantity_sold, 2)
        else 0
    end as revenue_per_unit_sold,
    
    case 
        when pi.pharmacies_stocking > 0 then round(pi.pharmacies_needing_reorder / pi.pharmacies_stocking * 100, 2)
        else 0
    end as reorder_percentage,
    
    case 
        when pi.pharmacies_stocking > 0 then round(pi.pharmacies_with_expiring_stock / pi.pharmacies_stocking * 100, 2)
        else 0
    end as expiry_risk_percentage,
    
    -- Performance classifications
    case 
        when po.total_revenue >= 50000 then 'High Revenue'
        when po.total_revenue >= 10000 then 'Medium Revenue'
        when po.total_revenue > 0 then 'Low Revenue'
        else 'No Sales'
    end as revenue_tier,
    
    case 
        when po.total_orders >= 100 then 'High Volume'
        when po.total_orders >= 20 then 'Medium Volume'
        when po.total_orders > 0 then 'Low Volume'
        else 'No Orders'
    end as volume_tier,
    
    case 
        when pi.pharmacies_stocking >= 50 then 'Widely Stocked'
        when pi.pharmacies_stocking >= 10 then 'Moderately Stocked'
        when pi.pharmacies_stocking > 0 then 'Limited Stock'
        else 'Not Stocked'
    end as distribution_tier,
    
    case 
        when p.profit_margin_percentage >= 50 then 'High Margin'
        when p.profit_margin_percentage >= 25 then 'Medium Margin'
        when p.profit_margin_percentage > 0 then 'Low Margin'
        else 'No Margin Data'
    end as margin_tier,
    
    -- Demand patterns
    case 
        when po.total_orders > 0 and po.active_months > 0 then round(po.total_orders / po.active_months, 2)
        else 0
    end as avg_orders_per_month,
    
    case 
        when po.total_quantity_sold > 0 and po.active_months > 0 then round(po.total_quantity_sold / po.active_months, 2)
        else 0
    end as avg_quantity_per_month,
    
    -- Metadata
    {{ current_timestamp_expr() }} as gold_processed_at,
    'gold_product_performance' as gold_model_name

from {{ ref('silver_products') }} p
left join product_orders po on p.product_id = po.product_id
left join product_inventory pi on p.product_id = pi.product_id
