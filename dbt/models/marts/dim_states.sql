-- États brésiliens, avec leur région et leur population (pour les indicateurs par habitant).
select
    states.state_abbr,
    states.state_code,
    states.state_name,
    states.region_name,
    population.population
from {{ ref('stg_ibge__states') }} as states
left join {{ ref('stg_ibge__population') }} as population
    on states.state_code = population.state_code
    and population.population_year = {{ var('population_year') }}
