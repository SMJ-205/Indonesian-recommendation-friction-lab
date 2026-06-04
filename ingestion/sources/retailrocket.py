import os
import hashlib
import uuid
import datetime
import pandas as pd
import dlt
from typing import List, Dict, Any

# Path to the files in the repo root
EVENTS_CSV = "events.csv"
CATEGORY_TREE_CSV = "category_tree.csv"

def is_treatment_user(visitor_id: int) -> bool:
    """
    Deterministic A/B split logic using MD5 hash of visitorid.
    Matches the dbt model variant assignment.
    """
    visitor_str = str(visitor_id)
    md5_hash = hashlib.md5(visitor_str.encode()).hexdigest()
    return md5_hash[0] in '89abcdef'

def get_holiday_dates() -> set:
    """
    Returns a static set of public holiday dates in Indonesia for 2015.
    Used for local context matching.
    """
    return {
        "2015-01-01", # New Year's Day
        "2015-01-03", # Maulid Nabi
        "2015-02-19", # Chinese New Year
        "2015-03-21", # Nyepi
        "2015-04-03", # Good Friday
        "2015-05-01", # Labor Day
        "2015-05-14", # Ascension of Christ
        "2015-06-02", # Vesak Day
        "2015-07-16", # Eid al-Fitr Holiday
        "2015-07-17", # Eid al-Fitr Day 1
        "2015-07-18", # Eid al-Fitr Day 2
        "2015-08-17", # Independence Day
        "2015-09-24", # Eid al-Adha
        "2015-10-14", # Islamic New Year
        "2015-12-24", # Christmas Eve Holiday
        "2015-12-25", # Christmas Day
    }

@dlt.source
def retailrocket_source():
    """
    dlt source containing Retailrocket events and category tree.
    """
    return [retailrocket_events(), retailrocket_categories()]

@dlt.resource(write_disposition="replace", name="retailrocket_categories")
def retailrocket_categories():
    """
    Loads the category tree metadata.
    """
    if os.path.exists(CATEGORY_TREE_CSV):
        print(f"Loading category tree from {CATEGORY_TREE_CSV}...")
        df = pd.read_csv(CATEGORY_TREE_CSV)
        yield df.to_dict("records")
    else:
        print("Warning: category_tree.csv not found, generating fallback categories.")
        yield [{"categoryid": i, "parentid": i // 10 if i > 10 else None} for i in range(1, 100)]

@dlt.resource(write_disposition="append", name="retailrocket_events", primary_key="event_id")
def retailrocket_events():
    """
    Loads, sessionizes, and injects A/B testing treatment metrics into Retailrocket events.
    """
    if not os.path.exists(EVENTS_CSV):
        print("Warning: events.csv not found. Yielding empty dataset.")
        return

    print(f"Loading raw events from {EVENTS_CSV}...")
    # Load a subset of events (250k rows) to prevent OOM on e2-micro VM while keeping massive real data
    df = pd.read_csv(EVENTS_CSV, nrows=250000)
    
    # Deduplicate raw events to ensure unique event_id keys
    df = df.drop_duplicates().reset_index(drop=True)
    
    # Sort events by user and time for sessionization
    df = df.sort_values(by=["visitorid", "timestamp"]).reset_index(drop=True)
    
    # Pre-load category mapping list
    if os.path.exists(CATEGORY_TREE_CSV):
        cat_df = pd.read_csv(CATEGORY_TREE_CSV)
        category_list = cat_df["categoryid"].dropna().unique().tolist()
    else:
        category_list = list(range(1, 100))

    # Helper function to map itemid to categoryid deterministically
    def get_category_id(item_id: int) -> int:
        h = int(hashlib.md5(str(item_id).encode()).hexdigest(), 16)
        return category_list[h % len(category_list)]

    print("Processing sessions and injecting A/B testing variant metrics...")
    
    # Sessionization constants
    SESSION_GAP_MS = 30 * 60 * 1000 # 30 minutes in milliseconds
    holidays = get_holiday_dates()
    
    sessionized_events = []
    
    # Group by visitorid to assign sessions
    grouped = df.groupby("visitorid")
    
    for visitor_id, group in grouped:
        current_session_id = str(uuid.uuid4())
        prev_timestamp = None
        is_treatment = is_treatment_user(visitor_id)
        
        # Check context indicators at session start
        first_event_ms = group["timestamp"].iloc[0]
        first_dt = datetime.datetime.utcfromtimestamp(first_event_ms / 1000.0)
        date_str = first_dt.strftime("%Y-%m-%d")
        
        is_holiday = date_str in holidays
        is_weekend = first_dt.weekday() in (5, 6)
        context_active = is_holiday or is_weekend
        
        session_has_addtocart = False
        session_has_transaction = False
        
        # Process individual events in the group
        visitor_events = []
        for idx, row in group.iterrows():
            ts = int(row["timestamp"])
            
            # Start new session if gap > 30 minutes
            if prev_timestamp is not None and (ts - prev_timestamp) > SESSION_GAP_MS:
                current_session_id = str(uuid.uuid4())
                
                # Check context for new session
                session_dt = datetime.datetime.utcfromtimestamp(ts / 1000.0)
                date_str = session_dt.strftime("%Y-%m-%d")
                is_holiday = date_str in holidays
                is_weekend = session_dt.weekday() in (5, 6)
                context_active = is_holiday or is_weekend
            
            prev_timestamp = ts
            
            event_type = str(row["event"])
            if event_type == "addtocart":
                session_has_addtocart = True
            elif event_type == "transaction":
                session_has_transaction = True
                
            visitor_events.append({
                "event_id": f"{row['visitorid']}_{ts}_{row['itemid']}_{event_type}",
                "session_id": current_session_id,
                "user_id": int(row["visitorid"]),
                "timestamp": ts,
                "event_type": event_type,
                "item_id": int(row["itemid"]),
                "category_id": get_category_id(int(row["itemid"])),
                "transaction_id": int(row["transactionid"]) if not pd.isna(row["transactionid"]) else None,
                "is_treatment": is_treatment,
                "context_active": context_active,
                "inserted_at": datetime.datetime.utcnow().isoformat()
            })
            
        # Inject treatment effect if user is in Treatment and Context is active (holidays/weekends)
        if is_treatment and context_active:
            # 1. Conversion Rate Lift: If they added to cart but didn't buy, upgrade to transaction with 8% probability
            if session_has_addtocart and not session_has_transaction:
                # Deterministic check for simulated conversions
                # We use visitor_id hash to keep it stable
                sim_hash = int(hashlib.md5(f"cvr_{visitor_id}".encode()).hexdigest(), 16)
                if (sim_hash % 100) < 8: # 8% conversion lift
                    # Find the last addtocart event to append a transaction event
                    add_to_cart_events = [e for e in visitor_events if e["event_type"] == "addtocart"]
                    if add_to_cart_events:
                        last_cart = add_to_cart_events[-1]
                        
                        # Time-to-Purchase friction reduction:
                        # Transaction happens 45% faster relative to session start
                        session_start_ts = visitor_events[0]["timestamp"]
                        original_gap = last_cart["timestamp"] - session_start_ts
                        reduced_gap = int(original_gap * 0.55) # 45% reduction
                        transaction_ts = session_start_ts + reduced_gap
                        
                        dummy_transaction_id = int(sim_hash % 1000000)
                        
                        visitor_events.append({
                            "event_id": f"{visitor_id}_{transaction_ts}_injected_{last_cart['item_id']}",
                            "session_id": last_cart["session_id"],
                            "user_id": int(visitor_id),
                            "timestamp": transaction_ts,
                            "event_type": "transaction",
                            "item_id": last_cart["item_id"],
                            "category_id": last_cart["category_id"],
                            "transaction_id": dummy_transaction_id,
                            "is_treatment": True,
                            "context_active": True,
                            "inserted_at": datetime.datetime.utcnow().isoformat()
                        })
            
            # 2. Time-to-purchase friction reduction:
            # If they already converted in the raw data, shift the transaction timestamp closer to session start
            elif session_has_transaction:
                session_start_ts = visitor_events[0]["timestamp"]
                for e in visitor_events:
                    if e["event_type"] == "transaction":
                        original_gap = e["timestamp"] - session_start_ts
                        reduced_gap = int(original_gap * 0.55) # 45% reduction
                        e["timestamp"] = session_start_ts + reduced_gap

        sessionized_events.extend(visitor_events)
        
    print(f"Ingesting {len(sessionized_events)} normalized events to dlt...")
    # Yield in chunks of 50,000 to keep memory low
    for i in range(0, len(sessionized_events), 50000):
        yield sessionized_events[i:i+50000]
