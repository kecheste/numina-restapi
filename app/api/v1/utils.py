"""Utility endpoints (timezone, place search). No auth required for timezone or place lookup."""

from urllib.parse import quote

import httpx
from fastapi import APIRouter, Query

from timezonefinder import TimezoneFinder

from app.core.config import settings

router = APIRouter()
_tf: TimezoneFinder | None = None

MAPBOX_GEOCODING_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"


def _get_tf() -> TimezoneFinder:
    global _tf
    if _tf is None:
        _tf = TimezoneFinder()
    return _tf


@router.get("/timezone")
async def get_timezone(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
) -> dict[str, str]:
    """Return IANA timezone for a point (e.g. America/New_York). Used by frontend when user selects birth place."""
    tz_name = _get_tf().timezone_at(lat=lat, lng=lng)
    return {"timezone": tz_name or "UTC"}


@router.get("/places/search")
async def search_places(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(5, ge=1, le=10),
) -> dict:
    """
    Proxy place search to Mapbox Geocoding API. Keeps the Mapbox token on the server.
    Returns the same feature shape the frontend expects (id, place_name, center, geometry).
    """
    if not settings.mapbox_access_token:
        return {"type": "FeatureCollection", "features": []}
    query = q.strip()[:200]
    params = {
        "access_token": settings.mapbox_access_token,
        "limit": limit,
        "types": "place,locality,address,region",
    }
    path_query = quote(query, safe="")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{MAPBOX_GEOCODING_URL}/{path_query}.json",
            params=params,
        )
    if resp.status_code != 200:
        return {"type": "FeatureCollection", "features": []}
    data = resp.json()
    if not isinstance(data, dict) or "features" not in data:
        return {"type": "FeatureCollection", "features": []}
    return data
