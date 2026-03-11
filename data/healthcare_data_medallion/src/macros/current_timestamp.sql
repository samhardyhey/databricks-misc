-- Adapter-agnostic current timestamp (DuckDB uses current_localtimestamp(), Spark/Databricks use current_timestamp())
{% macro current_timestamp_expr() %}
{% if target.type == 'duckdb' %}current_localtimestamp(){% else %}current_timestamp(){% endif %}
{% endmacro %}

-- Adapter-agnostic datediff in days (DuckDB: datediff('day', start, end); Spark: datediff(end, start))
{% macro datediff_days(start_expr, end_expr) %}
{% if target.type == 'duckdb' %}datediff('day', {{ start_expr }}, {{ end_expr }}){% else %}datediff({{ end_expr }}, {{ start_expr }}){% endif %}
{% endmacro %}

-- Trim that accepts numeric (e.g. postcode): cast to varchar first for DuckDB
{% macro trim_cast(expr) %}
trim(cast({{ expr }} as varchar))
{% endmacro %}
