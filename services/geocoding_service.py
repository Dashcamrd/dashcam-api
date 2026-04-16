"""
Geocoding Service - Convert GPS coordinates to human-readable Arabic addresses

Uses Google Maps Geocoding API for accurate Saudi/Arabic addresses.
Falls back to OpenStreetMap Nominatim if Google is unavailable.
Aggressive caching with coordinate rounding for high hit rates.
"""
import requests
import logging
import os
import threading
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)


class GeocodingService:
    GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

    _cache: OrderedDict = OrderedDict()
    _cache_max_size = 10000
    _lock = threading.Lock()

    # Nominatim rate limiting (fallback only)
    _last_nominatim_time = 0.0
    _nominatim_interval = 1.1

    @classmethod
    def _get_google_key(cls) -> Optional[str]:
        return os.getenv("GOOGLE_MAPS_API_KEY")

    @classmethod
    def reverse_geocode(cls, latitude: float, longitude: float) -> Optional[str]:
        """Convert coordinates to a human-readable Arabic address."""
        cache_key = f"{round(latitude, 3)},{round(longitude, 3)}"

        with cls._lock:
            if cache_key in cls._cache:
                cls._cache.move_to_end(cache_key)
                return cls._cache[cache_key]

        google_key = cls._get_google_key()
        if google_key:
            address = cls._google_geocode(latitude, longitude, google_key)
            if address:
                cls._add_to_cache(cache_key, address)
                return address

        address = cls._nominatim_geocode(latitude, longitude)
        if address:
            cls._add_to_cache(cache_key, address)
            return address

        return None

    @classmethod
    def _google_geocode(cls, lat: float, lng: float, api_key: str) -> Optional[str]:
        try:
            resp = requests.get(
                cls.GOOGLE_GEOCODE_URL,
                params={
                    "latlng": f"{lat},{lng}",
                    "key": api_key,
                    "language": "ar",
                    "result_type": "street_address|route|neighborhood|sublocality|locality",
                },
                timeout=3,
            )
            if resp.status_code != 200:
                logger.warning(f"Google Geocoding HTTP {resp.status_code}")
                return None

            data = resp.json()
            if data.get("status") != "OK" or not data.get("results"):
                if data.get("status") == "REQUEST_DENIED":
                    logger.error(f"Google Geocoding denied: {data.get('error_message', '')}")
                return None

            return cls._format_google_result(data["results"])
        except requests.Timeout:
            return None
        except Exception as e:
            logger.error(f"Google geocoding error: {e}")
            return None

    @classmethod
    def _format_google_result(cls, results: list) -> Optional[str]:
        """Pick the most useful result and build a concise Arabic address."""
        if not results:
            return None

        best = results[0]
        components = best.get("address_components", [])

        road = None
        neighborhood = None
        city = None

        for comp in components:
            types = comp.get("types", [])
            name = comp.get("long_name", "")
            if not name:
                continue
            if "route" in types:
                road = name
            elif "neighborhood" in types or "sublocality_level_1" in types or "sublocality" in types:
                neighborhood = name
            elif "locality" in types:
                city = name
            elif "administrative_area_level_1" in types and not city:
                city = name

        parts = [p for p in [city, neighborhood, road] if p]
        if not parts:
            formatted = best.get("formatted_address", "")
            if formatted:
                segments = [s.strip() for s in formatted.split(",")]
                return "، ".join(segments[:3])
            return None

        return "، ".join(parts)

    @classmethod
    def _nominatim_geocode(cls, lat: float, lng: float) -> Optional[str]:
        """Fallback: OpenStreetMap Nominatim (rate-limited to 1 req/sec)."""
        import time

        with cls._lock:
            now = time.monotonic()
            elapsed = now - cls._last_nominatim_time
            if elapsed < cls._nominatim_interval:
                wait = cls._nominatim_interval - elapsed
                if wait > 0.8:
                    return None
                time.sleep(wait)
            cls._last_nominatim_time = time.monotonic()

        try:
            resp = requests.get(
                cls.NOMINATIM_URL,
                params={
                    "lat": lat,
                    "lon": lng,
                    "format": "json",
                    "addressdetails": 1,
                    "accept-language": "ar,en",
                    "zoom": 16,
                },
                headers={"User-Agent": "DashcamRD-RoadApp/1.0 (fahad@dashcamrd.com)"},
                timeout=2,
            )
            if resp.status_code == 200:
                data = resp.json()
                return cls._format_nominatim(data.get("address", {}))
            return None
        except Exception:
            return None

    @classmethod
    def _format_nominatim(cls, addr: dict) -> Optional[str]:
        parts = []
        city = addr.get("city") or addr.get("town") or addr.get("village")
        suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter")
        road = addr.get("road")
        if city:
            parts.append(city)
        if suburb and suburb != city:
            parts.append(suburb)
        if road and road not in parts:
            parts.append(road)
        return "، ".join(parts[:3]) if parts else None

    @classmethod
    def _add_to_cache(cls, key: str, value: str):
        with cls._lock:
            if key in cls._cache:
                cls._cache.move_to_end(key)
            else:
                if len(cls._cache) >= cls._cache_max_size:
                    cls._cache.popitem(last=False)
                cls._cache[key] = value

    @classmethod
    def get_location_name(cls, latitude: Optional[float], longitude: Optional[float]) -> str:
        """Get location name with fallback to raw coordinates."""
        if not latitude or not longitude:
            return "Location unavailable"
        address = cls.reverse_geocode(latitude, longitude)
        if address:
            return address
        return f"{latitude:.4f}, {longitude:.4f}"

    @classmethod
    def should_geocode(cls, old_lat: Optional[float], old_lng: Optional[float],
                       new_lat: float, new_lng: float) -> bool:
        """Check if coordinates changed enough to warrant re-geocoding (~111m)."""
        if old_lat is None or old_lng is None:
            return True
        return (round(old_lat, 3) != round(new_lat, 3) or
                round(old_lng, 3) != round(new_lng, 3))
