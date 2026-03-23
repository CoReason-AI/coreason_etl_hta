{% macro clean_text(column_name) %}
    trim(regexp_replace({{ column_name }}, '[\n\r]+|<[^>]*>', ' ', 'g'))
{% endmacro %}
