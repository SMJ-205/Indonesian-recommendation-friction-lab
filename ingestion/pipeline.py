import os
import sys
import dlt

# Add the parent directory to the path so python can resolve imports correctly if run from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.sources.retailrocket import retailrocket_categories, retailrocket_events
from ingestion.sources.holidays import indonesian_holidays
from ingestion.sources.trends import google_trends
from ingestion.sources.bps import bps_income

def run_pipeline():
    """
    Orchestrates and executes the multi-source dlt ingestion pipeline,
    loading datasets into DuckDB or MotherDuck.
    """
    # Check for MotherDuck token in environment variables
    motherduck_token = os.environ.get("MOTHERDUCK_TOKEN")
    
    if motherduck_token:
        print("🚀 MOTHERDUCK_TOKEN detected. Loading data into MotherDuck...")
        credentials = f"md:///recommendation_lab?token={motherduck_token}"
    else:
        print("ℹ️ MOTHERDUCK_TOKEN not found. Loading data into local DuckDB: local_recommendation_lab.db")
        credentials = "local_recommendation_lab.db"

    # Define dlt pipeline targeting DuckDB destination
    pipeline = dlt.pipeline(
        pipeline_name="recommendation_friction_pipeline",
        destination=dlt.destinations.duckdb(credentials=credentials),
        dataset_name="raw"
    )

    print("⏳ Running dlt pipeline load jobs (Ingesting Retailrocket, Holidays, Google Trends, and BPS income tables)...")
    
    load_info = pipeline.run([
        retailrocket_categories(),
        retailrocket_events(),
        indonesian_holidays(),
        google_trends(),
        bps_income()
    ])
    
    print("✅ Pipeline ingestion completed successfully!")
    print(load_info)

if __name__ == "__main__":
    run_pipeline()
