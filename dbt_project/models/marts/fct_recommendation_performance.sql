with raw_events as (
    select * from {{ source('raw', 'retailrocket_events') }}
),

user_cohorts as (
    select * from {{ ref('stg_user_cohort') }}
),

context_signals as (
    select * from {{ ref('stg_context_signals') }}
),

-- Associate events with cohort and map category to trend keyword
events_with_metadata as (
    select
        e.event_id,
        e.session_id,
        e.user_id,
        e.event_type,
        e.timestamp,
        e.item_id,
        e.category_id,
        e.transaction_id,
        u.experiment_variant,
        u.province,
        u.first_seen_at,
        cast(to_timestamp(e.timestamp / 1000.0) as date) as event_date,
        to_timestamp(e.timestamp / 1000.0) as event_timestamp,
        -- Deterministic keyword mapping based on category_id
        case mod(e.category_id, 5)
            when 0 then 'fashion'
            when 1 then 'elektronik'
            when 2 then 'kosmetik'
            when 3 then 'makanan'
            else 'gadget'
        end as item_keyword
    from raw_events e
    join user_cohorts u on e.user_id = u.user_id
),

-- Aggregate sessions to compute session start and conversion indicators
session_aggregates as (
    select
        session_id,
        min(timestamp) as session_start_ts,
        max(case when event_type = 'transaction' then 1 else 0 end) as converted,
        count(case when event_type = 'view' then 1 end) as items_viewed,
        max(case when event_type = 'addtocart' then 1 else 0 end) as added_to_cart
    from raw_events
    group by session_id
),

joined as (
    select
        e.event_id,
        e.session_id,
        e.user_id,
        e.experiment_variant,
        e.item_id,
        e.category_id,
        e.event_type,
        e.event_timestamp,
        e.event_date,
        e.province,
        
        -- Time-to-purchase: seconds between session start and purchase event
        case 
            when e.event_type = 'transaction' 
            then (e.timestamp - sa.session_start_ts) / 1000.0
            else null 
        end as time_to_purchase_seconds,
        
        sa.converted,
        sa.items_viewed,
        sa.added_to_cart,
        
        -- Context signals
        c.is_holiday,
        c.holiday_name,
        c.trend_score_normalized,
        c.income_index_normalized,
        
        -- User tenure for novelty effect control (days since first seen)
        datediff('day', e.first_seen_at, e.event_timestamp) as user_tenure_days
    from events_with_metadata e
    join session_aggregates sa on e.session_id = sa.session_id
    left join context_signals c
        on e.event_date = c.signal_date
        and e.province = c.province
        and e.item_keyword = c.keyword
)

select
    *,
    -- Context active if weekend or public holiday
    (is_holiday = 1 or extract(dow from event_timestamp) in (0, 6)) as context_active
from joined
