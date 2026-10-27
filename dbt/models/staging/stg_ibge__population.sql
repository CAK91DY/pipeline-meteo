-- Population estimée par État et par année.
-- Source : le fichier versionné seeds/ibge_population.csv (voir seeds/_seeds.yml).
select
    cast(state_code as {{ dbt.type_string() }})      as state_code,
    cast(population_year as {{ dbt.type_int() }})    as population_year,
    cast(population as {{ dbt.type_int() }})         as population
from {{ ref('ibge_population') }}
