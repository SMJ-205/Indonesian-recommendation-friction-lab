import datetime
import hashlib
import random
import requests
from typing import List, Dict, Any
from faker import Faker

fake = Faker('id_ID')  # Use Indonesian locale for Faker

# List of Indonesian provinces with rough population weightings (for realistic geo distribution)
INDONESIAN_PROVINCES = [
    {"name": "DKI Jakarta", "weight": 15},
    {"name": "Jawa Barat", "weight": 20},
    {"name": "Jawa Tengah", "weight": 15},
    {"name": "Jawa Timur", "weight": 18},
    {"name": "Banten", "weight": 8},
    {"name": "Sumatera Utara", "weight": 6},
    {"name": "Sulawesi Selatan", "weight": 4},
    {"name": "Bali", "weight": 3},
    {"name": "DI Yogyakarta", "weight": 3},
    {"name": "Kalimantan Timur", "weight": 2},
    {"name": "Riau", "weight": 3},
    {"name": "Sumatera Selatan", "weight": 3},
]

def get_weighted_province() -> str:
    provinces = [p["name"] for p in INDONESIAN_PROVINCES]
    weights = [p["weight"] for p in INDONESIAN_PROVINCES]
    return random.choices(provinces, weights=weights, k=1)[0]

def fetch_countries_metadata() -> List[Dict[str, Any]]:
    """
    Fetches Indonesian metadata from the REST Countries API.
    Includes fallbacks in case of API failure.
    """
    url = "https://restcountries.com/v3.1/name/indonesia"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                country = data[0]
                return [{
                    "country_name": country.get("name", {}).get("common", "Indonesia"),
                    "official_name": country.get("name", {}).get("official", "Republic of Indonesia"),
                    "capital": country.get("capital", ["Jakarta"])[0],
                    "region": country.get("region", "Asia"),
                    "subregion": country.get("subregion", "South-Eastern Asia"),
                    "population": country.get("population", 273523615),
                    "area": country.get("area", 1904569.0),
                    "languages": ", ".join(country.get("languages", {}).values()),
                    "latitude": country.get("latlng", [-5.0, 120.0])[0],
                    "longitude": country.get("latlng", [-5.0, 120.0])[1],
                    "fetched_at": datetime.datetime.utcnow().isoformat()
                }]
    except Exception as e:
        print(f"Warning: REST Countries API fetch failed ({e}). Using fallback metadata.")
    
    # Fallback response
    return [{
        "country_name": "Indonesia",
        "official_name": "Republic of Indonesia",
        "capital": "Jakarta",
        "region": "Asia",
        "subregion": "South-Eastern Asia",
        "population": 273523615,
        "area": 1904569.0,
        "languages": "Indonesian",
        "latitude": -5.0,
        "longitude": 120.0,
        "fetched_at": datetime.datetime.utcnow().isoformat()
    }]

def fetch_holidays() -> List[Dict[str, Any]]:
    """
    Fetches public holidays in Indonesia for 2025 and 2026 from Nager.Date API.
    Includes fallback static holidays if API is down.
    """
    years = [2025, 2026]
    holidays = []
    
    for year in years:
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/ID"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    holidays.append({
                        "holiday_date": item.get("date"),
                        "local_name": item.get("localName"),
                        "english_name": item.get("name"),
                        "country_code": item.get("countryCode"),
                        "global_holiday": item.get("global"),
                        "year": year
                    })
                continue
        except Exception as e:
            print(f"Warning: Nager.Date API fetch failed for year {year} ({e}).")
            
        # Fallback public holidays for Indonesia
        fallbacks = [
            {"date": f"{year}-01-01", "localName": "Tahun Baru Masehi", "name": "New Year's Day"},
            {"date": f"{year}-03-29", "localName": "Hari Suci Nyepi", "name": "Nyepi Kasa"},
            {"date": f"{year}-05-01", "localName": "Hari Buruh Internasional", "name": "International Workers' Day"},
            {"date": f"{year}-05-13", "localName": "Hari Raya Waisak", "name": "Vesak Day"},
            {"date": f"{year}-06-01", "localName": "Hari Lahir Pancasila", "name": "Pancasila Day"},
            {"date": f"{year}-08-17", "localName": "Hari Kemerdekaan RI", "name": "Independence Day"},
            {"date": f"{year}-12-25", "localName": "Hari Raya Natal", "name": "Christmas Day"},
        ]
        
        # Approximate dynamic Islamic holidays for fallbacks if needed
        if year == 2025:
            fallbacks.extend([
                {"date": "2025-03-31", "localName": "Hari Raya Idul Fitri", "name": "Eid al-Fitr"},
                {"date": "2025-04-01", "localName": "Hari Raya Idul Fitri (Hari Kedua)", "name": "Eid al-Fitr Day 2"},
                {"date": "2025-06-06", "localName": "Hari Raya Idul Adha", "name": "Eid al-Adha"}
            ])
        elif year == 2026:
            fallbacks.extend([
                {"date": "2026-03-20", "localName": "Hari Raya Idul Fitri", "name": "Eid al-Fitr"},
                {"date": "2026-03-21", "localName": "Hari Raya Idul Fitri (Hari Kedua)", "name": "Eid al-Fitr Day 2"},
                {"date": "2026-05-27", "localName": "Hari Raya Idul Adha", "name": "Eid al-Adha"}
            ])
            
        for fb in fallbacks:
            holidays.append({
                "holiday_date": fb["date"],
                "local_name": fb["localName"],
                "english_name": fb["name"],
                "country_code": "ID",
                "global_holiday": True,
                "year": year
            })
            
    return holidays

def is_treatment_group(user_id: int) -> bool:
    """
    Deterministic A/B split logic in Python matching dbt hash logic:
    We use MD5 first character to split cohorts (8-f is treatment, 0-7 is control).
    """
    user_str = str(user_id)
    md5_hash = hashlib.md5(user_str.encode()).hexdigest()
    return md5_hash[0] in '89abcdef'

def generate_synthetic_data(num_sessions: int = 15000) -> List[Dict[str, Any]]:
    """
    Generates synthetic session transactions over the last 90 days.
    Calculates dynamic metrics displaying statistical significance for the treatment group.
    """
    # Get holidays to evaluate context active flag
    holidays = {h["holiday_date"] for h in fetch_holidays()}
    
    # Establish dynamic time bounds
    now = datetime.datetime.utcnow()
    start_date = now - datetime.timedelta(days=90)
    
    data = []
    
    # Pre-generate a list of user IDs to allow repeated sessions from same users (customer retention)
    user_pool = [random.randint(100000, 999999) for _ in range(3000)]
    
    for i in range(num_sessions):
        user_id = random.choice(user_pool)
        session_id = fake.uuid4()
        
        # Generate random timestamp within past 90 days
        random_days = random.randint(0, 90)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        session_time = start_date + datetime.timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
        date_str = session_time.strftime("%Y-%m-%d")
        
        is_holiday = date_str in holidays
        is_weekend = session_time.weekday() in (5, 6)
        context_active = is_holiday or is_weekend
        
        treatment = is_treatment_group(user_id)
        
        # CVR Logic (conversion rate simulation)
        if treatment and context_active:
            # Treatment variant on holiday/weekend gets significant lift
            conversion_prob = 0.23
        elif treatment:
            # Treatment variant on regular day (similar to baseline)
            conversion_prob = 0.14
        else:
            # Control variant has no context lift on holiday/weekend
            conversion_prob = 0.13
            
        purchased = random.random() < conversion_prob
        
        # Time-to-Purchase (TTP) friction simulation (seconds)
        time_spent_seconds = None
        clicks_count = random.randint(1, 8)
        
        if purchased:
            clicks_count = random.randint(3, 15)
            if treatment and context_active:
                # Less friction -> faster checkout!
                time_spent_seconds = int(random.lognormvariate(4.6, 0.3))  # Mean ~105s, stddev is small
            else:
                # Baseline checkout speed
                time_spent_seconds = int(random.lognormvariate(5.4, 0.4))  # Mean ~235s
                
            # Bound time-spent logically
            time_spent_seconds = max(15, min(time_spent_seconds, 1200))
        else:
            # For non-converting sessions, they browse and leave
            time_spent_seconds = random.randint(10, 300)
            
        data.append({
            "session_id": session_id,
            "user_id": user_id,
            "session_timestamp": session_time.isoformat(),
            "province": get_weighted_province(),
            "device": random.choices(["Mobile", "Desktop", "Tablet"], weights=[75, 20, 5], k=1)[0],
            "clicks": clicks_count,
            "purchased": purchased,
            "time_to_purchase_seconds": time_spent_seconds,
            "inserted_at": datetime.datetime.utcnow().isoformat()
        })
        
    return data
