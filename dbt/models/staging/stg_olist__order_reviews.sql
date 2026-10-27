-- Avis clients. Attention : une commande peut avoir plusieurs avis, et un même
-- review_id peut concerner plusieurs commandes. La clé est donc le couple (avis, commande).
-- Le choix d'UN avis par commande se fait plus loin, dans fct_orders.
with source as (
    select * from {{ raw_table('retail_raw', 'olist_order_reviews') }}
),

renamed as (
    select
        {{ json_text('review_id') }}                                       as review_id,
        {{ json_text('order_id') }}                                        as order_id,
        cast({{ json_text('review_score') }} as {{ dbt.type_int() }})       as review_score,
        {{ json_text('review_comment_title') }}                            as review_title,
        {{ json_text('review_comment_message') }}                          as review_message,
        cast({{ json_text('review_creation_date') }} as timestamp)          as review_created_at,
        cast({{ json_text('review_answer_timestamp') }} as timestamp)       as review_answered_at,
        extracted_at
    from source
),

ranked as (
    select
        *,
        row_number() over (partition by review_id, order_id order by extracted_at desc) as row_num
    from renamed
)

select
    review_id || '-' || order_id as review_key,
    review_id, order_id, review_score, review_title, review_message,
    review_created_at, review_answered_at
from ranked
where row_num = 1
