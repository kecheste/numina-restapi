"""Utility endpoints (e.g. timezone from coordinates). No auth required for timezone lookup."""

from fastapi import APIRouter, Query

from timezonefinder import TimezoneFinder

router = APIRouter()
_tf: TimezoneFinder | None = None


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
