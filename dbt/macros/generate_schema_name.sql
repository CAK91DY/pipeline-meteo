{#-
  Nom des schémas créés par dbt.
  Par défaut, dbt préfixe le schéma personnalisé par celui du profil ("main_staging").
  On garde le nom court ("staging", "marts") : plus lisible dans les tableaux de bord.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
