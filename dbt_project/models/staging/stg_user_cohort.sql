with raw_events as (
    select * from {{ source('raw', 'retailrocket_events') }}
),

user_base as (
    select
        user_id,
        min(timestamp) as min_ts
    from raw_events
    group by user_id
),

provinces as (
    select 
        province,
        row_number() over (order by province) - 1 as prov_idx,
        count(*) over () as total_provs
    from {{ source('raw', 'bps_income') }}
)

select
    cast(u.user_id as bigint) as user_id,
    case 
        when strpos('89abcdef', lower(left(md5(cast(u.user_id as varchar)), 1))) > 0 then 'treatment'
        else 'control'
    end as experiment_variant,
    to_timestamp(u.min_ts / 1000.0) as first_seen_at,
    
    -- Map user deterministically to a province based on their user_id
    p.province as province
from user_base u
join provinces p
    on mod(u.user_id, p.total_provs) = p.prov_idx
