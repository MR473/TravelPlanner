# tools.py
import os
import time
from typing import List
import requests
from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

OTM_BASE = "https://api.opentripmap.com/0.1/en"
# Single source of truth for the key
OTM_API_KEY = os.getenv("OPENTRIPMAP_API_KEY")

# Map simple interests → OpenTripMap kinds
KIND_MAP = {
    "museum": "museums",
    "park": "urban_environment,parks",
    "landmark": "interesting_places,historic,architecture",
    "restaurant": "foods",
    "entertainment": "theatres_and_entertainments,amusements",
}

class OTMSearchInput(BaseModel):
    city: str = Field(..., description="City name to search, e.g., 'Paris' or 'Dubai'")
    interests: List[str] = Field(
        default_factory=list,
        description=(
            "List of user interests like ['museum', 'park', 'landmark']. "
            "These are mapped to OpenTripMap 'kinds' internally."
        ),
    )
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of places to return (1-50).",
    )

_last_call = 0.0
_MIN_INTERVAL = 0.25  # seconds, to be nice to the API


def _throttle() -> None:
    """Rate-limit outbound requests a bit to avoid hammering the API."""
    global _last_call
    dt = time.time() - _last_call
    if dt < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - dt)
    _last_call = time.time()


def _geocode_city(city: str):
    """Use OTM /places/geoname to get lat/lon for a city."""
    if not OTM_API_KEY:
        raise RuntimeError("OPENTRIPMAP_API_KEY is not set in the environment.")

    _throttle()
    r = requests.get(
        f"{OTM_BASE}/places/geoname",
        params={"name": city, "apikey": OTM_API_KEY},
        timeout=15,
    )
    print("Geocode status:", r.status_code, r.text[:200])  # DEBUG
    r.raise_for_status()

    data = r.json()
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is None or lon is None:
        # Return None so the tool can handle it gracefully
        return None
    return float(lat), float(lon)


def _search_radius(lat: float, lon: float, kinds: str, limit: int):
    """Call OTM /places/radius, return raw list of places."""
    if not OTM_API_KEY:
        raise RuntimeError("OPENTRIPMAP_API_KEY is not set in the environment.")

    _throttle()
    params = {
        "apikey": OTM_API_KEY,
        "radius": 7000,
        "lon": lon,
        "lat": lat,
        "rate": 2,         # filter to higher-rated POIs
        "format": "json",
        "limit": limit,
    }
    if kinds:
        params["kinds"] = kinds

    r = requests.get(
        f"{OTM_BASE}/places/radius",
        params=params,
        timeout=20,
    )
    print("Search status:", r.status_code, r.text[:200])  # DEBUG
    r.raise_for_status()
    return r.json()


def _interests_to_kinds(interests: List[str]) -> str:
    """
    Convert human-friendly interests into OTM 'kinds' strings,
    using KIND_MAP where possible. Unknown interests are passed through.
    """
    if not interests:
        return ""
    parts: List[str] = []
    for interest in interests:
        mapped = KIND_MAP.get(interest, interest)
        parts.append(mapped)
    return ",".join(parts)


@tool("opentripmap_search", args_schema=OTMSearchInput)
def opentripmap_search(city: str, interests: List[str], limit: int = 10) -> dict:
    """
    Search OpenTripMap for POIs in a given city matching user interests.

    - Uses OpenTripMap geocoding to resolve the city to latitude/longitude.
    - Maps user-friendly interests (e.g., 'museum', 'park') into OTM 'kinds'.
    - Queries /places/radius and returns a structured dictionary.
    """
    if not OTM_API_KEY:
        return {"error": "Missing OPENTRIPMAP_API_KEY environment variable"}

    # 1) Geocode the city
    coords = _geocode_city(city)
    if coords is None:
        return {
            "error": f"Could not geocode city '{city}' via OpenTripMap.",
            "city": city,
        }
    lat, lon = coords

    # 2) Map interests → OTM 'kinds'
    kinds = _interests_to_kinds(interests)

    # 3) Search for POIs
    try:
        places = _search_radius(lat, lon, kinds, limit)
    except requests.HTTPError as e:
        return {
            "error": f"Search HTTP error: {e}",
            "city": city,
            "lat": lat,
            "lon": lon,
        }
    except Exception as e:
        return {
            "error": f"Unexpected error while searching: {e}",
            "city": city,
            "lat": lat,
            "lon": lon,
        }

    # 4) Return a clean structured result
    return {
        "city": city,
        "interests": interests,
        "lat": lat,
        "lon": lon,
        "count": len(places),
        "places": places,
    }
