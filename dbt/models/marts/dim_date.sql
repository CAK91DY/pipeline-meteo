-- Calendrier : une ligne par jour, avec tout ce qui aide à lire la saisonnalité.
-- Les tableaux de bord filtrent sur is_in_analysis_window pour ne jamais montrer
-- les artefacts du début et de la fin du jeu Olist (voir docs/03_resultats_exploration.md).
with days as (
    {{ date_series(var('calendar_start'), var('calendar_end')) }}
),

national_holidays as (
    select holiday_date, holiday_name_pt
    from {{ ref('stg_nager__holidays') }}
    where is_national
),

calendar as (
    select
        date_day,
        extract(year from date_day)          as year,
        extract(month from date_day)         as month,
        extract(day from date_day)           as day_of_month,
        cast({{ dbt.date_trunc('month', 'date_day') }} as date) as month_start,
        {{ iso_weekday('date_day') }}        as iso_weekday      -- 1 = lundi ... 7 = dimanche
    from days
)

select
    calendar.*,
    -- Lundi de la semaine : on recule de (jour ISO - 1) jours.
    -- Écrit à la main car BigQuery fait commencer ses semaines le dimanche.
    cast({{ dbt.dateadd('day', '1 - calendar.iso_weekday', 'calendar.date_day') }} as date) as week_start,
    -- Libellé court en français, pour les axes des graphiques
    case calendar.iso_weekday
        when 1 then 'lun' when 2 then 'mar' when 3 then 'mer' when 4 then 'jeu'
        when 5 then 'ven' when 6 then 'sam' else 'dim'
    end                                                       as weekday_name,
    calendar.iso_weekday in (6, 7)                            as is_weekend,
    national_holidays.holiday_date is not null                as is_holiday,
    national_holidays.holiday_name_pt                         as holiday_name,
    -- Black Friday : le vendredi qui suit le 4e jeudi de novembre.
    -- Le 4e jeudi tombe entre le 22 et le 28 : le vendredi suivant, entre le 23 et le 29.
    (calendar.month = 11 and calendar.iso_weekday = 5
     and calendar.day_of_month between 23 and 29)             as is_black_friday,
    calendar.date_day between date '{{ var("analysis_start") }}'
                          and date '{{ var("analysis_end") }}' as is_in_analysis_window
from calendar
left join national_holidays
    on calendar.date_day = national_holidays.holiday_date
