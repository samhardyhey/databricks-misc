{{
  config(
    materialized='table',
    schema='gold',
    tags=['gold', 'analytics', 'ml_ready']
  )
}}

-- Gold layer: ML-Ready Dataset - Feature Engineered Data for Machine Learning
-- This model provides feature-engineered datasets optimized for ML use cases
-- Focus: Feature engineering, ML-ready data, predictive analytics

with customer_features as (
    select 
        o.customer_id,
        o.customer_type,
        
        -- Basic features
        count(distinct o.order_id) as total_orders,
        count(distinct o.product_id) as unique_products_ordered,
        sum(o.quantity) as total_quantity_ordered,
        sum(o.total_amount) as total_order_value,
        sum(o.discounted_amount) as total_discounted_value,
        avg(o.total_amount) as avg_order_value,
        avg(o.discount_rate) as avg_discount_rate,
        min(o.order_date) as first_order_date,
        max(o.order_date) as last_order_date,
        
        -- Temporal features
        datediff(current_date(), min(o.order_date)) as customer_age_days,
        datediff(current_date(), max(o.order_date)) as days_since_last_order,
        count(distinct date_trunc('month', o.order_date)) as active_months,
        
        -- Behavioral features
        count(case when o.volume_tier = 'HIGH VOLUME' then 1 end) as high_volume_orders,
        count(case when o.volume_tier = 'MEDIUM VOLUME' then 1 end) as medium_volume_orders,
        count(case when o.volume_tier = 'LOW VOLUME' then 1 end) as low_volume_orders,
        count(case when o.order_value_tier = 'HIGH VALUE' then 1 end) as high_value_orders,
        count(case when o.order_value_tier = 'MEDIUM VALUE' then 1 end) as medium_value_orders,
        count(case when o.order_value_tier = 'LOW VALUE' then 1 end) as low_value_orders,
        
        -- Discount behavior
        count(case when o.discount_rate > 0 then 1 end) as discounted_orders,
        avg(case when o.discount_rate > 0 then o.discount_rate end) as avg_discount_when_discounted,
        
        -- Order frequency
        case 
            when count(distinct o.order_id) > 0 then 
                count(distinct o.order_id) / nullif(count(distinct date_trunc('month', o.order_date)), 0)
            else 0
        end as orders_per_month,
        
        -- Customer value score
        case 
            when sum(o.total_amount) >= 100000 then 5
            when sum(o.total_amount) >= 50000 then 4
            when sum(o.total_amount) >= 20000 then 3
            when sum(o.total_amount) >= 5000 then 2
            else 1
        end as customer_value_score
        
    from {{ ref('silver_orders') }} o
    group by o.customer_id, o.customer_type
),

product_features as (
    select 
        p.product_id,
        p.product_name,
        p.category,
        p.price_tier,
        p.regulatory_class,
        p.storage_classification,
        p.unit_price,
        p.profit_margin_percentage,
        p.is_prescription,
        p.is_controlled_substance,
        p.requires_cold_chain,
        p.expiry_months,
        p.minimum_order_quantity,
        p.lead_time_days,
        
        -- Sales features
        count(distinct o.order_id) as total_orders,
        count(distinct o.customer_id) as unique_customers,
        sum(o.quantity) as total_quantity_sold,
        sum(o.total_amount) as total_revenue,
        avg(o.quantity) as avg_quantity_per_order,
        avg(o.total_amount) as avg_order_value,
        avg(o.discount_rate) as avg_discount_rate,
        
        -- Temporal features
        min(o.order_date) as first_sale_date,
        max(o.order_date) as last_sale_date,
        count(distinct date_trunc('month', o.order_date)) as active_sale_months,
        
        -- Demand patterns
        count(case when o.volume_tier = 'HIGH VOLUME' then 1 end) as high_volume_orders,
        count(case when o.volume_tier = 'MEDIUM VOLUME' then 1 end) as medium_volume_orders,
        count(case when o.volume_tier = 'LOW VOLUME' then 1 end) as low_volume_orders,
        
        -- Product performance score
        case 
            when sum(o.total_amount) >= 50000 then 5
            when sum(o.total_amount) >= 20000 then 4
            when sum(o.total_amount) >= 5000 then 3
            when sum(o.total_amount) >= 1000 then 2
            else 1
        end as product_performance_score
        
    from {{ ref('silver_products') }} p
    left join {{ ref('silver_orders') }} o on p.product_id = o.product_id
    group by 
        p.product_id, p.product_name, p.category, p.price_tier,
        p.regulatory_class, p.storage_classification, p.unit_price,
        p.profit_margin_percentage, p.is_prescription, p.is_controlled_substance,
        p.requires_cold_chain, p.expiry_months, p.minimum_order_quantity, p.lead_time_days
),

inventory_features as (
    select 
        i.pharmacy_id,
        i.product_id,
        i.current_stock,
        i.reorder_level,
        i.max_stock,
        i.stock_percentage,
        i.stock_to_reorder_ratio,
        i.days_until_expiry,
        i.days_since_last_restock,
        i.stock_status,
        i.expiry_status,
        i.stock_level_tier,
        i.reorder_alert,
        i.expiry_alert,
        i.low_stock_alert,
        
        -- Inventory health score
        case 
            when i.stock_percentage >= 80 and i.days_until_expiry >= 90 then 5
            when i.stock_percentage >= 60 and i.days_until_expiry >= 60 then 4
            when i.stock_percentage >= 40 and i.days_until_expiry >= 30 then 3
            when i.stock_percentage >= 20 and i.days_until_expiry >= 15 then 2
            else 1
        end as inventory_health_score
        
    from {{ ref('silver_inventory') }} i
)

select 
    -- Customer features
    cf.customer_id,
    cf.customer_type,
    cf.total_orders,
    cf.unique_products_ordered,
    cf.total_quantity_ordered,
    cf.total_order_value,
    cf.total_discounted_value,
    cf.avg_order_value,
    cf.avg_discount_rate,
    cf.customer_age_days,
    cf.days_since_last_order,
    cf.active_months,
    cf.high_volume_orders,
    cf.medium_volume_orders,
    cf.low_volume_orders,
    cf.high_value_orders,
    cf.medium_value_orders,
    cf.low_value_orders,
    cf.discounted_orders,
    cf.avg_discount_when_discounted,
    cf.orders_per_month,
    cf.customer_value_score,
    
    -- Product features
    pf.product_id,
    pf.product_name,
    pf.category,
    pf.price_tier,
    pf.regulatory_class,
    pf.storage_classification,
    pf.unit_price,
    pf.profit_margin_percentage,
    pf.is_prescription,
    pf.is_controlled_substance,
    pf.requires_cold_chain,
    pf.expiry_months,
    pf.minimum_order_quantity,
    pf.lead_time_days,
    pf.total_orders as product_total_orders,
    pf.unique_customers as product_unique_customers,
    pf.total_quantity_sold,
    pf.total_revenue,
    pf.avg_quantity_per_order,
    pf.avg_order_value as product_avg_order_value,
    pf.avg_discount_rate as product_avg_discount_rate,
    pf.active_sale_months,
    pf.high_volume_orders as product_high_volume_orders,
    pf.medium_volume_orders as product_medium_volume_orders,
    pf.low_volume_orders as product_low_volume_orders,
    pf.product_performance_score,
    
    -- Inventory features
    inf.current_stock,
    inf.reorder_level,
    inf.max_stock,
    inf.stock_percentage,
    inf.stock_to_reorder_ratio,
    inf.days_until_expiry,
    inf.days_since_last_restock,
    inf.stock_status,
    inf.expiry_status,
    inf.stock_level_tier,
    inf.reorder_alert,
    inf.expiry_alert,
    inf.low_stock_alert,
    inf.inventory_health_score,
    
    -- Derived features for ML
    case 
        when cf.days_since_last_order > 90 then 1
        else 0
    end as is_churn_risk,
    
    case 
        when inf.reorder_alert or inf.expiry_alert then 1
        else 0
    end as needs_attention,
    
    case 
        when cf.customer_value_score >= 4 and pf.product_performance_score >= 4 then 'High Value'
        when cf.customer_value_score >= 3 and pf.product_performance_score >= 3 then 'Medium Value'
        else 'Low Value'
    end as customer_product_value_tier,
    
    -- Metadata
    current_timestamp() as gold_processed_at,
    'gold_ml_ready_dataset' as gold_model_name

from customer_features cf
cross join product_features pf
left join inventory_features inf on cf.customer_id = inf.pharmacy_id and pf.product_id = inf.product_id
