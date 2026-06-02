with transactions as (
    select * from {{ ref('stg_transactions') }}
),

holidays as (
    select * from {{ ref('stg_holidays') }}
),

joined as (
    select
        t.session_id,
        t.user_id,
        -- Deterministic variant assignment based on user_id hash matching Python generator
        case 
            when strpos('89abcdef', lower(left(md5(cast(t.user_id as varchar)), 1))) > 0 then 'Treatment'
            else 'Control'
        end as experiment_variant,
        t.session_timestamp,
        cast(t.session_timestamp as date) as session_date,
        t.province,
        t.device,
        t.clicks,
        t.purchased,
        t.time_to_purchase_seconds,
        h.holiday_date is not null as is_holiday,
        h.english_name as holiday_name,
        (extract(dow from t.session_timestamp) in (0, 6)) as is_weekend
    from transactions t
    left join holidays h
        on cast(t.session_timestamp as date) = h.holiday_date
)

select
    *,
    -- Context-aware trigger is active on weekends or national holidays
    (is_holiday or is_weekend) as context_active
from joined
