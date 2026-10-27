{#-
  Lit une table brute au format commun du pipeline :
  run_date (DATE), extracted_at (TIMESTAMP), source (texte), record (JSON).

  - Sur BigQuery, la table brute a déjà ces colonnes : on la lit telle quelle.
  - En local (DuckDB), la "table" est l'ensemble des fichiers NDJSON de data/raw :
    chaque ligne arrive comme un seul objet JSON, qu'on découpe en colonnes.

  adapter.dispatch choisit automatiquement la version selon la base utilisée
  (duckdb__raw_table pour DuckDB, default__raw_table sinon).
-#}
{% macro raw_table(source_name, table_name) -%}
    {{ return(adapter.dispatch('raw_table')(source_name, table_name)) }}
{%- endmacro %}

{% macro default__raw_table(source_name, table_name) -%}
    {{ source(source_name, table_name) }}
{%- endmacro %}

{% macro duckdb__raw_table(source_name, table_name) -%}
    (
        select
            cast(json_extract_string(json, '$.run_date') as date)           as run_date,
            cast(json_extract_string(json, '$.extracted_at') as timestamptz) as extracted_at,
            json_extract_string(json, '$.source')                          as source,
            json_extract(json, '$.record')                                 as record
        from {{ source(source_name, table_name) }}
    )
{%- endmacro %}
