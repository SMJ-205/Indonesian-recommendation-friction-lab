# 🛒 Indonesian Recommendation Friction Lab (v2.0)

An end-to-end automated A/B testing pipeline designed to measure the causal impact of context-aware (Geographical + Cultural) recommendations on user conversion in the Indonesian e-commerce market, using real behavioral events from the **Retailrocket dataset**.

## 🎯 Project Overview
This project evaluates the business impact of an Indonesian context-aware recommendation engine. It runs a randomized control trial to test the hypothesis: **"Does injecting local Indonesian context (holidays, provincial income indices, Google search trends) into product recommendations reduce purchase friction and increase Conversion Rate?"**

This repository serves as a portfolio piece demonstrating:
* **DE Skills:** Automated multi-source ELT pipelines, incremental loading, and API failover resiliency.
* **DA Skills:** Pre-experiment statistical power analysis, Chi-Squared Sample Ratio Mismatch (SRM) checks, Welch's T-Test and Z-Test cohort modeling, and business health guardrail monitoring.

---

## 🏗️ Architecture & Data Flow
The pipeline is designed to be fully automated, resilient, and serverless:

```mermaid
graph TD
    %% Styling
    classDef de fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b;
    classDef da fill:#f5f5f5,stroke:#616161,stroke-width:2px,color:#212121;
    classDef storage fill:#fff8e1,stroke:#ffb300,stroke-width:2px,color:#ff6f00;
    classDef trigger fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    subgraph Data_Engineering_POV ["Data Engineering Layer (Automated ETL Ingestion)"]
        A1[REST Countries API] -->|Metadata| B[Python dlt Pipeline]
        A2[Nager.Date API] -->|2015 Holidays| B
        A3[Retailrocket events.csv] -->|Sessionization & Treatment Injection| B
        A4[category_tree.csv] -->|Deterministic Category Mapping| B
        A5[bps_income_per_capita.csv] -->|Local CSV Ingest| B
        A6[pytrends Google Trends] -->|Province interest mapping| B
        
        B -->|Ingest Raw Data| C[(MotherDuck DW)]
        GHA[GitHub Actions Cron] -->|Orchestrates Weekly Run| B
    end

    subgraph Database_Layer ["Storage Layer (MotherDuck Serverless DuckDB)"]
        C -->|raw.retailrocket_events| D1[Raw Ingest Tables]
        C -->|raw.indonesian_holidays| D2[Raw Ingest Tables]
        C -->|raw.google_trends| D3[Raw Ingest Tables]
        C -->|raw.bps_income| D4[Raw Ingest Tables]
    end

    subgraph Data_Analytics_POV ["Data Analytics & Transformation Layer (dbt Core Models)"]
        D1 -->|dbt source| E1[stg_user_cohort]
        D2 & D3 & D4 -->|dbt source| E2[stg_context_signals]
        
        E1 & E2 & D1 -->|Join & Sessionize| F1[fct_recommendation_performance]
        
        F1 -->|Cohort A/B splits + MD5 Hashing| F2[fct_ab_test_significance]
        F1 -->|Guardrail Metrics Monitor| F3[mart_guardrails]
        F1 -->|Chi-Squared SRM Check| F4[srm_check]
    end

    subgraph Visualization_Layer ["Visualization & Analytics Delivery"]
        C -->|Secure Connection| S[Apache Superset]
        S -->|Hosted on GCP e2-micro VM| VM[Free Tier VM Docker Container]
    end

    %% Apply Classes
    class A1,A2,A3,A4,A5,A6,B,GHA,D1,D2,D3,D4 de;
    class E1,E2,F1,F2,F3,F4,S da;
    class C storage;
    class VM trigger;
```

1.  **Ingestion:** Python `dlt` pipeline pulls data from REST Countries API, Nager.Date API, Google Trends (`pytrends`), BPS provincial income data, and the raw Retailrocket behavioral dataset.
2.  **Orchestration:** GitHub Actions triggers the pipeline weekly with timeout limits to prevent quota drain.
3.  **Storage:** MotherDuck (Serverless DuckDB) handles the data warehouse.
4.  **Transformation:** `dbt Core` models clean the data, assign user cohorts using deterministic MD5 hashing, consolidate daily context signals, and compute statistical significance (Welch's T-test and Z-test) directly in SQL.
5.  **Visualization:** Apache Superset (hosted on GCP e2-micro VM) connects securely to MotherDuck to display conversion rates and time-to-purchase lifts.

---

## 🛠️ Tech Stack
| Layer | Technology |
| :--- | :--- |
| **Compute/Cloud** | GCP (e2-micro Always Free) |
| **Orchestration** | GitHub Actions |
| **Ingestion** | Python (`dlt`) |
| **Data Warehouse** | MotherDuck |
| **Transformation** | `dbt Core` |
| **Visualization** | Apache Superset (Dockerized on VM) |

---

## 📊 A/B Testing & Statistical Framework
The experiment uses a randomized control trial split:
* **Control Group:** Popularity-based ranking (global purchase frequency in the past 30 days).
* **Treatment Group:** Context-aware ranking (popularity boosted by holidays, provincial income index, and trending search categories).
* **Pre-Experiment Gate:** Power analysis script (`statsmodels`) calculates the minimum required sample size to prevent underpowered peeking.
* **Randomization Check:** Chi-Squared Goodness-of-Fit test model (`srm_check`) automatically flags any Sample Ratio Mismatch (SRM).
* **Novelty Control:** The primary significance engine evaluates **returning users only** (user tenure > 0) to control for first-week novelty spikes.
* **Guardrail Monitor:** Tracks session depth, browse-only rate, and cart abandonment rate to ensure the Treatment engine does not cause adverse user friction.

---

## 🚀 Getting Started
1. Clone the repo.
2. Set up your `.env` with `MOTHERDUCK_TOKEN`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Run the ingestion pipeline locally:
   ```bash
   python ingestion/pipeline.py
   ```
5. Run the power analysis gate:
   ```bash
   python pre_experiment_power_analysis.py
   ```
6. Run and test the analytical models:
   ```bash
   DBT_DUCKDB_PATH="local_recommendation_lab.db" dbt run --profiles-dir dbt_project --project-dir dbt_project
   DBT_DUCKDB_PATH="local_recommendation_lab.db" dbt test --profiles-dir dbt_project --project-dir dbt_project
   ```
7. Spin up the Superset container: `docker compose up -d`.

---
*Built for the Indonesian Market | Powered by [GCP Free Tier]*
