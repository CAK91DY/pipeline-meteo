-- Ventes par jour, sur la fenêtre d'analyse uniquement.
-- Chaque jour est présent, même sans commande (valeurs à 0) : une série temporelle continue
-- évite qu'un graphique relie deux points en sautant un jour vide.
with daily as (
    select
        order_date,
        count(*)                                as orders,
        count(distinct customer_unique_id)      as customers,
        sum(n_items)                            as items,
        sum(revenue_brl)                        as revenue_brl,
        sum(revenue_eur)                        as revenue_eur,
        sum(freight_brl)                        as freight_brl
    from {{ ref('fct_orders') }}
    where is_valid                              -- ventes réalisées uniquement
    group by order_date
),

cancelled as (
    select order_date, count(*) as cancelled_orders
    from {{ ref('fct_orders') }}
    where not is_valid
    group by order_date
)

select
    dates.date_day,
    dates.month_start,
    dates.week_start,
    dates.iso_weekday,
    dates.weekday_name,
    dates.is_weekend,
    dates.is_holiday,
    dates.holiday_name,
    dates.is_black_friday,
    coalesce(daily.orders, 0)               as orders,
    coalesce(daily.customers, 0)            as customers,
    coalesce(daily.items, 0)                as items,
    coalesce(daily.revenue_brl, 0)          as revenue_brl,
    coalesce(daily.revenue_eur, 0)          as revenue_eur,
    coalesce(daily.freight_brl, 0)          as freight_brl,
    coalesce(cancelled.cancelled_orders, 0) as cancelled_orders,
    -- Panier moyen ; nullif évite une division par zéro les jours sans commande
    daily.revenue_brl / nullif(daily.orders, 0) as avg_basket_brl
from {{ ref('dim_date') }} as dates
left join daily     on dates.date_day = daily.order_date
left join cancelled on dates.date_day = cancelled.order_date
where dates.is_in_analysis_window
