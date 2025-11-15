# tool.py
import os
import time
from typing import List
import requests
from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

OTM_BASE = "https://api.opentripmap.com/0.1/en"
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
    city: str = Field(..., description="City name to search, e.g., 'Paris'")
    interests: List[str] = Field(
        default_factory=list,
        description="List of user interests like ['museum', 'park', 'landmark']",
    )
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of places to return (1–50).",
    )


_last_call = 0.0
_MIN_INTERVAL = 0.25  # seconds, to be nice to the API


def _throttle():
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
    r.raise_for_status()
    data = r.json()
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def _search_radius(lat: float, lon: float, kinds: str, limit: int):
    """Call OTM /places/radius, return raw list."""
    _throttle()
    r = requests.get(
        f"{OTM_BASE}/places/radius",
        params={
            "apikey": OTM_API_KEY,
            "radius": 7000,
            "lon": lon,
            "lat": lat,
            "kinds": kinds,
            "rate": 2,
            "format": "json",
            "limit": limit,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


@tool("opentripmap_search", args_schema=OTMSearchInput)
def opentripmap_search_tool(city: str, interests: List[str], limit: int = 10):
    """
    Search for interesting tourist places in a city using the OpenTripMap API.

    Returns a list of simple dicts, each with:
    - name
    - kind
    - lat, lon
    - approx_rating (fake 1-5 star scale from OTM 'rate')
    """
    if not OTM_API_KEY:
        return {
            "error": "OPENTRIPMAP_API_KEY not set. Please configure it in your environment."
        }

    coords = _geocode_city(city)
    if not coords:
        return {"error": f"Could not geocode city '{city}' via OpenTripMap."}

    lat, lon = coords

    # Map interests -> OTM kinds, fallback to generic
    kinds_set = set()
    for i in interests or []:
        mapped = KIND_MAP.get(i.lower())
        if mapped:
            kinds_set.update(mapped.split(","))
    kinds = ",".join(kinds_set) if kinds_set else "interesting_places"

    try:
        results = _search_radius(lat, lon, kinds=kinds, limit=limit)
    except Exception as e:
        return {"error": f"Error calling OpenTripMap: {e}"}

    places = []
    for item in results:
        name = item.get("name") or "Unknown place"
        point = item.get("point") or {}
        kinds_str = item.get("kinds") or ""
        primary_kind = kinds_str.split(",")[0] if kinds_str else "poi"
        rate = item.get("rate", 1)
        approx_rating = {1: 4.2, 2: 4.5, 3: 4.8}.get(rate, 4.4)

        places.append(
            {
                "name": name,
                "kind": primary_kind,
                "lat": float(point.get("lat", lat)),
                "lon": float(point.get("lon", lon)),
                "approx_rating": approx_rating,
            }
        )

    return {
        "city": city,
        "interests": interests,
        "places": places,
    }
