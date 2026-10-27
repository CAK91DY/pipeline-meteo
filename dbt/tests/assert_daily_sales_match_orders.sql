-- Test de cohérence : le chiffre d'affaires quotidien doit être égal, au centime près,
-- à la somme des commandes valides de la même période. Le test échoue s'il renvoie une ligne.
with from_daily as (
    select sum(revenue_brl) as revenue from {{ ref('fct_daily_sales') }}
),

from_orders as (
    select sum(revenue_brl) as revenue
    from {{ ref('fct_orders') }}
    where is_valid
      and order_date between date '{{ var("analysis_start") }}' and date '{{ var("analysis_end") }}'
)

select from_daily.revenue as daily_revenue, from_orders.revenue as orders_revenue
from from_daily
cross join from_orders
where abs(from_daily.revenue - from_orders.revenue) > 0.01
