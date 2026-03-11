{{
  config(
    materialized='table',
    schema='gold',
    tags=['gold', 'analytics', 'financial_analytics']
  )
}}

-- Gold layer: Financial Analytics - Revenue, Discounts, and Profitability Metrics
-- This model provides comprehensive financial performance analytics
-- Focus: Revenue analysis, discount optimization, profitability tracking

with monthly_financials as (
    select
        date_trunc('month', o.order_date) as order_month,
        o.customer_type,
        p.category as product_category,
        p.price_tier as product_price_tier,

        -- Order metrics
        count(distinct o.order_id) as total_orders,
        count(distinct o.customer_id) as unique_customers,
        count(distinct o.product_id) as unique_products,
        sum(o.quantity) as total_quantity,

        -- Revenue metrics
        sum(o.total_amount) as gross_revenue,
        sum(o.discounted_amount) as net_revenue,
        sum(o.total_amount - o.discounted_amount) as total_discount_amount,
        avg(o.total_amount) as avg_gross_order_value,
        avg(o.discounted_amount) as avg_net_order_value,
        avg(o.discount_rate) as avg_discount_rate,

        -- Volume metrics
        avg(o.quantity) as avg_quantity_per_order,
        sum(case when o.volume_tier = 'HIGH VOLUME' then o.quantity else 0 end) as high_volume_quantity,
        sum(case when o.volume_tier = 'MEDIUM VOLUME' then o.quantity else 0 end) as medium_volume_quantity,
        sum(case when o.volume_tier = 'LOW VOLUME' then o.quantity else 0 end) as low_volume_quantity,

        -- Discount analysis
        count(case when o.discount_rate > 0 then 1 end) as discounted_orders,
        sum(case when o.discount_rate > 0 then o.total_amount else 0 end) as discounted_order_value,
        avg(case when o.discount_rate > 0 then o.discount_rate end) as avg_discount_rate_when_discounted
    from {{ ref('silver_orders') }} o
    left join {{ ref('silver_products') }} p on o.product_id = p.product_id
    group by
        date_trunc('month', o.order_date),
        o.customer_type,
        p.category,
        p.price_tier
),

customer_financials as (
    select
        o.customer_id,
        o.customer_type,
        count(distinct o.order_id) as total_orders,
        sum(o.total_amount) as lifetime_gross_revenue,
        sum(o.discounted_amount) as lifetime_net_revenue,
        sum(o.total_amount - o.discounted_amount) as lifetime_discount_amount,
        avg(o.total_amount) as avg_order_value,
        avg(o.discount_rate) as avg_discount_rate,
        min(o.order_date) as first_order_date,
        max(o.order_date) as last_order_date,
        count(distinct date_trunc('month', o.order_date)) as active_months,

        -- Customer value analysis
        case
            when sum(o.total_amount) >= 100000 then 'High Value'
            when sum(o.total_amount) >= 50000 then 'Medium Value'
            when sum(o.total_amount) >= 10000 then 'Low Value'
            else 'Minimal Value'
        end as customer_value_tier,

        -- Discount behavior analysis
        case
            when avg(o.discount_rate) >= 0.1 then 'High Discount User'
            when avg(o.discount_rate) >= 0.05 then 'Medium Discount User'
            when avg(o.discount_rate) > 0 then 'Low Discount User'
            else 'No Discount User'
        end as discount_behavior_tier
    from {{ ref('silver_orders') }} o
    group by o.customer_id, o.customer_type
),

product_financials as (
    select
        p.product_id,
        p.product_name,
        p.category,
        p.price_tier,
        p.unit_price,
        p.wholesale_price,
        p.retail_price,
        p.profit_margin,
        p.profit_margin_percentage,

        -- Sales metrics
        count(distinct o.order_id) as total_orders,
        count(distinct o.customer_id) as unique_customers,
        sum(o.quantity) as total_quantity_sold,
        sum(o.total_amount) as gross_revenue,
        sum(o.discounted_amount) as net_revenue,
        sum(o.total_amount - o.discounted_amount) as total_discount_amount,
        avg(o.discount_rate) as avg_discount_rate,

        -- Profitability analysis
        sum(o.quantity * p.profit_margin) as total_profit,
        avg(o.quantity * p.profit_margin) as avg_profit_per_order,

        -- Performance metrics
        case
            when sum(o.total_amount) >= 50000 then 'High Revenue'
            when sum(o.total_amount) >= 10000 then 'Medium Revenue'
            when sum(o.total_amount) > 0 then 'Low Revenue'
            else 'No Sales'
        end as revenue_tier,

        case
            when avg(o.discount_rate) >= 0.1 then 'High Discount'
            when avg(o.discount_rate) >= 0.05 then 'Medium Discount'
            when avg(o.discount_rate) > 0 then 'Low Discount'
            else 'No Discount'
        end as discount_tier
    from {{ ref('silver_products') }} p
    left join {{ ref('silver_orders') }} o on p.product_id = o.product_id
    group by
        p.product_id, p.product_name, p.category, p.price_tier,
        p.unit_price, p.wholesale_price, p.retail_price,
        p.profit_margin, p.profit_margin_percentage
)

select
    -- Monthly financial summary
    mf.order_month,
    mf.customer_type,
    mf.product_category,
    mf.product_price_tier,

    -- Order metrics
    mf.total_orders,
    mf.unique_customers,
    mf.unique_products,
    mf.total_quantity,

    -- Revenue metrics
    mf.gross_revenue,
    mf.net_revenue,
    mf.total_discount_amount,
    mf.avg_gross_order_value,
    mf.avg_net_order_value,
    mf.avg_discount_rate,

    -- Volume distribution
    mf.high_volume_quantity,
    mf.medium_volume_quantity,
    mf.low_volume_quantity,

    -- Discount analysis
    mf.discounted_orders,
    mf.discounted_order_value,
    mf.avg_discount_rate_when_discounted,

    -- Calculated KPIs
    case
        when mf.total_orders > 0 then round(mf.discounted_orders / mf.total_orders * 100, 2)
        else 0
    end as discount_percentage,

    case
        when mf.gross_revenue > 0 then round(mf.total_discount_amount / mf.gross_revenue * 100, 2)
        else 0
    end as discount_impact_percentage,

    case
        when mf.total_quantity > 0 then round(mf.gross_revenue / mf.total_quantity, 2)
        else 0
    end as revenue_per_unit,

    case
        when mf.unique_customers > 0 then round(mf.gross_revenue / mf.unique_customers, 2)
        else 0
    end as revenue_per_customer,

    -- Performance classifications
    case
        when mf.gross_revenue >= 100000 then 'High Revenue Month'
        when mf.gross_revenue >= 50000 then 'Medium Revenue Month'
        when mf.gross_revenue >= 10000 then 'Low Revenue Month'
        else 'Minimal Revenue Month'
    end as monthly_revenue_tier,

    case
        when mf.avg_discount_rate >= 0.1 then 'High Discount Month'
        when mf.avg_discount_rate >= 0.05 then 'Medium Discount Month'
        when mf.avg_discount_rate > 0 then 'Low Discount Month'
        else 'No Discount Month'
    end as monthly_discount_tier,

    -- Metadata
    {{ current_timestamp_expr() }} as gold_processed_at,
    'gold_financial_analytics' as gold_model_name

from monthly_financials mf
