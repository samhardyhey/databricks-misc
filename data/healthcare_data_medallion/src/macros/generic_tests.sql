-- Custom generic tests for healthcare data models.
-- Referential integrity is wired in schema_referential_integrity.yml.

{% test unique_identifier(model, column_name) %}
  select {{ column_name }}
  from {{ model }}
  group by {{ column_name }}
  having count(*) > 1
{% endtest %}

{% test valid_date_range(model, column_name, start_date='1900-01-01', end_date='2100-12-31') %}
  select *
  from {{ model }}
  where {{ column_name }} < '{{ start_date }}' or {{ column_name }} > '{{ end_date }}'
{% endtest %}

{% test positive_value(model, column_name) %}
  select *
  from {{ model }}
  where {{ column_name }} < 0
{% endtest %}

{% test valid_percentage(model, column_name) %}
  select *
  from {{ model }}
  where {{ column_name }} < 0 or {{ column_name }} > 100
{% endtest %}

{% test valid_discount_rate(model, column_name) %}
  select *
  from {{ model }}
  where {{ column_name }} < 0 or {{ column_name }} > 1
{% endtest %}

-- Every non-null FK must exist in the parent table.
{% test referential_integrity(model, column_name, ref_model, ref_column) %}
  select {{ column_name }}
  from {{ model }}
  where {{ column_name }} is not null
    and {{ column_name }} not in (select {{ ref_column }} from {{ ref(ref_model) }})
{% endtest %}
