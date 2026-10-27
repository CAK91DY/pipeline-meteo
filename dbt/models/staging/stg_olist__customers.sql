-- Clients. Attention : chez Olist, customer_id change à chaque commande ;
-- c'est customer_unique_id qui identifie une personne (utile pour compter les clients fidèles).
with source as (
    select * from {{ raw_table('retail_raw', 'olist_customers') }}
),

latest as (
    -- Table de référence : chaque extraction contient la liste complète.
    -- On ne garde que l'extraction la plus récente.
    select *
    from source
    where run_date = (select max(run_date) from source)
)

select
    {{ json_text('customer_id') }}              as customer_id,
    {{ json_text('customer_unique_id') }}       as customer_unique_id,
    {{ json_text('customer_zip_code_prefix') }} as customer_zip_code_prefix,
    {{ json_text('customer_city') }}            as customer_city,
    {{ json_text('customer_state') }}           as customer_state   -- sigle de l'État : SP, RJ...
from latest
