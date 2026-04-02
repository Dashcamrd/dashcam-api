"""
Geocoding Service - Convert GPS coordinates to human-readable addresses

Uses OpenStreetMap Nominatim with proper rate limiting (1 req/sec policy)
and aggressive coordinate rounding for high cache hit rates.
"""
import requests
import logging
import time
import threading
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    Service for reverse geocoding (coordinates -> address).
    Uses OpenStreetMap Nominatim API with rate limiting and LRU cache.
    """

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

    _cache: OrderedDict = OrderedDict()
    _cache_max_size = 5000
    _last_request_time = 0.0
    _rate_limit_interval = 1.1  # seconds between requests (Nominatim requires >= 1s)
    _lock = threading.Lock()

    @classmethod
    def reverse_geocode(cls, latitude: float, longitude: float) -> Optional[str]:
        """
        Convert coordinates to a human-readable address.
        Returns cached result if available; respects Nominatim rate limit.
        """
        # Round to 3 decimal places (~111m precision) for better cache hits
        cache_key = f"{round(latitude, 3)},{round(longitude, 3)}"

        if cache_key in cls._cache:
            cls._cache.move_to_end(cache_key)
            return cls._cache[cache_key]

        # Rate limit: wait if we called too recently
        with cls._lock:
            now = time.monotonic()
            elapsed = now - cls._last_request_time
            if elapsed < cls._rate_limit_interval:
                wait = cls._rate_limit_interval - elapsed
                if wait > 0.8:
                    return None  # Skip this call instead of blocking the request
                time.sleep(wait)
            cls._last_request_time = time.monotonic()

        try:
            response = requests.get(
                cls.NOMINATIM_URL,
                params={
                    'lat': latitude,
                    'lon': longitude,
                    'format': 'json',
                    'addressdetails': 1,
                    'accept-language': 'ar,en',
                    'zoom': 16,
                },
                headers={'User-Agent': 'DashcamRD-RoadApp/1.0 (fahad@dashcamrd.com)'},
                timeout=2,
            )

            if response.status_code == 200:
                data = response.json()
                address = cls._format_address(data.get('address', {}))
                if address:
                    cls._add_to_cache(cache_key, address)
                return address

            if response.status_code == 429:
                logger.debug("Nominatim rate limited, skipping")
            else:
                logger.warning(f"Geocoding API returned status {response.status_code}")
            return None

        except requests.Timeout:
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None

    @classmethod
    def _format_address(cls, address_parts: dict) -> Optional[str]:
        """Format address parts into a concise, readable string."""
        components = []

        if road := address_parts.get('road'):
            components.append(road)

        suburb = (address_parts.get('suburb') or
                  address_parts.get('neighbourhood') or
                  address_parts.get('quarter'))
        if suburb:
            components.append(suburb)

        city = (address_parts.get('city') or
                address_parts.get('town') or
                address_parts.get('village'))
        if city and city not in components:
            components.append(city)

        if state := address_parts.get('state'):
            if state not in components:
                components.append(state)

        return ', '.join(components[:3]) if components else None

    @classmethod
    def _add_to_cache(cls, key: str, value: str):
        """Add item to LRU cache with size limit."""
        if key in cls._cache:
            cls._cache.move_to_end(key)
        else:
            if len(cls._cache) >= cls._cache_max_size:
                cls._cache.popitem(last=False)
            cls._cache[key] = value

    @classmethod
    def get_location_name(cls, latitude: Optional[float], longitude: Optional[float]) -> str:
        """
        Get location name from coordinates with fallback to raw coordinates.
        """
        if not latitude or not longitude:
            return "Location unavailable"

        address = cls.reverse_geocode(latitude, longitude)
        if address:
            return address

        return f"{latitude:.4f}, {longitude:.4f}"
