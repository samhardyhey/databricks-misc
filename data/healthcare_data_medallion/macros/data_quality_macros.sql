-- Macro to generate standard data quality tests
{% macro test_data_quality(model, column_name, min_value=none, max_value=none, not_null=true) %}
  {% if not_null %}
    select * from {{ model }} where {{ column_name }} is null
  {% endif %}
  
  {% if min_value is not none %}
    union all
    select * from {{ model }} where {{ column_name }} < {{ min_value }}
  {% endif %}
  
  {% if max_value is not none %}
    union all
    select * from {{ model }} where {{ column_name }} > {{ max_value }}
  {% endif %}
{% endmacro %}

-- Macro to calculate business metrics
{% macro calculate_discount_impact(gross_amount, discounted_amount) %}
  case 
    when {{ gross_amount }} > 0 then round(({{ gross_amount }} - {{ discounted_amount }}) / {{ gross_amount }} * 100, 2)
    else 0
  end
{% endmacro %}

-- Macro to classify performance tiers
{% macro classify_performance_tier(value, high_threshold, medium_threshold) %}
  case 
    when {{ value }} >= {{ high_threshold }} then 'High'
    when {{ value }} >= {{ medium_threshold }} then 'Medium'
    else 'Low'
  end
{% endmacro %}

-- Macro to generate date partitions
{% macro generate_date_partitions(start_date, end_date, partition_type='month') %}
  {% if partition_type == 'month' %}
    select date_trunc('month', date_add('{{ start_date }}', interval x month)) as partition_date
    from (select explode(sequence(0, date_diff('{{ end_date }}', '{{ start_date }}', month))) as x)
  {% elif partition_type == 'day' %}
    select date_add('{{ start_date }}', interval x day) as partition_date
    from (select explode(sequence(0, date_diff('{{ end_date }}', '{{ start_date }}', day))) as x)
  {% endif %}
{% endmacro %}
