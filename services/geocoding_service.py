"""
Geocoding Service - Convert GPS coordinates to human-readable addresses
"""
import requests
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class GeocodingService:
    """
    Service for reverse geocoding (coordinates -> address)
    Uses OpenStreetMap Nominatim API (free, no API key required)
    """
    
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
    
    # Cache for recently geocoded locations to reduce API calls
    _cache = {}
    _cache_max_size = 100
    
    @classmethod
    def reverse_geocode(cls, latitude: float, longitude: float) -> Optional[str]:
        """
        Convert coordinates to a human-readable address.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Human-readable address string or None if geocoding fails
        """
        # Check cache first (round to 4 decimal places for cache key)
        cache_key = f"{round(latitude, 4)},{round(longitude, 4)}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        try:
            # Make request to Nominatim API
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'addressdetails': 1,
                'zoom': 18,  # Street-level detail
            }
            
            headers = {
                'User-Agent': 'RoadApp/1.0'  # Nominatim requires User-Agent
            }
            
            response = requests.get(
                cls.NOMINATIM_URL,
                params=params,
                headers=headers,
                timeout=3  # 3 second timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                address = cls._format_address(data.get('address', {}))
                
                # Cache the result
                cls._add_to_cache(cache_key, address)
                
                return address
            else:
                logger.warning(f"Geocoding API returned status {response.status_code}")
                return None
                
        except requests.Timeout:
            logger.warning(f"Geocoding timeout for ({latitude}, {longitude})")
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None
    
    @classmethod
    def _format_address(cls, address_parts: dict) -> str:
        """
        Format address parts into a concise, readable string.
        
        Priority order:
        1. Road/Street name
        2. Suburb/Neighborhood
        3. City/Town
        4. State
        5. Country
        """
        components = []
        
        # Road/Street
        if road := address_parts.get('road'):
            components.append(road)
        
        # Suburb/Neighborhood
        suburb = (address_parts.get('suburb') or 
                 address_parts.get('neighbourhood') or 
                 address_parts.get('quarter'))
        if suburb:
            components.append(suburb)
        
        # City/Town
        city = (address_parts.get('city') or 
               address_parts.get('town') or 
               address_parts.get('village'))
        if city and city not in components:
            components.append(city)
        
        # State
        if state := address_parts.get('state'):
            if state not in components:
                components.append(state)
        
        # Country
        if country := address_parts.get('country'):
            if country not in components:
                components.append(country)
        
        # Join with commas (max 3 components for brevity)
        return ', '.join(components[:3]) if components else None
    
    @classmethod
    def _add_to_cache(cls, key: str, value: str):
        """Add item to cache with size limit"""
        if len(cls._cache) >= cls._cache_max_size:
            # Remove oldest item (FIFO)
            cls._cache.pop(next(iter(cls._cache)))
        cls._cache[key] = value
    
    @classmethod
    def get_location_name(cls, latitude: Optional[float], longitude: Optional[float]) -> str:
        """
        Get location name from coordinates with fallback to raw coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Human-readable location name or "Location unavailable"
        """
        if not latitude or not longitude:
            return "Location unavailable"
        
        # Try reverse geocoding
        address = cls.reverse_geocode(latitude, longitude)
        
        if address:
            return address
        
        # Fallback to coordinates with 4 decimal places
        return f"{latitude:.4f}, {longitude:.4f}"

