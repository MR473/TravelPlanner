from dotenv import load_dotenv
import os
import json

from tools import (
    geoapify_geocode,
    geoapify_places_search,
    geoapify_route,
    geoapify_isolines,
)

load_dotenv()

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
print("==========================================")
print(" API KEY LOADED? :", GEOAPIFY_API_KEY is not None)
print("==========================================\n")


def pretty(title, data):
    print(f"\n========== {title} ==========")
    print(json.dumps(data, indent=2))
    print("==========================================")


# ---------------------------------------------------------
# TEST 1: GEOCODING
# ---------------------------------------------------------
geo_result = geoapify_geocode.func(
    query="NC State University, Raleigh, NC",
    limit=1,
)
pretty("TEST 1: Geocoding → 'NC State University'", geo_result)


# ---------------------------------------------------------
# TEST 2: PLACES SEARCH
# ---------------------------------------------------------
places_result = geoapify_places_search.func(
    city="Raleigh",
    interests=["entertainment"],
    limit=5,
)

# Show only place name + address for readability
places_clean = {
    "city": places_result.get("city"),
    "count": places_result.get("count"),
    "places": [
        {
            "name": p.get("name"),
            "address": p.get("address"),
            "categories": p.get("categories"),
            "lat": p.get("lat"),
            "lon": p.get("lon"),
        }
        for p in places_result.get("places", [])
    ],
}

pretty("TEST 2: Places Search → Raleigh (attractions + entertainment)", places_clean)


# ---------------------------------------------------------
# TEST 3: ROUTING
# ---------------------------------------------------------
route_result = geoapify_route.func(
    origin_lat=35.78539684435315, origin_lon=-78.68115048932215,  
    dest_lat=35.83892902155767, dest_lon=-78.68014353635571,      
    mode="drive",
)

# Extract summary info
try:
    route_info = {
        "distance_meters": route_result["raw"]["features"][0]["properties"]["distance"],
        "time_seconds": route_result["raw"]["features"][0]["properties"]["time"],
        "mode": route_result["mode"],
        "origin": route_result["origin"],
        "destination": route_result["destination"],
    }
except Exception:
    route_info = route_result  # fallback

pretty("TEST 3: Route → NC State → CrabTree", route_info)


# ---------------------------------------------------------
# TEST 4: REACHABILITY / ISOLINES
# ---------------------------------------------------------
isolines_result = geoapify_isolines.func(
    center_lat=35.78539684435315, center_lon=-78.68115048932215,
    mode="drive",
    range_type="time",
    ranges=[1800, 3600],
)

# Show only isoline metadata (GeoJSON is large)
isolines_clean = {
    "center_lat": 35.78539684435315,
    "center_lon": -78.68115048932215,
    "mode": "drive",
    "range_type": "time",
    "ranges": [1800, 3600],
    "num_polygons": len(isolines_result["raw"].get("features", [])),
}

pretty("TEST 4: Reachability → NC State (30 & 60 min drive)", isolines_clean)

print("\nALL TESTS FINISHED SUCCESSFULLY ✔️\n")
