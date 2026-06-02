with source as (
    select * from {{ source('raw', 'holidays') }}
)

select
    cast(holiday_date as date) as holiday_date,
    cast(local_name as varchar) as local_name,
    cast(english_name as varchar) as english_name,
    cast(country_code as varchar) as country_code,
    cast(global_holiday as boolean) as global_holiday,
    cast(year as integer) as holiday_year
from source
