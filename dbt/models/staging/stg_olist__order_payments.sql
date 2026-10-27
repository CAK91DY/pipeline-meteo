-- Paiements : une ligne par moyen de paiement d'une commande.
with source as (
    select * from {{ raw_table('retail_raw', 'olist_order_payments') }}
),

renamed as (
    select
        {{ json_text('order_id') }}                                              as order_id,
        cast({{ json_text('payment_sequential') }} as {{ dbt.type_int() }})       as payment_sequential,
        {{ json_text('payment_type') }}                                          as payment_type,
        -- Nombre de mensualités (le paiement en plusieurs fois est très courant au Brésil)
        cast({{ json_text('payment_installments') }} as {{ dbt.type_int() }})     as payment_installments,
        cast({{ json_text('payment_value') }} as {{ dbt.type_numeric() }})        as payment_value_brl,
        extracted_at
    from source
),

ranked as (
    select
        *,
        row_number() over (partition by order_id, payment_sequential order by extracted_at desc) as row_num
    from renamed
)

select
    order_id || '-' || cast(payment_sequential as {{ dbt.type_string() }}) as payment_key,
    order_id, payment_sequential, payment_type, payment_installments, payment_value_brl
from ranked
where row_num = 1
