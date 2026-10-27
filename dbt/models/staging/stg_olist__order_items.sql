-- Articles des commandes : une ligne par article d'une commande.
with source as (
    select * from {{ raw_table('retail_raw', 'olist_order_items') }}
),

renamed as (
    select
        {{ json_text('order_id') }}                                       as order_id,
        cast({{ json_text('order_item_id') }} as {{ dbt.type_int() }})     as order_item_id,
        {{ json_text('product_id') }}                                     as product_id,
        {{ json_text('seller_id') }}                                      as seller_id,
        cast({{ json_text('shipping_limit_date') }} as timestamp)          as shipping_limit_at,
        -- Montants en réais (BRL) : prix de l'article et frais de port
        cast({{ json_text('price') }} as {{ dbt.type_numeric() }})         as price_brl,
        cast({{ json_text('freight_value') }} as {{ dbt.type_numeric() }}) as freight_brl,
        extracted_at
    from source
),

ranked as (
    select
        *,
        row_number() over (partition by order_id, order_item_id order by extracted_at desc) as row_num
    from renamed
)

select
    -- Clé unique d'un article : identifiant de commande + numéro d'article
    order_id || '-' || cast(order_item_id as {{ dbt.type_string() }}) as order_item_key,
    order_id, order_item_id, product_id, seller_id, shipping_limit_at, price_brl, freight_brl
from ranked
where row_num = 1
