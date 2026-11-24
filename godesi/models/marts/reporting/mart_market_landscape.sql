-- Q8, Q9 (real Open Food Facts data): GoDesi vs other brands sold in India.
-- Grain: one row per brand. Brands with at least 5 products, plus GoDesi always.

with off    as (select * from {{ ref('stg_off__products') }}),
     brands as (select * from {{ ref('brand_mapping') }}),

named as (

    select
        off.*,
        coalesce(brands.brand_name, initcap(off.brand_first))   as brand_name
    from off
    left join brands on off.brand_key = brands.brand_key
    where off.brand_first is not null

)

select
    brand_name,
    boolor_agg(is_godesi)                                                       as is_godesi,
    count(*)                                                                    as products,
    count(sugars_100g)                                                          as products_with_nutrition,
    round(median(sugars_100g), 1)                                               as median_sugars_100g,
    round(median(energy_kcal_100g), 0)                                          as median_energy_kcal_100g,
    count(nutriscore_grade)                                                     as products_with_nutriscore,
    round(count_if(nutriscore_grade in ('d', 'e')) / nullif(count(nutriscore_grade), 0) * 100, 1)
                                                                                as pct_nutriscore_d_or_e,
    mode(main_category)                                                         as most_common_category,
    min(year(created_at))                                                       as first_listed_year
from named
group by brand_name
having count(*) >= 5 or boolor_agg(is_godesi)
