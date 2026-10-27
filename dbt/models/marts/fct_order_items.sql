-- Une ligne par article vendu : pour analyser les catégories, les produits et les vendeurs.
select
    items.order_item_key,
    items.order_id,
    items.order_item_id,
    items.product_id,
    products.category,
    items.seller_id,
    sellers.seller_state,
    orders.order_date,
    orders.customer_state,
    orders.is_valid,
    items.price_brl,
    items.freight_brl,
    items.price_brl * orders.eur_per_brl as price_eur
from {{ ref('stg_olist__order_items') }} as items
inner join {{ ref('fct_orders') }} as orders
    on items.order_id = orders.order_id
left join {{ ref('dim_products') }} as products
    on items.product_id = products.product_id
left join {{ ref('stg_olist__sellers') }} as sellers
    on items.seller_id = sellers.seller_id
