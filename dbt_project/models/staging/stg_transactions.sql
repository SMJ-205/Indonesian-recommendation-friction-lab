with source as (
    select * from {{ source('raw', 'transactions') }}
)

select
    cast(session_id as varchar) as session_id,
    cast(user_id as bigint) as user_id,
    cast(session_timestamp as timestamp) as session_timestamp,
    cast(province as varchar) as province,
    cast(device as varchar) as device,
    cast(clicks as integer) as clicks,
    cast(purchased as boolean) as purchased,
    cast(time_to_purchase_seconds as integer) as time_to_purchase_seconds,
    cast(inserted_at as timestamp) as inserted_at
from source
