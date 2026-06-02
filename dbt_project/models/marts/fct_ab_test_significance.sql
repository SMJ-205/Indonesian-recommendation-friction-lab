with performance as (
    select * from {{ ref('fct_recommendation_performance') }}
),

-- Define segments to evaluate: Overall, Context-Active, and Non-Context
segmented as (
    select
        'Overall' as segment,
        experiment_variant,
        purchased,
        time_to_purchase_seconds
    from performance

    union all

    select
        'Context Active (Holidays & Weekends)' as segment,
        experiment_variant,
        purchased,
        time_to_purchase_seconds
    from performance
    where context_active = true

    union all

    select
        'Non-Context Days (Weekdays)' as segment,
        experiment_variant,
        purchased,
        time_to_purchase_seconds
    from performance
    where context_active = false
),

-- Compute metrics per variant and segment
group_stats as (
    select
        segment,
        experiment_variant,
        -- Metrics for Conversion Rate (CVR) Z-Test
        count(*) as total_sessions,
        count(case when purchased = true then 1 end) as converted_sessions,
        
        -- Metrics for Time-to-Purchase (TTP) Welch's T-Test (only on converting sessions)
        count(case when purchased = true and time_to_purchase_seconds is not null then 1 end) as ttp_sample_size,
        avg(case when purchased = true then time_to_purchase_seconds end) as ttp_mean,
        var_samp(case when purchased = true then time_to_purchase_seconds end) as ttp_variance
    from segmented
    group by segment, experiment_variant
),

-- Pivot Control and Treatment stats into a single row per segment
pivoted as (
    select
        c.segment,
        
        -- Control stats
        c.total_sessions as n_ctrl,
        c.converted_sessions as x_ctrl,
        cast(c.converted_sessions as double) / c.total_sessions as cvr_ctrl,
        c.ttp_sample_size as ttp_n_ctrl,
        c.ttp_mean as ttp_mean_ctrl,
        c.ttp_variance as ttp_var_ctrl,
        
        -- Treatment stats
        t.total_sessions as n_treat,
        t.converted_sessions as x_treat,
        cast(t.converted_sessions as double) / t.total_sessions as cvr_treat,
        t.ttp_sample_size as ttp_n_treat,
        t.ttp_mean as ttp_mean_treat,
        t.ttp_variance as ttp_var_treat
    from group_stats c
    join group_stats t 
        on c.segment = t.segment
    where c.experiment_variant = 'Control'
      and t.experiment_variant = 'Treatment'
),

-- Calculate Z-Test for CVR and Welch's T-Test for TTP
calculations as (
    select
        segment,
        n_ctrl,
        x_ctrl,
        cvr_ctrl,
        n_treat,
        x_treat,
        cvr_treat,
        (cvr_treat - cvr_ctrl) as cvr_lift,
        
        -- CVR Z-Test logic
        (cast(x_ctrl + x_treat as double) / (n_ctrl + n_treat)) as p_pooled,
        
        -- TTP Welch's T-Test logic
        ttp_n_ctrl,
        ttp_mean_ctrl,
        ttp_var_ctrl,
        ttp_n_treat,
        ttp_mean_treat,
        ttp_var_treat,
        (ttp_mean_ctrl - ttp_mean_treat) as ttp_reduction_seconds, -- positive means treatment is faster
        
        -- Welch's T Denominator (Standard Error of Difference)
        sqrt((ttp_var_ctrl / ttp_n_ctrl) + (ttp_var_treat / ttp_n_treat)) as t_se
    from pivoted
),

z_and_t_stats as (
    select
        *,
        -- CVR Z-Statistic
        (cvr_treat - cvr_ctrl) / nullif(sqrt(p_pooled * (1.0 - p_pooled) * (1.0 / n_ctrl + 1.0 / n_treat)), 0) as cvr_z_stat,
        
        -- TTP T-Statistic
        ttp_reduction_seconds / nullif(t_se, 0) as ttp_t_stat,
        
        -- Degrees of Freedom for Welch's T-test
        power((ttp_var_ctrl / ttp_n_ctrl) + (ttp_var_treat / ttp_n_treat), 2) / 
        nullif(
            (power(ttp_var_ctrl / ttp_n_ctrl, 2) / (ttp_n_ctrl - 1)) + 
            (power(ttp_var_treat / ttp_n_treat, 2) / (ttp_n_treat - 1)), 
            0
        ) as welch_df
    from calculations
)

select
    segment,
    
    -- CVR metrics & significance
    n_ctrl as control_sessions,
    n_treat as treatment_sessions,
    round(cvr_ctrl * 100, 2) as control_cvr_pct,
    round(cvr_treat * 100, 2) as treatment_cvr_pct,
    round(cvr_lift * 100, 2) as cvr_lift_pct,
    round(cvr_z_stat, 4) as cvr_z_stat,
    
    -- Two-tailed p-value for CVR Z-Test using Logistic-Normal CDF approximation
    round(
        2.0 / (1.0 + exp(1.5976 * abs(cvr_z_stat) * (1.0 + 0.04417 * power(cvr_z_stat, 2)))), 
        6
    ) as cvr_p_value,
    
    -- TTP metrics & significance
    ttp_n_ctrl as control_conversions,
    ttp_n_treat as treatment_conversions,
    round(ttp_mean_ctrl, 2) as control_mean_ttp_sec,
    round(ttp_mean_treat, 2) as treatment_mean_ttp_sec,
    round(ttp_reduction_seconds, 2) as ttp_reduction_sec,
    round(ttp_t_stat, 4) as ttp_t_stat,
    round(welch_df, 1) as degrees_of_freedom,
    
    -- Two-tailed p-value for TTP Welch's T-Test using same approximation (df is large)
    round(
        2.0 / (1.0 + exp(1.5976 * abs(ttp_t_stat) * (1.0 + 0.04417 * power(ttp_t_stat, 2)))), 
        6
    ) as ttp_p_value
from z_and_t_stats
