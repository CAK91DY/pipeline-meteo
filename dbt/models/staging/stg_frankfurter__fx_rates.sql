-- Taux de change : combien vaut 1 réal (BRL) en euros et en dollars, pour chaque jour.
with source as (
    select * from {{ raw_table('retail_raw', 'frankfurter_fx_rates') }}
),

renamed as (
    select
        -- Le jour demandé (y compris samedi et dimanche) : c'est la clé de jointure
        cast({{ json_text('requested_date') }} as date)                    as rate_date,
        -- Le jour où la BCE a publié ce taux (le vendredi pour un week-end)
        cast({{ json_text('date') }} as date)                              as published_date,
        cast({{ json_text('rates.EUR') }} as {{ dbt.type_float() }})       as eur_per_brl,
        cast({{ json_text('rates.USD') }} as {{ dbt.type_float() }})       as usd_per_brl,
        extracted_at
    from source
),

ranked as (
    select
        *,
        row_number() over (partition by rate_date order by extracted_at desc) as row_num
    from renamed
)

select rate_date, published_date, eur_per_brl, usd_per_brl
from ranked
where row_num = 1
