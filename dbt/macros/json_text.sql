{#-
  Extrait un champ texte de la colonne JSON "record".
  Exemple : {{ json_text('order_id') }} ou {{ json_text('rates.EUR') }} pour un champ imbriqué.
  Olist écrit les valeurs manquantes sous forme de texte vide : nullif les transforme en NULL.
  Seule la fonction d'extraction diffère entre DuckDB et BigQuery.
-#}
{% macro json_text(path) -%}
    {{ return(adapter.dispatch('json_text')(path)) }}
{%- endmacro %}

{% macro default__json_text(path) -%}
    nullif(json_value(record, '$.{{ path }}'), '')
{%- endmacro %}

{% macro duckdb__json_text(path) -%}
    nullif(json_extract_string(record, '$.{{ path }}'), '')
{%- endmacro %}


{#-
  Conversion en entier qui renvoie NULL au lieu d'échouer sur une valeur non numérique
  (ex. "..." dans les tableaux de l'IBGE) : try_cast en DuckDB, safe_cast en BigQuery.
-#}
{% macro try_cast_int(expression) -%}
    {{ return(adapter.dispatch('try_cast_int')(expression)) }}
{%- endmacro %}

{% macro default__try_cast_int(expression) -%}
    safe_cast({{ expression }} as int64)
{%- endmacro %}

{% macro duckdb__try_cast_int(expression) -%}
    try_cast({{ expression }} as bigint)
{%- endmacro %}
