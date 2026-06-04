import os
import duckdb
from statsmodels.stats.power import NormalIndPower

def run_power_analysis():
    print("=== Pre-Experiment Power Analysis ===")
    
    # Attempt to load baseline CVR from raw transactions in the DB
    baseline_cvr = 0.025 # Default fallback
    db_path = "local_recommendation_lab.db"
    
    if os.path.exists(db_path):
        try:
            conn = duckdb.connect(db_path)
            # Calculate raw baseline CVR (Total sessions that converted / total sessions)
            # We filter out injected records to get the true historical baseline
            res = conn.execute("""
                with session_events as (
                    select 
                        session_id,
                        max(case when event_type = 'transaction' and event_id not like '%injected%' then 1 else 0 end) as converted
                    from raw.retailrocket_events
                    group by session_id
                )
                select 
                    sum(converted) * 1.0 / count(*) as cvr
                from session_events
            """).fetchone()
            if res and res[0] is not None:
                baseline_cvr = float(res[0])
                print(f"Calculated Baseline CVR from events database: {baseline_cvr * 100:.3f}%")
        except Exception as e:
            print(f"Note: Could not calculate CVR from DB ({e}). Using default: {baseline_cvr * 100:.1f}%")
    else:
        print(f"Note: local database not found. Using default baseline CVR: {baseline_cvr * 100:.1f}%")
        
    mde = 0.02 # Minimum Detectable Effect (2% absolute lift)
    power = 0.80 # 80% power
    alpha = 0.025 # Bonferroni-corrected significance level (0.05 / 2 metrics: CVR & TTP)
    
    # Calculate effect size for two proportions
    p1 = baseline_cvr
    p2 = baseline_cvr + mde
    p_avg = (p1 + p2) / 2
    effect_size = abs(p1 - p2) / (p_avg * (1 - p_avg)) ** 0.5
    
    analysis = NormalIndPower()
    n_per_group = analysis.solve_power(
        effect_size=effect_size,
        power=power,
        alpha=alpha,
        ratio=1.0,
        alternative='two-sided'
    )
    
    total_required = int(n_per_group) * 2
    
    print("\n------------------------------------------------")
    print(f"Parameters Locked:")
    print(f"  * Baseline CVR:                    {baseline_cvr * 100:.2f}%")
    print(f"  * Target Treatment CVR (MDE):      {(baseline_cvr + mde) * 100:.2f}% (absolute lift: {mde*100:.1f}%)")
    print(f"  * Statistical Power (1 - Beta):    {power * 100:.1f}%")
    print(f"  * Significance Threshold (Alpha):  {alpha:.3f} (Bonferroni-corrected for 2 metrics)")
    print("------------------------------------------------")
    print(f"Calculated Sample Sizes:")
    print(f"  * Minimum users required PER GROUP: {int(n_per_group):,}")
    print(f"  * Total minimum users required:     {total_required:,}")
    print("------------------------------------------------")
    print("Decision Rule: Do not analyze or peek at results until the total")
    print(f"distinct user count in fct_recommendation_performance exceeds {total_required:,} users.")
    print("=== Power Analysis Completed ===")

if __name__ == "__main__":
    run_power_analysis()
