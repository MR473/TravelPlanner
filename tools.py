# tools.py
import os
import time
from typing import List, Optional, Tuple, Dict, Any

import requests
from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv
from mapping import get_mapping

load_dotenv()

# -------------------------------------------------------------------
# Config: Geoapify base + API key
# -------------------------------------------------------------------
GEOAPIFY_BASE = "https://api.geoapify.com"
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

if not GEOAPIFY_API_KEY:
    print("[WARN] GEOAPIFY_API_KEY is not set in the environment.")

# -------------------------------------------------------------------
# Interest → Geoapify Places categories
# -------------------------------------------------------------------
CATEGORY_MAP: Dict[str, str] = get_mapping()

# -------------------------------------------------------------------
# Pydantic input models
# -------------------------------------------------------------------


class GeoapifyPlacesInput(BaseModel):
    """Search for POIs around a city based on user interests."""
    city: str = Field(
        ...,
        description="City name to search, e.g., 'Paris' or 'Dubai'",
    )
    interests: List[str] = Field(
        default_factory=list,
        description=(
            "List of user interests like ['museum', 'park', 'landmark']. "
            "These are mapped to Geoapify 'categories' internally."
        ),
    )
    limit: int = Field(
        20,
        ge=1,
        le=50,
        description="Maximum number of places to return (1-50).",
    )


class GeoapifyGeocodeInput(BaseModel):
    """General geocoding (not limited to cities)."""
    query: str = Field(
        ...,
        description="Free-text address/location to geocode, e.g., 'Eiffel Tower, Paris'.",
    )
    limit: int = Field(
        1,
        ge=1,
        le=20,
        description="Maximum number of geocoding results.",
    )


class GeoapifyRouteInput(BaseModel):
    """Point-to-point routing."""
    origin_lat: float = Field(..., description="Origin latitude.")
    origin_lon: float = Field(..., description="Origin longitude.")
    dest_lat: float = Field(..., description="Destination latitude.")
    dest_lon: float = Field(..., description="Destination longitude.")
    mode: str = Field(
        "drive",
        description=(
            "Routing mode, e.g. 'drive', 'walk', 'bicycle', 'transit', "
            "'truck', 'light_truck', etc."
        ),
    )


class GeoapifyIsolineInput(BaseModel):
    """
    Reachability / isolines (isochrones or isodistances).
    """
    center_lat: float = Field(..., description="Center latitude.")
    center_lon: float = Field(..., description="Center longitude.")
    mode: str = Field(
        "walk",
        description=(
            "Travel mode, e.g. 'walk', 'drive', 'bicycle', 'transit', "
            "'truck', etc."
        ),
    )
    range_type: str = Field(
        "time",
        description="Either 'time' (seconds) or 'distance' (meters).",
    )
    ranges: List[int] = Field(
        ...,
        description=(
            "List of ranges. If range_type='time', values are seconds "
            "(e.g., [600, 1200] for 10 and 20 minutes). "
            "If 'distance', values are meters."
        ),
    )


# -------------------------------------------------------------------
# Simple throttle to avoid hammering the API
# -------------------------------------------------------------------
_last_call = 0.0
_MIN_INTERVAL = 0.25  # seconds


def _throttle() -> None:
    """Rate-limit outbound requests a bit to avoid hammering the API."""
    global _last_call
    dt = time.time() - _last_call
    if dt < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - dt)
    _last_call = time.time()


# -------------------------------------------------------------------
# Low-level helpers
# -------------------------------------------------------------------


def _check_key() -> None:
    if not GEOAPIFY_API_KEY:
        raise RuntimeError("GEOAPIFY_API_KEY is not set in the environment.")


def _geoapify_get(
    path: str,
    params: Dict[str, Any],
    timeout: int = 20,
) -> Dict[str, Any]:
    """
    Generic GET request helper.

    paths:
      - /v1/geocode/search
      - /v2/places
      - /v1/routing
      - /v1/isoline
    """
    _check_key()
    _throttle()
    params = {**params, "apiKey": GEOAPIFY_API_KEY}
    url = f"{GEOAPIFY_BASE}{path}"
    r = requests.get(url, params=params, timeout=timeout)
    print(f"[Geoapify GET] {url} status:", r.status_code, r.text[:200])
    r.raise_for_status()
    return r.json()


def _geocode_city(city: str) -> Optional[Tuple[float, float]]:
    """
    Use Geoapify Forward Geocoding API to get lat/lon for a city.

    GET https://api.geoapify.com/v1/geocode/search?text={city}&type=city&apiKey=...
    """
    data = _geoapify_get(
        "/v1/geocode/search",
        {
            "text": city,
            "limit": 1,
            "type": "city",
        },
        timeout=15,
    )

    # Forward Geocoding (default JSON format) usually returns "results"
    results = data.get("results") or data.get("features")
    if not results:
        return None

    first = results[0]
    lat = first.get("lat")
    lon = first.get("lon")

    # GeoJSON-style fallback
    if lat is None or lon is None:
        props = first.get("properties", {})
        geom = first.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        lon = props.get("lon", coords[0])
        lat = props.get("lat", coords[1])

    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def _interests_to_categories(interests: List[str]) -> str:
    """
    Convert human-friendly interests into Geoapify 'categories' strings,
    using CATEGORY_MAP where possible. Unknown interests are passed through.
    """
    if not interests:
        return ""
    parts: List[str] = []
    for interest in interests:
        mapped = CATEGORY_MAP.get(interest, interest)
        parts.append(mapped)
    return ",".join(parts)


def _places_radius(lat: float, lon: float, categories: str, limit: int) -> List[Dict[str, Any]]:
    """
    Call Geoapify Places API with a circular filter around (lat, lon).

    GET https://api.geoapify.com/v2/places
        ?categories=...
        &filter=circle:lon,lat,radius
        &bias=proximity:lon,lat
        &limit=...
        &apiKey=...
    """
    params: Dict[str, Any] = {
        "limit": limit,
        "filter": f"circle:{lon},{lat},7000",  # 7km radius
        "bias": f"proximity:{lon},{lat}",
    }
    if categories:
        params["categories"] = categories

    data = _geoapify_get("/v2/places", params, timeout=20)
    features = data.get("features", [])

    places: List[Dict[str, Any]] = []
    for f in features:
        props = f.get("properties", {})
        geom = f.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        pl_lon = props.get("lon", coords[0])
        pl_lat = props.get("lat", coords[1])

        places.append(
            {
                "name": props.get("name") or props.get("formatted", ""),
                "categories": props.get("categories", []),
                "address": props.get("formatted"),
                "lat": pl_lat,
                "lon": pl_lon,
                "place_id": props.get("place_id"),
                "raw": f,
            }
        )
    return places


# -------------------------------------------------------------------
# LangChain tools
# -------------------------------------------------------------------


@tool("geoapify_places_search", args_schema=GeoapifyPlacesInput)
def geoapify_places_search(city: str, interests: List[str], limit: int = 20) -> dict:
    """
    Search Geoapify Places for POIs in a given city matching user interests.

    - Geocodes the city to latitude/longitude.
    - Maps human-friendly interests to Geoapify 'categories'.
    - Queries Geoapify Places API with a circular filter around the city center.
    """
    if not GEOAPIFY_API_KEY:
        return {"error": "Missing GEOAPIFY_API_KEY environment variable"}

    coords = _geocode_city(city)
    if coords is None:
        return {
            "error": f"Could not geocode city '{city}' via Geoapify.",
            "city": city,
        }
    lat, lon = coords

    categories = _interests_to_categories(interests)

    try:
        places = _places_radius(lat, lon, categories, limit)
    except requests.HTTPError as e:
        return {
            "error": f"Places HTTP error: {e}",
            "city": city,
            "lat": lat,
            "lon": lon,
        }
    except Exception as e:
        return {
            "error": f"Unexpected error while searching places: {e}",
            "city": city,
            "lat": lat,
            "lon": lon,
        }

    return {
        "city": city,
        "interests": interests,
        "lat": lat,
        "lon": lon,
        "count": len(places),
        "places": places,
    }


@tool("geoapify_geocode", args_schema=GeoapifyGeocodeInput)
def geoapify_geocode(query: str, limit: int = 1) -> dict:
    """
    General-purpose geocoding tool using Geoapify Forward Geocoding API.

    GET https://api.geoapify.com/v1/geocode/search?text=...&limit=...&apiKey=...
    """
    if not GEOAPIFY_API_KEY:
        return {"error": "Missing GEOAPIFY_API_KEY environment variable"}

    try:
        data = _geoapify_get(
            "/v1/geocode/search",
            {
                "text": query,
                "limit": limit,
            },
            timeout=15,
        )
    except requests.HTTPError as e:
        return {"error": f"Geocode HTTP error: {e}", "query": query}
    except Exception as e:
        return {"error": f"Unexpected error while geocoding: {e}", "query": query}

    return {
        "query": query,
        "raw": data,
    }


@tool("geoapify_route", args_schema=GeoapifyRouteInput)
def geoapify_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    mode: str = "drive",
) -> dict:
    """
    Point-to-point routing using Geoapify Routing API.

    GET https://api.geoapify.com/v1/routing
        ?waypoints=lat1,lon1|lat2,lon2
        &mode=drive
        &apiKey=...

    NOTE: waypoints use 'latitude,longitude'.
    """
    if not GEOAPIFY_API_KEY:
        return {"error": "Missing GEOAPIFY_API_KEY environment variable"}

    waypoints = f"{origin_lat},{origin_lon}|{dest_lat},{dest_lon}"

    try:
        data = _geoapify_get(
            "/v1/routing",
            {
                "waypoints": waypoints,
                "mode": mode,
            },
            timeout=20,
        )
    except requests.HTTPError as e:
        return {"error": f"Routing HTTP error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error while routing: {e}"}

    return {
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": dest_lat, "lon": dest_lon},
        "mode": mode,
        "raw": data,
    }


@tool("geoapify_isolines", args_schema=GeoapifyIsolineInput)
def geoapify_isolines(
    center_lat: float,
    center_lon: float,
    mode: str,
    range_type: str,
    ranges: List[int],
) -> dict:
    """
    Reachability / Isolines using Geoapify Isoline API.

    GET https://api.geoapify.com/v1/isoline
        ?lat=...
        &lon=...
        &type=time|distance
        &mode=...
        &range=900,1800,...
        &apiKey=...
    """
    if not GEOAPIFY_API_KEY:
        return {"error": "Missing GEOAPIFY_API_KEY environment variable"}

    if range_type not in {"time", "distance"}:
        return {"error": "range_type must be 'time' or 'distance'."}

    if not ranges:
        return {"error": "ranges must be a non-empty list of integers."}

    range_str = ",".join(str(r) for r in ranges)

    try:
        data = _geoapify_get(
            "/v1/isoline",
            {
                "lat": center_lat,
                "lon": center_lon,
                "type": range_type,
                "mode": mode,
                "range": range_str,
            },
            timeout=20,
        )
    except requests.HTTPError as e:
        return {"error": f"Isoline HTTP error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error while requesting isolines: {e}"}

    return {
        "center": {"lat": center_lat, "lon": center_lon},
        "mode": mode,
        "range_type": range_type,
        "ranges": ranges,
        "raw": data,
    }
