{#- Fonctions de calendrier dont l'écriture diffère entre DuckDB et BigQuery. -#}

{#- Une ligne par jour entre deux dates incluses, dans une colonne date_day. -#}
{% macro date_series(start_date, end_date) -%}
    {{ return(adapter.dispatch('date_series')(start_date, end_date)) }}
{%- endmacro %}

{% macro default__date_series(start_date, end_date) -%}
    select date_day
    from unnest(generate_date_array(date '{{ start_date }}', date '{{ end_date }}')) as date_day
{%- endmacro %}

{% macro duckdb__date_series(start_date, end_date) -%}
    select cast(range as date) as date_day
    from range(date '{{ start_date }}', date '{{ end_date }}' + interval 1 day, interval 1 day)
{%- endmacro %}


{#- Jour de la semaine au format ISO : 1 = lundi ... 7 = dimanche. -#}
{% macro iso_weekday(column) -%}
    {{ return(adapter.dispatch('iso_weekday')(column)) }}
{%- endmacro %}

{% macro default__iso_weekday(column) -%}
    {#- BigQuery numérote 1 = dimanche ... 7 = samedi : on décale d'un jour -#}
    mod(extract(dayofweek from {{ column }}) + 5, 7) + 1
{%- endmacro %}

{% macro duckdb__iso_weekday(column) -%}
    isodow({{ column }})
{%- endmacro %}
