-- Commandes Olist : une ligne par commande, avec des types corrects.
with source as (
    -- Les lignes brutes (run_date, extracted_at, source, record JSON)
    select * from {{ raw_table('retail_raw', 'olist_orders') }}
),

renamed as (
    select
        {{ json_text('order_id') }}                                      as order_id,
        {{ json_text('customer_id') }}                                   as customer_id,
        {{ json_text('order_status') }}                                  as order_status,
        -- Les dates arrivent en texte "2017-11-24 10:15:32" : on les convertit
        cast({{ json_text('order_purchase_timestamp') }} as timestamp)      as purchased_at,
        cast({{ json_text('order_approved_at') }} as timestamp)             as approved_at,
        cast({{ json_text('order_delivered_carrier_date') }} as timestamp)  as delivered_carrier_at,
        cast({{ json_text('order_delivered_customer_date') }} as timestamp) as delivered_customer_at,
        -- La date de livraison estimée n'a pas d'heure utile : on garde la date seule
        cast(cast({{ json_text('order_estimated_delivery_date') }} as timestamp) as date) as estimated_delivery_date,
        run_date,
        extracted_at
    from source
),

ranked as (
    -- Si une journée a été rejouée plusieurs fois, on garde l'extraction la plus récente.
    -- row_number numérote les lignes de chaque commande, de la plus récente à la plus ancienne.
    select
        *,
        row_number() over (partition by order_id order by extracted_at desc) as row_num
    from renamed
)

select
    order_id, customer_id, order_status,
    purchased_at,
    cast(purchased_at as date) as order_date,   -- le jour d'achat, clé du calendrier
    approved_at, delivered_carrier_at, delivered_customer_at, estimated_delivery_date,
    run_date
from ranked
where row_num = 1
