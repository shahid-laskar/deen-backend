"""
Qibla Service
=============
Calculates the Qibla direction (bearing toward the Kaaba in Mecca)
using the Great Circle formula. No external API required.

Kaaba coordinates: 21.4225° N, 39.8262° E

Also provides mosque finder using OpenStreetMap Overpass API (free, no key).
"""

import math
from typing import Any

import httpx

# Kaaba, Masjid al-Haram, Mecca
KAABA_LAT = 21.4225
KAABA_LNG = 39.8262


def calculate_qibla(lat: float, lng: float) -> dict:
    """
    Return Qibla bearing (degrees from True North, clockwise) for a given location.

    Uses the Great Circle formula:
        bearing = atan2(
            sin(Δlng) * cos(lat_kaaba),
            cos(lat) * sin(lat_kaaba) - sin(lat) * cos(lat_kaaba) * cos(Δlng)
        )
    """
    lat_r = math.radians(lat)
    lng_r = math.radians(lng)
    kaaba_lat_r = math.radians(KAABA_LAT)
    kaaba_lng_r = math.radians(KAABA_LNG)

    delta_lng = kaaba_lng_r - lng_r

    x = math.sin(delta_lng) * math.cos(kaaba_lat_r)
    y = (
        math.cos(lat_r) * math.sin(kaaba_lat_r)
        - math.sin(lat_r) * math.cos(kaaba_lat_r) * math.cos(delta_lng)
    )

    bearing_rad = math.atan2(x, y)
    bearing_deg = (math.degrees(bearing_rad) + 360) % 360

    # Distance to Kaaba using Haversine
    R = 6371  # Earth radius km
    dlat = kaaba_lat_r - lat_r
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat_r) * math.cos(kaaba_lat_r) * math.sin(delta_lng / 2) ** 2
    )
    distance_km = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    compass = _bearing_to_compass(bearing_deg)

    return {
        "qibla_bearing": round(bearing_deg, 2),
        "compass_direction": compass,
        "distance_to_kaaba_km": round(distance_km, 1),
        "latitude": lat,
        "longitude": lng,
        "kaaba_latitude": KAABA_LAT,
        "kaaba_longitude": KAABA_LNG,
    }


def _bearing_to_compass(bearing: float) -> str:
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    idx = round(bearing / 22.5) % 16
    return directions[idx]


async def find_nearby_mosques(
    lat: float,
    lng: float,
    radius_m: int = 5000,
    limit: int = 20,
) -> list[dict]:
    """
    Find nearby mosques using OpenStreetMap Overpass API.
    Completely free, no API key required.
    """
    overpass_url = "https://overpass-api.de/api/interpreter"

    query = f"""
[out:json][timeout:25];
(
  node["amenity"="place_of_worship"]["religion"="muslim"](around:{radius_m},{lat},{lng});
  way["amenity"="place_of_worship"]["religion"="muslim"](around:{radius_m},{lat},{lng});
  relation["amenity"="place_of_worship"]["religion"="muslim"](around:{radius_m},{lat},{lng});
);
out center {limit};
"""

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(overpass_url, data={"data": query})
        resp.raise_for_status()
        data = resp.json()

    mosques = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        # Get coordinates (node has lat/lon directly; way/relation use center)
        if element["type"] == "node":
            mlat, mlng = element.get("lat"), element.get("lon")
        else:
            center = element.get("center", {})
            mlat, mlng = center.get("lat"), center.get("lon")

        if not mlat or not mlng:
            continue

        distance = _haversine_distance(lat, lng, mlat, mlng)

        mosque = {
            "id": element["id"],
            "osm_type": element["type"],
            "name": tags.get("name") or tags.get("name:en") or "Mosque",
            "arabic_name": tags.get("name:ar"),
            "latitude": mlat,
            "longitude": mlng,
            "distance_m": round(distance),
            "address": _build_address(tags),
            "opening_hours": tags.get("opening_hours"),
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "website": tags.get("website") or tags.get("contact:website"),
            "wheelchair": tags.get("wheelchair"),
            "female_prayer_room": tags.get("female:prayer_room") or tags.get("women_prayer_area"),
            "wudu_facility": tags.get("toilets:access") == "yes" or False,
        }
        mosques.append(mosque)

    # Sort by distance
    mosques.sort(key=lambda m: m["distance_m"])
    return mosques[:limit]


def _haversine_distance(lat1, lng1, lat2, lng2) -> float:
    """Distance in metres between two coordinates."""
    R = 6_371_000
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _build_address(tags: dict) -> str:
    parts = filter(None, [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city"),
        tags.get("addr:postcode"),
        tags.get("addr:country"),
    ])
    return ", ".join(parts)
