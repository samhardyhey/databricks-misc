{{
  config(
    materialized='table',
    schema='silver',
    tags=['silver', 'business_logic']
  )
}}

-- Silver layer: Cleaned and validated pharmacy data
-- This model applies business logic, data quality checks, and standardization
-- Focus: Data quality, business rules, standardized naming

with pharmacy_cleaned as (
    select
        pharmacy_id,
        
        -- Standardized naming
        trim(upper(pharmacy_name)) as pharmacy_name,
        case 
            when is_chain then 'Chain'
            else 'Independent'
        end as pharmacy_type,
        
        -- Address standardization
        trim(upper(address)) as address,
        trim(upper(suburb)) as suburb,
        trim(upper(state)) as state,
        {{ trim_cast('postcode') }} as postcode,
        
        -- Contact information
        phone,
        lower(trim(email)) as email,
        license_number,
        
        -- Dates
        established_date,
        {{ datediff_days('established_date', 'current_date()') }} / 365 as years_in_operation,
        
        -- Services
        pharmacist_in_charge,
        trading_hours,
        has_consultation_room,
        has_vaccination_service,
        
        -- Financial metrics
        monthly_revenue,
        customer_count,
        
        -- Data quality flags
        case 
            when monthly_revenue < 0 then true
            else false
        end as has_negative_revenue,
        
        case 
            when customer_count < 0 then true
            else false
        end as has_negative_customers,
        
        case 
            when years_in_operation < 0 then true
            else false
        end as has_future_establishment_date,
        
        -- Business classifications
        case 
            when monthly_revenue >= 300000 then 'High Revenue'
            when monthly_revenue >= 150000 then 'Medium Revenue'
            else 'Low Revenue'
        end as revenue_tier,
        
        case 
            when customer_count >= 3000 then 'High Volume'
            when customer_count >= 1500 then 'Medium Volume'
            else 'Low Volume'
        end as customer_volume_tier,
        
        -- Metadata
        _ingestion_timestamp,
        _source,
        _batch_id,
        bronze_processed_at,
        {{ current_timestamp_expr() }} as silver_processed_at,
        'silver_pharmacies' as silver_model_name
        
    from {{ ref('bronze_pharmacies') }}
)

select *
from pharmacy_cleaned
where 
    -- Data quality filters
    not has_negative_revenue
    and not has_negative_customers
    and not has_future_establishment_date
    and pharmacy_name is not null
    and state is not null
