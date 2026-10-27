-- Jours fériés brésiliens. "global" vaut true pour un férié national,
-- false pour un férié limité à certains États (ex. São Paulo le 9 juillet).
with source as (
    select * from {{ raw_table('retail_raw', 'nager_holidays') }}
),

latest as (
    select * from source
    where run_date = (select max(run_date) from source)
),

renamed as (
    select
        cast({{ json_text('date') }} as date)           as holiday_date,
        {{ json_text('localName') }}                    as holiday_name_pt,
        {{ json_text('name') }}                         as holiday_name_en,
        cast({{ json_text('global') }} as boolean)      as is_national
    from latest
),

ranked as (
    -- Un même jour peut apparaître deux fois (deux fériés le même jour) : on en garde un.
    select
        *,
        row_number() over (partition by holiday_date, is_national order by holiday_name_pt) as row_num
    from renamed
)

select holiday_date, holiday_name_pt, holiday_name_en, is_national
from ranked
where row_num = 1
