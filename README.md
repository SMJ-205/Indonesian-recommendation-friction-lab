# 🛒 Indonesian Recommendation Friction Lab

An end-to-end automated A/B testing pipeline designed to measure the impact of context-aware (Geographical + Cultural) recommendations on user conversion in the Indonesian e-commerce market.

## 🎯 Project Overview
This project simulates an e-commerce recommendation engine to test the hypothesis: **"Does injecting local Indonesian context (holidays, regional trends) into product recommendations reduce purchase friction?"**

This repository serves as a portfolio piece demonstrating:
* **DE Skills:** Automated ELT pipelines, state management, and cloud orchestration.
* **DA Skills:** Statistical hypothesis testing, A/B experimental design, and actionable metric modeling.

## 🏗️ Architecture & Data Flow
The pipeline is designed to be fully automated and cloud-native:

```mermaid
graph TD
    %% Styling
    classDef de fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b;
    classDef da fill:#f5f5f5,stroke:#616161,stroke-width:2px,color:#212121;
    classDef storage fill:#fff8e1,stroke:#ffb300,stroke-width:2px,color:#ff6f00;
    classDef trigger fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    subgraph Data_Engineering_POV ["Data Engineering Layer (Automated ETL Ingestion)"]
        A1[REST Countries API] -->|Metadata| B[Python dlt Pipeline]
        A2[Nager.Date API] -->|Holidays| B
        A3[Faker Transaction Generator] -->|Clickstream Logs| B
        
        B -->|Ingest Raw Data| C[(MotherDuck DW)]
        
        GHA[GitHub Actions Cron] -->|Orchestrates Weekly Run| B
    end

    subgraph Database_Layer ["Storage Layer (MotherDuck Serverless DuckDB)"]
        C -->|raw.countries_metadata| D1[Raw Ingest Tables]
        C -->|raw.holidays| D2[Raw Ingest Tables]
        C -->|raw.transactions| D3[Raw Ingest Tables]
    end

    subgraph Data_Analytics_POV ["Data Analytics & Transformation Layer (dbt Core Models)"]
        D1 -->|dbt source| E1[stg_holidays]
        D2 -->|dbt source| E1
        D3 -->|dbt source| E2[stg_transactions]
        
        E1 & E2 -->|Join & Assign Cohort| F1[fct_recommendation_performance]
        
        F1 -->|Cohort A/B splits + MD5 Hashing| F2[fct_ab_test_significance]
        
        subgraph Stats_Engine ["dbt SQL Statistical Engine"]
            F2 -->|Welch's T-Test| T[Time-to-Purchase Friction]
            F2 -->|Two-Proportion Z-Test| Z[Conversion Rate Lift]
        end
    end

    subgraph Visualization_Layer ["Visualization & Analytics Delivery"]
        C -->|Secure Connection| S[Apache Superset]
        S -->|Hosted on GCP e2-micro VM| VM[Free Tier VM Docker Container]
        
        Stats_Engine -.->|Visualized in Charts| S
    end

    %% Apply Classes
    class A1,A2,A3,B,GHA,D1,D2,D3 de;
    class E1,E2,F1,F2,T,Z,S da;
    class C storage;
    class VM trigger;
```

1.  **Ingestion:** Python `dlt` pipeline pulls data from REST Countries API, Nager.Date API, and synthetic transaction logs.
2.  **Orchestration:** GitHub Actions triggers the pipeline weekly.
3.  **Storage:** MotherDuck (Serverless DuckDB) handles the data warehouse.
4.  **Transformation:** `dbt Core` models clean the data, assign user cohorts using MD5 hashing, and compute statistical significance (Welch's T-test and Z-test) directly in SQL.
5.  **Visualization:** Apache Superset (hosted on GCP e2-micro VM) connects securely to MotherDuck to display conversion rates and time-to-purchase lifts.

## 🛠️ Tech Stack
| Layer | Technology |
| :--- | :--- |
| **Compute/Cloud** | GCP (e2-micro) |
| **Orchestration** | GitHub Actions |
| **Ingestion** | Python (`dlt`) |
| **Data Warehouse** | MotherDuck |
| **Transformation** | `dbt Core` |
| **Visualization** | Apache Superset |

## 📊 A/B Testing Methodology
The experiment uses a randomized control trial split:
* **Control Group:** Generic, non-contextual recommendations.
* **Treatment Group:** Context-aware recommendations (triggered by holiday/geo-trends).
* **Metrics:** 
    * Primary: Conversion Rate (CVR).
    * Secondary: Time-to-Purchase (TTP) — our primary proxy for "Friction."
    * Significance Testing: Welch's T-Test and Chi-Squared implementation.

## 🚀 Getting Started
1. Clone the repo.
2. Set up your `.env` with `MOTHERDUCK_TOKEN`.
3. Run the pipeline: `python pipeline.py`.
4. Spin up the Superset container: `docker-compose up -d`.

---
*Built for the Indonesian Market | Powered by [GCP Free Tier]*
