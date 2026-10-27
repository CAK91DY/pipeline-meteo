-- Produits, avec une catégorie lisible et jamais vide.
select
    products.product_id,
    products.category_name_pt,
    -- 1) nom anglais si la traduction existe, 2) sinon le nom portugais,
    -- 3) sinon "unknown" : une case vide fausserait les regroupements par catégorie.
    coalesce(translation.category_name_en, products.category_name_pt, 'unknown') as category,
    products.weight_g,
    products.photos_qty
from {{ ref('stg_olist__products') }} as products
left join {{ ref('stg_olist__category_translation') }} as translation
    on products.category_name_pt = translation.category_name_pt
