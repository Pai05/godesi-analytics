-- One row per canonical city (the seed has several spellings per city; keep one row each).

select distinct
    city,
    state,
    region,
    is_metro
from {{ ref('city_mapping') }}
