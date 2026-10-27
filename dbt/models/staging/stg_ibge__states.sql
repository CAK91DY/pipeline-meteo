-- États brésiliens : code IBGE, sigle (la clé utilisée par Olist), nom et région.
-- Source : le fichier versionné seeds/ibge_states.csv (voir seeds/_seeds.yml).
select
    cast(state_code as {{ dbt.type_string() }}) as state_code,    -- ex. "35"
    state_abbr,                                                  -- ex. "SP"
    state_name,                                                  -- ex. "São Paulo"
    region_name                                                  -- ex. "Sudeste"
from {{ ref('ibge_states') }}
