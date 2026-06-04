import requests
import datetime
import dlt
from typing import List, Dict, Any

@dlt.resource(write_disposition="replace", name="indonesian_holidays")
def indonesian_holidays():
    """
    Fetches public holidays in Indonesia for 2015 and 2016 (matching the Retailrocket dataset timeframe).
    Includes robust fallback static holidays.
    """
    years = [2015, 2016]
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
            print(f"Warning: Nager.Date API fetch failed for year {year} ({e}). Using fallback holidays.")
            
        # Fallback public holidays for Indonesia in 2015/2016
        fallbacks = [
            {"date": f"{year}-01-01", "localName": "Tahun Baru Masehi", "name": "New Year's Day"},
            {"date": f"{year}-05-01", "localName": "Hari Buruh Internasional", "name": "International Workers' Day"},
            {"date": f"{year}-06-01", "localName": "Hari Lahir Pancasila", "name": "Pancasila Day"},
            {"date": f"{year}-08-17", "localName": "Hari Kemerdekaan RI", "name": "Independence Day"},
            {"date": f"{year}-12-25", "localName": "Hari Raya Natal", "name": "Christmas Day"},
        ]
        
        # Add dynamic lunar-calendar fallbacks specifically for 2015/2016
        if year == 2015:
            fallbacks.extend([
                {"date": "2015-03-21", "localName": "Hari Suci Nyepi", "name": "Nyepi"},
                {"date": "2015-07-17", "localName": "Hari Raya Idul Fitri", "name": "Eid al-Fitr"},
                {"date": "2015-07-18", "localName": "Hari Raya Idul Fitri (Hari Kedua)", "name": "Eid al-Fitr Day 2"},
                {"date": "2015-09-24", "localName": "Hari Raya Idul Adha", "name": "Eid al-Adha"}
            ])
        elif year == 2016:
            fallbacks.extend([
                {"date": "2016-03-09", "localName": "Hari Suci Nyepi", "name": "Nyepi"},
                {"date": "2016-07-06", "localName": "Hari Raya Idul Fitri", "name": "Eid al-Fitr"},
                {"date": "2016-07-07", "localName": "Hari Raya Idul Fitri (Hari Kedua)", "name": "Eid al-Fitr Day 2"},
                {"date": "2016-09-12", "localName": "Hari Raya Idul Adha", "name": "Eid al-Adha"}
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
            
    yield holidays
