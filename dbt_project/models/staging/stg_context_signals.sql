with dates as (
    select distinct
        cast(to_timestamp(timestamp / 1000.0) as date) as signal_date
    from {{ source('raw', 'retailrocket_events') }}
),

provinces as (
    select * from {{ source('raw', 'bps_income') }}
),

holidays as (
    select * from {{ source('raw', 'indonesian_holidays') }}
),

trends as (
    select * from {{ source('raw', 'google_trends') }}
),

date_province as (
    select
        d.signal_date,
        p.province,
        p.income_index
    from dates d
    cross join provinces p
),

joined as (
    select
        dp.signal_date,
        dp.province,
        dp.income_index,
        case when h.holiday_date is not null then 1 else 0 end as is_holiday,
        h.english_name as holiday_name,
        t.keyword,
        coalesce(t.trend_score, 50) as trend_score
    from date_province dp
    left join holidays h
        on dp.signal_date = cast(h.holiday_date as date)
    left join trends t
        on dp.province = t.province
)

select
    signal_date,
    province,
    keyword,
    income_index,
    is_holiday,
    holiday_name,
    trend_score,
    cast(is_holiday as double) as holiday_score,
    cast(trend_score as double) / 100.0 as trend_score_normalized,
    cast(income_index as double) as income_index_normalized
from joined
