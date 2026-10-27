-- Traduction des catégories de produits, du portugais vers l'anglais.
with source as (
    select * from {{ raw_table('retail_raw', 'olist_category_translation') }}
),

latest as (
    select * from source
    where run_date = (select max(run_date) from source)
)

select
    {{ json_text('product_category_name') }}         as category_name_pt,
    {{ json_text('product_category_name_english') }} as category_name_en
from latest
