{{
  config(
    materialized='table',
    schema='silver',
    tags=['silver', 'business_logic']
  )
}}

-- Silver layer: Cleaned and validated hospital data
-- This model applies business logic, data quality checks, and standardization
-- Focus: Data quality, business rules, standardized naming

with hospital_cleaned as (
    select
        hospital_id,

        -- Standardized naming
        trim(upper(hospital_name)) as hospital_name,
        trim(upper(hospital_type)) as hospital_type,

        -- Address standardization
        trim(upper(address)) as address,
        trim(upper(suburb)) as suburb,
        trim(upper(state)) as state,
        {{ trim_cast('postcode') }} as postcode,

        -- Contact information
        phone,
        lower(trim(email)) as email,
        license_number,

        -- Capacity metrics
        beds,
        emergency_department,
        icu_beds,
        specialties,

        -- Dates
        accreditation_date,
        {{ datediff_days('accreditation_date', 'current_date()') }} / 365 as years_accredited,

        -- Financial metrics
        monthly_budget,

        -- Procurement contacts
        procurement_contact,
        lower(trim(procurement_email)) as procurement_email,

        -- Data quality flags
        case
            when beds < 0 then true
            else false
        end as has_negative_beds,

        case
            when icu_beds < 0 then true
            else false
        end as has_negative_icu_beds,

        case
            when monthly_budget < 0 then true
            else false
        end as has_negative_budget,

        case
            when years_accredited < 0 then true
            else false
        end as has_future_accreditation_date,

        -- Business classifications
        case
            when beds >= 500 then 'Large Hospital'
            when beds >= 200 then 'Medium Hospital'
            when beds >= 50 then 'Small Hospital'
            else 'Very Small Hospital'
        end as hospital_size_tier,

        case
            when monthly_budget >= 5000000 then 'High Budget'
            when monthly_budget >= 2000000 then 'Medium Budget'
            else 'Low Budget'
        end as budget_tier,

        -- Service capabilities
        case
            when emergency_department and icu_beds > 0 then 'Full Service'
            when emergency_department then 'Emergency Only'
            when icu_beds > 0 then 'ICU Only'
            else 'Basic Service'
        end as service_level,

        -- Metadata
        _ingestion_timestamp,
        _source,
        _batch_id,
        bronze_processed_at,
        {{ current_timestamp_expr() }} as silver_processed_at,
        'silver_hospitals' as silver_model_name

    from {{ ref('bronze_hospitals') }}
)

select *
from hospital_cleaned
where
    -- Data quality filters
    not has_negative_beds
    and not has_negative_icu_beds
    and not has_negative_budget
    and not has_future_accreditation_date
    and hospital_name is not null
    and state is not null
