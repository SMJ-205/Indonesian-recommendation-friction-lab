import os
import pandas as pd
import dlt

BPS_CSV = "data/bps_income_per_capita.csv"

@dlt.resource(write_disposition="replace", name="bps_income")
def bps_income():
    """
    Loads the BPS provincial income per capita index data from the local CSV file.
    """
    if os.path.exists(BPS_CSV):
        print(f"Loading BPS regional income per capita from {BPS_CSV}...")
        df = pd.read_csv(BPS_CSV)
        yield df.to_dict("records")
    else:
        print(f"Warning: {BPS_CSV} not found. Yielding default province list.")
        yield [
            {"province": "DKI Jakarta", "income_index": 1.00, "population_weight": 0.15},
            {"province": "Jawa Barat", "income_index": 0.65, "population_weight": 0.20},
            {"province": "Jawa Tengah", "income_index": 0.52, "population_weight": 0.15},
            {"province": "Jawa Timur", "income_index": 0.58, "population_weight": 0.18},
        ]
