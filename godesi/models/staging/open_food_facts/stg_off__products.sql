-- One row per barcode: the ~25 useful columns of the 211 in the Open Food Facts export.

with source as (

    select * from {{ source('open_food_facts', 'products') }}

),

renamed as (

    select
        trim(code)                                                      as barcode,
        nullif(trim(product_name), '')                                  as product_name,

        -- brands is a free-text list: 'Desi Pop, Go Desi'. Keep the first one and a
        -- punctuation-free key ('Haldiram''s' / 'haldirams' -> 'haldirams') for mapping.
        trim(brands)                                                    as brands_raw,
        nullif(trim(split_part(brands, ',', 1)), '')                    as brand_first,
        nullif(regexp_replace(lower(split_part(brands, ',', 1)), '[^a-z0-9]', ''), '') as brand_key,
        coalesce(lower(brands) like '%go desi%' or lower(brands) like '%godesi%', false) as is_godesi,

        trim(quantity)                                                  as quantity_raw,
        try_to_double(regexp_substr(lower(quantity), $$(\d+(\.\d+)?)\s*(kg|gm|g|ml|ltr|l)$$, 1, 1, 'e', 1)) as quantity_value,
        regexp_substr(lower(quantity), $$(\d+(\.\d+)?)\s*(kg|gm|g|ml|ltr|l)$$, 1, 1, 'e', 3)                as quantity_unit,

        regexp_replace(main_category_en, '^[a-z]{2}:', '')              as main_category,   -- 'en:Imli' -> 'Imli'
        categories_tags,
        labels_tags,

        nullif(nullif(lower(nutriscore_grade), 'unknown'), 'not-applicable')  as nutriscore_grade,
        try_to_number(nova_group)                                       as nova_group,
        try_to_number(additives_n)                                      as additives_count,
        try_to_double(energy_kcal_100g)                                 as energy_kcal_100g,
        try_to_double(fat_100g)                                         as fat_100g,
        try_to_double(saturated_fat_100g)                               as saturated_fat_100g,
        try_to_double(carbohydrates_100g)                               as carbohydrates_100g,
        try_to_double(sugars_100g)                                      as sugars_100g,
        try_to_double(fiber_100g)                                       as fiber_100g,
        try_to_double(proteins_100g)                                    as proteins_100g,
        try_to_double(salt_100g)                                        as salt_100g,

        try_to_number(unique_scans_n)                                   as unique_scans,
        try_to_double(completeness)                                     as completeness,
        {{ parse_timestamp('created_datetime') }}                       as created_at,
        {{ parse_timestamp('last_modified_datetime') }}                 as last_modified_at,
        _loaded_at

    from source

),

final as (

    select
        *,
        case quantity_unit
            when 'kg'  then quantity_value * 1000
            when 'g'   then quantity_value
            when 'gm'  then quantity_value
            when 'l'   then quantity_value * 1000
            when 'ltr' then quantity_value * 1000
            when 'ml'  then quantity_value
        end                                                             as net_quantity,       -- grams or ml
        case when quantity_unit in ('ml', 'l', 'ltr') then 'ml'
             when quantity_unit is not null then 'g'
        end                                                             as net_quantity_unit
    from renamed

)

select * from final
