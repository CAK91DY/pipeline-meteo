-- Produits, avec leur catégorie en portugais.
with source as (
    select * from {{ raw_table('retail_raw', 'olist_products') }}
),

latest as (
    select * from source
    where run_date = (select max(run_date) from source)
)

select
    {{ json_text('product_id') }}                                          as product_id,
    {{ json_text('product_category_name') }}                               as category_name_pt,
    cast({{ json_text('product_weight_g') }} as {{ dbt.type_int() }})       as weight_g,
    cast({{ json_text('product_photos_qty') }} as {{ dbt.type_int() }})     as photos_qty
from latest
