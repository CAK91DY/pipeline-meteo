-- Population estimée par État et par année (format de l'API SIDRA de l'IBGE).
-- D1C = code de l'État, D3C = année, V = valeur.
with source as (
    select * from {{ raw_table('retail_raw', 'ibge_population') }}
),

latest as (
    select * from source
    where run_date = (select max(run_date) from source)
),

renamed as (
    select
        {{ json_text('D1C') }}                                              as state_code,
        cast({{ json_text('D3C') }} as {{ dbt.type_int() }})                 as population_year,
        -- SIDRA écrit "..." ou "-" quand la valeur n'existe pas :
        -- try_cast_int renvoie NULL au lieu de faire échouer la requête (macro du projet).
        {{ try_cast_int(json_text('V')) }}                                   as population
    from latest
),

ranked as (
    select
        *,
        row_number() over (partition by state_code, population_year order by population desc) as row_num
    from renamed
)

select state_code, population_year, population
from ranked
where row_num = 1
