import os
import sys
import dlt

# Add the parent directory to the path so python can resolve imports correctly if run from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.generators import fetch_countries_metadata, fetch_holidays, generate_synthetic_data

def run_pipeline():
    """
    Runs the dlt ingestion pipeline, loading raw datasets into DuckDB/MotherDuck.
    """
    # Check for MotherDuck token in environment variables or dlt secrets
    motherduck_token = os.environ.get("MOTHERDUCK_TOKEN")
    
    if motherduck_token:
        print("🚀 MOTHERDUCK_TOKEN detected. Loading data into MotherDuck...")
        # Create connection string targeting MotherDuck database named 'recommendation_lab'
        credentials = f"md:///recommendation_lab?token={motherduck_token}"
    else:
        print("ℹ️ MOTHERDUCK_TOKEN not found. Loading data into local DuckDB: local_recommendation_lab.db")
        credentials = "local_recommendation_lab.db"

    # Define dlt pipeline targeting DuckDB destination (which MotherDuck operates through)
    pipeline = dlt.pipeline(
        pipeline_name="recommendation_friction_pipeline",
        destination=dlt.destinations.duckdb(credentials=credentials),
        dataset_name="raw"
    )

    # Ingest country data (replace on each run to get latest updates)
    @dlt.resource(name="countries_metadata", write_disposition="replace")
    def countries_resource():
        yield fetch_countries_metadata()

    # Ingest holidays (replace on each run)
    @dlt.resource(name="holidays", write_disposition="replace")
    def holidays_resource():
        yield fetch_holidays()

    # Ingest synthetic transaction logs (append weekly transaction logs)
    @dlt.resource(name="transactions", write_disposition="append")
    def transactions_resource():
        # Generate 15,000 transaction events representing e-commerce traffic
        yield generate_synthetic_data(num_sessions=15000)

    # Execute load
    print("⏳ Running dlt pipeline load jobs...")
    load_info = pipeline.run([
        countries_resource(),
        holidays_resource(),
        transactions_resource()
    ])
    
    print("✅ Pipeline execution successful!")
    print(load_info)

if __name__ == "__main__":
    run_pipeline()
