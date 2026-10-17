"""
routers/geo.py
────────────────────────────────────────────────────────────────────────────
GET /api/geo/reverse?lat=&lng=

Public endpoint — no auth required.
Delegates to services.external.reverse_geocode which is fault-tolerant:
  - 5 s httpx timeout
  - Falls back to "lat, lng" string on any failure
  - Never raises to the caller
"""
from fastapi import APIRouter, Query
from app.schemas import ReverseGeoOut
from app.services.external import reverse_geocode

router = APIRouter()


@router.get("/reverse", response_model=ReverseGeoOut)
async def geo_reverse(
    lat: float = Query(..., description="Latitude", ge=-90.0,  le=90.0),
    lng: float = Query(..., description="Longitude", ge=-180.0, le=180.0),
) -> ReverseGeoOut:
    """
    Reverse-geocode a coordinate pair via Nominatim.
    Always returns a 200 response — falls back to "lat, lng" if the
    external service is unavailable or takes longer than 5 seconds.
    """
    result = await reverse_geocode(lat, lng)
    return ReverseGeoOut(address=result["address"])
