-- Une ligne par commande : la table centrale des tableaux de bord.
-- Règles issues de l'exploration (notebooks/01_exploration_olist.ipynb, section 9) :
--   - chiffre d'affaires = somme des prix des articles, frais de port à part ;
--   - les commandes annulées ou indisponibles ne comptent pas dans le chiffre d'affaires ;
--   - une seule note par commande : l'avis le plus récent.

with orders as (
    select * from {{ ref('stg_olist__orders') }}
),

items as (
    -- Totaux par commande à partir des articles
    select
        order_id,
        count(*)          as n_items,
        sum(price_brl)    as revenue_brl,
        sum(freight_brl)  as freight_brl
    from {{ ref('stg_olist__order_items') }}
    group by order_id
),

payments as (
    select
        order_id,
        sum(payment_value_brl)     as payment_total_brl,
        max(payment_installments)  as max_installments
    from {{ ref('stg_olist__order_payments') }}
    group by order_id
),

latest_review as (
    -- L'avis le plus récent de chaque commande
    select order_id, review_score
    from (
        select
            order_id,
            review_score,
            row_number() over (partition by order_id order by review_answered_at desc, review_id) as row_num
        from {{ ref('stg_olist__order_reviews') }}
    ) as ranked
    where row_num = 1
),

customers as (
    select customer_id, customer_unique_id, customer_state
    from {{ ref('stg_olist__customers') }}
),

fx as (
    select rate_date, eur_per_brl, usd_per_brl
    from {{ ref('stg_frankfurter__fx_rates') }}
)

select
    orders.order_id,
    orders.customer_id,
    customers.customer_unique_id,
    customers.customer_state,
    orders.order_status,
    orders.order_status not in ('canceled', 'unavailable')              as is_valid,
    orders.purchased_at,
    orders.order_date,
    orders.delivered_customer_at,
    orders.estimated_delivery_date,

    -- Montants. Une commande sans article a un chiffre d'affaires nul (et non inconnu).
    coalesce(items.n_items, 0)                                          as n_items,
    coalesce(items.revenue_brl, 0)                                      as revenue_brl,
    coalesce(items.freight_brl, 0)                                      as freight_brl,
    payments.payment_total_brl,
    payments.max_installments,

    -- Conversion au taux du jour d'achat
    fx.eur_per_brl,
    coalesce(items.revenue_brl, 0) * fx.eur_per_brl                     as revenue_eur,
    coalesce(items.revenue_brl, 0) * fx.usd_per_brl                     as revenue_usd,

    -- Livraison : délai en jours et retard par rapport à la date annoncée au client
    {{ dbt.datediff('orders.order_date', 'cast(orders.delivered_customer_at as date)', 'day') }} as delivery_days,
    case
        when orders.delivered_customer_at is null then null             -- pas encore livrée : on ne sait pas
        else cast(orders.delivered_customer_at as date) > orders.estimated_delivery_date
    end                                                                 as is_late,

    latest_review.review_score
from orders
left join items         on orders.order_id = items.order_id
left join payments      on orders.order_id = payments.order_id
left join latest_review on orders.order_id = latest_review.order_id
left join customers     on orders.customer_id = customers.customer_id
left join fx            on orders.order_date = fx.rate_date
