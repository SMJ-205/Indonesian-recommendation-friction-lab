with sessions as (
    select distinct
        session_id,
        experiment_variant,
        items_viewed,
        added_to_cart,
        converted,
        case when user_tenure_days = 0 then 'new_user' else 'returning_user' end as user_segment
    from {{ ref('fct_recommendation_performance') }}
)

select
    experiment_variant,
    user_segment,
    count(distinct session_id) as total_sessions,
    
    -- Guardrail 1: Session depth (average items viewed per session)
    round(avg(items_viewed), 2) as avg_session_depth,
    
    -- Guardrail 2: Browse-only rate (sessions that viewed but never added to cart)
    round(
        count(case when added_to_cart = 0 then 1 end) * 100.0 / count(distinct session_id), 
        2
    ) as browse_only_rate_pct,
    
    -- Guardrail 3: Cart abandonment rate (sessions that added to cart but did not purchase)
    round(
        count(case when added_to_cart = 1 and converted = 0 then 1 end) * 100.0 
        / nullif(count(case when added_to_cart = 1 then 1 end), 0),
        2
    ) as cart_abandonment_rate_pct
from sessions
group by experiment_variant, user_segment
