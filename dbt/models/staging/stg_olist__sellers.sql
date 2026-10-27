-- Vendeurs de la place de marché.
with source as (
    select * from {{ raw_table('retail_raw', 'olist_sellers') }}
),

latest as (
    select * from source
    where run_date = (select max(run_date) from source)
)

select
    {{ json_text('seller_id') }}              as seller_id,
    {{ json_text('seller_zip_code_prefix') }} as seller_zip_code_prefix,
    {{ json_text('seller_city') }}            as seller_city,
    {{ json_text('seller_state') }}           as seller_state
from latest
