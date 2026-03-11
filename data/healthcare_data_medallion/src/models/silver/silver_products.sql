{{
  config(
    materialized='table',
    schema='silver',
    tags=['silver', 'business_logic']
  )
}}

-- Silver layer: Cleaned and validated products data
-- This model applies business logic, data quality checks, and standardization
-- Focus: Data quality, business rules, standardized naming

with product_cleaned as (
    select
        product_id,
        
        -- Standardized naming
        trim(upper(product_name)) as product_name,
        trim(upper(generic_name)) as generic_name,
        trim(upper(category)) as category,
        trim(upper(manufacturer)) as manufacturer,
        trim(upper(supplier)) as supplier,
        
        -- Regulatory codes
        pbs_code,
        atc_code,
        
        -- Pricing (standardized to 2 decimal places)
        round(unit_price, 2) as unit_price,
        round(wholesale_price, 2) as wholesale_price,
        round(retail_price, 2) as retail_price,
        
        -- Product attributes
        is_prescription,
        is_controlled_substance,
        requires_cold_chain,
        trim(upper(storage_type)) as storage_type,
        
        -- Inventory management
        expiry_months,
        batch_size,
        minimum_order_quantity,
        lead_time_days,
        
        -- Product details
        active_ingredient,
        dosage_form,
        pack_size,
        supplier_id,
        therapeutic_category,
        brand,
        generic_equivalent_id,
        pack_size_variants,
        margin_percentage,

        -- Dates
        created_date,
        last_updated,
        {{ datediff_days('created_date', 'current_date()') }} as days_since_created,
        
        -- Data quality flags
        case 
            when unit_price < 0 then true
            else false
        end as has_negative_unit_price,
        
        case 
            when wholesale_price < 0 then true
            else false
        end as has_negative_wholesale_price,
        
        case 
            when retail_price < 0 then true
            else false
        end as has_negative_retail_price,
        
        case 
            when expiry_months < 0 then true
            else false
        end as has_negative_expiry_months,
        
        case 
            when days_since_created < 0 then true
            else false
        end as has_future_created_date,
        
        -- Business classifications
        case 
            when unit_price >= 200 then 'High Value'
            when unit_price >= 50 then 'Medium Value'
            else 'Low Value'
        end as price_tier,
        
        case 
            when is_prescription and is_controlled_substance then 'Controlled Prescription'
            when is_prescription then 'Prescription Only'
            else 'Over the Counter'
        end as regulatory_class,
        
        case 
            when requires_cold_chain then 'Cold Chain Required'
            when storage_type like '%Frozen%' then 'Frozen Storage'
            when storage_type like '%Refrigerated%' then 'Refrigerated Storage'
            else 'Room Temperature'
        end as storage_classification,
        
        -- Profitability metrics
        round(retail_price - wholesale_price, 2) as profit_margin,
        round((retail_price - wholesale_price) / retail_price * 100, 2) as profit_margin_percentage,
        
        -- Metadata
        _ingestion_timestamp,
        _source,
        _batch_id,
        bronze_processed_at,
        {{ current_timestamp_expr() }} as silver_processed_at,
        'silver_products' as silver_model_name
        
    from {{ ref('bronze_products') }}
)

select *
from product_cleaned
where 
    -- Data quality filters
    not has_negative_unit_price
    and not has_negative_wholesale_price
    and not has_negative_retail_price
    and not has_negative_expiry_months
    and not has_future_created_date
    and product_name is not null
    and category is not null
