-- États brésiliens : code IBGE, sigle (la clé utilisée par Olist), nom et région.
with source as (
    select * from {{ raw_table('retail_raw', 'ibge_states') }}
),

latest as (
    select * from source
    where run_date = (select max(run_date) from source)
)

select
    {{ json_text('id') }}           as state_code,    -- ex. "35"
    {{ json_text('sigla') }}        as state_abbr,    -- ex. "SP"
    {{ json_text('nome') }}         as state_name,    -- ex. "São Paulo"
    {{ json_text('regiao.nome') }}  as region_name    -- ex. "Sudeste" (champ imbriqué)
from latest
