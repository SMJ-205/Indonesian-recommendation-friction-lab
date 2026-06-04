with counts as (
    select
        experiment_variant,
        count(distinct user_id) as observed
    from {{ ref('fct_recommendation_performance') }}
    group by experiment_variant
),

stats as (
    select
        coalesce(max(case when experiment_variant = 'control' then observed end), 0) as observed_control,
        coalesce(max(case when experiment_variant = 'treatment' then observed end), 0) as observed_treatment,
        sum(observed) as total_observed,
        sum(observed) / 2.0 as expected
    from counts
),

chi_squared as (
    select
        observed_control,
        observed_treatment,
        total_observed,
        case 
            when expected > 0 
            then (power(observed_control - expected, 2) / expected) + (power(observed_treatment - expected, 2) / expected)
            else 0
        end as chi_sq_stat
    from stats
)

select
    observed_control,
    observed_treatment,
    total_observed,
    round(chi_sq_stat, 4) as chi_squared_statistic,
    -- If chi-squared > 3.841 (critical value for df=1 at alpha=0.05), we reject the 50/50 split null hypothesis.
    case 
        when chi_sq_stat > 3.841 then 'WARNING: SRM DETECTED (Imbalanced split)'
        else 'PASS: Randomization healthy'
    end as srm_status
from chi_squared
