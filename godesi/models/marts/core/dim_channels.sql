-- One row per sales channel.

select
    channel,
    channel_name,
    channel_type
from {{ ref('channel_mapping') }}
