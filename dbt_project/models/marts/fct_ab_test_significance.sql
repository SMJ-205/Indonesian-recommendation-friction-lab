with performance as (
    select * from {{ ref('fct_recommendation_performance') }}
),

-- Define segments to evaluate: Overall, Context-Active, and Non-Context
segmented as (
    select
        'Overall' as segment,
        experiment_variant,
        session_id,
        user_id,
        converted,
        time_to_purchase_seconds,
        user_tenure_days
    from performance

    union all

    select
        'Context Active (Holidays & Weekends)' as segment,
        experiment_variant,
        session_id,
        user_id,
        converted,
        time_to_purchase_seconds,
        user_tenure_days
    from performance
    where context_active = true

    union all

    select
        'Non-Context Days (Weekdays)' as segment,
        experiment_variant,
        session_id,
        user_id,
        converted,
        time_to_purchase_seconds,
        user_tenure_days
    from performance
    where context_active = false
),

-- Compute metrics per variant and segment
group_stats as (
    select
        segment,
        experiment_variant,
        -- Metrics for Conversion Rate (CVR) Z-Test
        count(distinct user_id) as total_users,
        count(distinct session_id) as total_sessions,
        count(distinct case when converted = 1 then session_id end) as conversions,
        
        -- Metrics for Time-to-Purchase (TTP) Welch's T-Test
        count(case when converted = 1 and time_to_purchase_seconds is not null then 1 end) as ttp_sample_size,
        avg(case when converted = 1 then time_to_purchase_seconds end) as ttp_mean,
        var_samp(case when converted = 1 then time_to_purchase_seconds end) as ttp_variance
    from segmented
    -- Exclude first-session users (novelty control)
    where user_tenure_days > 0
    group by segment, experiment_variant
),

-- Pivot Control and Treatment stats
pivoted as (
    select
        c.segment,
        
        -- Control stats
        c.total_users as users_ctrl,
        c.total_sessions as n_ctrl,
        c.conversions as x_ctrl,
        cast(c.conversions as double) / c.total_sessions as cvr_ctrl,
        c.ttp_sample_size as ttp_n_ctrl,
        c.ttp_mean as ttp_mean_ctrl,
        c.ttp_variance as ttp_var_ctrl,
        
        -- Treatment stats
        t.total_users as users_treat,
        t.total_sessions as n_treat,
        t.conversions as x_treat,
        cast(t.conversions as double) / t.total_sessions as cvr_treat,
        t.ttp_sample_size as ttp_n_treat,
        t.ttp_mean as ttp_mean_treat,
        t.ttp_variance as ttp_var_treat
    from group_stats c
    join group_stats t on c.segment = t.segment
    where c.experiment_variant = 'control'
      and t.experiment_variant = 'treatment'
),

-- Calculations for statistical tests
calculations as (
    select
        segment,
        users_ctrl,
        users_treat,
        n_ctrl,
        x_ctrl,
        cvr_ctrl,
        n_treat,
        x_treat,
        cvr_treat,
        (cvr_treat - cvr_ctrl) as cvr_lift_absolute,
        (cvr_treat - cvr_ctrl) / nullif(cvr_ctrl, 0) as cvr_lift_relative,
        
        -- CVR Z-Test logic
        (cast(x_ctrl + x_treat as double) / (n_ctrl + n_treat)) as p_pooled,
        
        -- TTP Welch's T-Test logic
        ttp_n_ctrl,
        ttp_mean_ctrl,
        ttp_var_ctrl,
        ttp_n_treat,
        ttp_mean_treat,
        ttp_var_treat,
        (ttp_mean_ctrl - ttp_mean_treat) as ttp_reduction_seconds, -- positive means treatment reduces friction
        sqrt((ttp_var_ctrl / nullif(ttp_n_ctrl, 0)) + (ttp_var_treat / nullif(ttp_n_treat, 0))) as t_se
    from pivoted
),

z_and_t_stats as (
    select
        *,
        -- CVR Z-Statistic
        cvr_lift_absolute / nullif(sqrt(p_pooled * (1.0 - p_pooled) * (1.0 / n_ctrl + 1.0 / n_treat)), 0) as cvr_z_stat,
        
        -- TTP T-Statistic
        ttp_reduction_seconds / nullif(t_se, 0) as ttp_t_stat,
        
        -- Degrees of Freedom for Welch's T-test
        power((ttp_var_ctrl / nullif(ttp_n_ctrl, 0)) + (ttp_var_treat / nullif(ttp_n_treat, 0)), 2) / 
        nullif(
            (power(ttp_var_ctrl / nullif(ttp_n_ctrl, 0), 2) / nullif(ttp_n_ctrl - 1, 0)) + 
            (power(ttp_var_treat / nullif(ttp_n_treat, 0), 2) / nullif(ttp_n_treat - 1, 0)), 
            0
        ) as welch_df
    from calculations
)

select
    segment,
    users_ctrl as control_users,
    users_treat as treatment_users,
    n_ctrl as control_sessions,
    n_treat as treatment_sessions,
    round(cvr_ctrl * 100, 2) as control_cvr_pct,
    round(cvr_treat * 100, 2) as treatment_cvr_pct,
    round(cvr_lift_absolute * 100, 2) as cvr_lift_abs_pct,
    round(cvr_lift_relative * 100, 2) as cvr_lift_rel_pct,
    round(cvr_z_stat, 4) as cvr_z_stat,
    
    -- Two-tailed p-value for CVR Z-Test (alpha threshold is 0.025 due to Bonferroni correction)
    round(
        2.0 / (1.0 + exp(1.5976 * abs(cvr_z_stat) * (1.0 + 0.04417 * power(cvr_z_stat, 2)))), 
        6
    ) as cvr_p_value,
    
    ttp_n_ctrl as control_conversions,
    ttp_n_treat as treatment_conversions,
    round(ttp_mean_ctrl, 2) as control_mean_ttp_sec,
    round(ttp_mean_treat, 2) as treatment_mean_ttp_sec,
    round(ttp_reduction_seconds, 2) as ttp_reduction_sec,
    round(ttp_t_stat, 4) as ttp_t_stat,
    round(welch_df, 1) as degrees_of_freedom,
    
    -- Two-tailed p-value for TTP Welch's T-Test
    round(
        2.0 / (1.0 + exp(1.5976 * abs(ttp_t_stat) * (1.0 + 0.04417 * power(ttp_t_stat, 2)))), 
        6
    ) as ttp_p_value
from z_and_t_stats
