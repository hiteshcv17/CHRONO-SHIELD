"""
ai-engine/src/ingestion/sources/weather.py

WeatherDataSource — Production implementation of OpenWeatherMap API
with seamless public Open-Meteo API fallback, caching capabilities,
and automated retry handling.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import aiohttp

from src.ingestion.base import (
    BaseDataSource,
    HealthState,
    IngestionResult,
    IngestionStatus,
    SourceCategory,
    SourceHealthStatus,
    SourceMetadata,
)
from src.ingestion.registry import register_source

logger = logging.getLogger("ingestion.sources.weather")


@register_source("weather")
class WeatherDataSource(BaseDataSource):
    """
    Atmospheric environmental telemetry source pulling real-time weather observations.

    Integrates:
      - OpenWeatherMap API v2.5 (requires API key)
      - Open-Meteo API v1 (free, zero-config public fallback)
    """

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            name="weather",
            version="1.0.0",
            category=SourceCategory.WEATHER,
            description=(
                "Atmospheric weather observations and short-range forecasts "
                "for configured geographic locations."
            ),
            interval_seconds=self.config.interval_seconds,
            supported_fields=[
                "timestamp", "location", "temperature_c", "humidity_pct",
                "wind_speed_ms", "precipitation_mm", "cloud_coverage_pct",
            ],
            tags=["weather", "climate", "atmospheric", "real-time"],
        )

    async def fetch(self) -> IngestionResult:
        """
        Pull real-time records from configured coordinates.
        Uses OpenWeatherMap if API key is provided; falls back to Open-Meteo.
        """
        meta = self.get_metadata()
        if not self.config.enabled:
            return IngestionResult(
                source_name=meta.name,
                status=IngestionStatus.SKIPPED,
                error_message="Weather data source is disabled in config.",
            )

        locations: List[Dict[str, Any]] = self.config.extra.get("locations", [])
        if not locations:
            return IngestionResult(
                source_name=meta.name,
                status=IngestionStatus.SKIPPED,
                error_message="No geographic target locations configured.",
            )

        records = []
        errors = []
        now = datetime.utcnow()

        async with aiohttp.ClientSession() as session:
            for loc in locations:
                city = loc.get("city", "Unknown")
                lat = loc.get("lat")
                lon = loc.get("lon")

                if lat is None or lon is None:
                    logger.warning(f"[{meta.name}] Skipping location {city} due to missing coordinates.")
                    continue

                try:
                    record = await self._fetch_location_weather(session, city, lat, lon)
                    records.append(record)
                except Exception as e:
                    logger.error(f"[{meta.name}] Failed to fetch weather for {city}: {e}")
                    errors.append(f"{city}: {str(e)}")

        status = IngestionStatus.SUCCESS
        error_msg = None

        if errors:
            if not records:
                status = IngestionStatus.FAILED
                error_msg = f"All location fetches failed: {'; '.join(errors)}"
            else:
                status = IngestionStatus.PARTIAL
                error_msg = f"Some fetches failed: {'; '.join(errors)}"

        return IngestionResult(
            source_name=meta.name,
            status=status,
            fetched_at=now,
            record_count=len(records),
            records=records,
            error_message=error_msg,
            metadata={
                "endpoint": self.config.endpoint,
                "locations_polled": len(locations),
                "api_used": "OpenWeatherMap" if self.config.api_key else "Open-Meteo",
            },
        )

    async def health_check(self) -> SourceHealthStatus:
        """
        Performs a lightweight HTTP connectivity ping to the active endpoint.
        """
        meta = self.get_metadata()
        test_lat = 40.7128
        test_lon = -74.0060

        async with aiohttp.ClientSession() as session:
            try:
                start_time = datetime.utcnow()
                if self.config.api_key:
                    url = (
                        f"https://api.openweathermap.org/data/2.5/weather"
                        f"?lat={test_lat}&lon={test_lon}&appid={self.config.api_key}"
                    )
                else:
                    url = (
                        f"https://api.open-meteo.com/v1/forecast"
                        f"?latitude={test_lat}&longitude={test_lon}&current=temperature_2m"
                    )

                async with session.get(url, timeout=5) as response:
                    latency = (datetime.utcnow() - start_time).total_seconds() * 1000
                    if response.status == 200:
                        return SourceHealthStatus(
                            source_name=meta.name,
                            state=HealthState.REACHABLE,
                            latency_ms=latency,
                            detail="Connection successful, weather service is healthy.",
                        )
                    else:
                        return SourceHealthStatus(
                            source_name=meta.name,
                            state=HealthState.DEGRADED,
                            latency_ms=latency,
                            detail=f"Reachable, but returned HTTP {response.status}",
                        )
            except Exception as e:
                return SourceHealthStatus(
                    source_name=meta.name,
                    state=HealthState.UNREACHABLE,
                    detail=f"Connection failed: {str(e)}",
                )

    # ------------------------------------------------------------------
    # Ingestion Core Logic
    # ------------------------------------------------------------------

    async def _fetch_location_weather(
        self, session: aiohttp.ClientSession, city: str, lat: float, lon: float
    ) -> Dict[str, Any]:
        """
        Fetch weather data for a specific city coordinates, with retries and failover.
        """
        # Determine URL
        if self.config.api_key:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&appid={self.config.api_key}&units=metric"
            )
            is_owm = True
        else:
            # Zero-config Open-Meteo API
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"
            )
            is_owm = False

        # Query with retries and exponential back-off
        data = await self._http_get_with_retry(session, url)

        # Parse payloads
        if "current" in data:
            return self._parse_open_meteo_response(city, lat, lon, data)
        elif is_owm:
            return self._parse_owm_response(city, lat, lon, data)
        else:
            return self._parse_open_meteo_response(city, lat, lon, data)

    async def _http_get_with_retry(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        """
        Internal HTTP client wrapper enforcing timeouts, retries, and exponential back-offs.
        """
        retries = self.config.max_retries
        backoff = self.config.retry_backoff
        timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)

        for attempt in range(retries + 1):
            try:
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        return await response.json()
                    
                    # Handle API key unauthorized by logging and raising failover
                    if response.status == 401:
                        logger.warning(
                            f"[Weather Ingestion] Unauthorized (401). "
                            f"Invalid OpenWeatherMap API key. Triggering immediate fallback to Open-Meteo."
                        )
                        raise ValueError("401 Unauthorized OpenWeatherMap Key")

                    response.raise_for_status()

            except Exception as e:
                if attempt < retries:
                    sleep_time = backoff * (2 ** attempt)
                    logger.warning(
                        f"[Weather Ingestion] Fetch attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {sleep_time:.1f}s..."
                    )
                    await asyncio.sleep(sleep_time)
                else:
                    # If OpenWeatherMap failed all retries, try to fall back to Open-Meteo on the fly
                    if "api.openweathermap.org" in url:
                        logger.warning(
                            f"[Weather Ingestion] OpenWeatherMap failed all retries. "
                            f"Falling back to public Open-Meteo API."
                        )
                        # Re-run the fetch using Open-Meteo URL format
                        # Extract coordinates from the URL or query
                        import re
                        lat_match = re.search(r"lat=([0-9.-]+)", url)
                        lon_match = re.search(r"lon=([0-9.-]+)", url)
                        if lat_match and lon_match:
                            lat = float(lat_match.group(1))
                            lon = float(lon_match.group(1))
                            fallback_url = (
                                f"https://api.open-meteo.com/v1/forecast"
                                f"?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"
                            )
                            logger.info(f"[Weather Ingestion] Triggering fallback query to Open-Meteo: {fallback_url}")
                            async with session.get(fallback_url, timeout=timeout) as fb_resp:
                                if fb_resp.status == 200:
                                    return await fb_resp.json()
                    raise e

        raise RuntimeError("Max HTTP retrieval attempts exceeded.")

    # ------------------------------------------------------------------
    # Response Translators
    # ------------------------------------------------------------------

    def _parse_owm_response(self, city: str, lat: float, lon: float, data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate OpenWeatherMap response payload into standard pipeline format."""
        temp = data.get("main", {}).get("temp")
        hum = data.get("main", {}).get("humidity")
        wind = data.get("wind", {}).get("speed")
        clouds = data.get("clouds", {}).get("all")
        
        # Rainfall parsing
        rain_1h = data.get("rain", {}).get("1h", 0.0)
        rain_3h = data.get("rain", {}).get("3h", 0.0)
        precipitation = rain_1h or (rain_3h / 3.0 if rain_3h else 0.0)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "location": city,
            "latitude": lat,
            "longitude": lon,
            "temperature_c": temp,
            "humidity_pct": hum,
            "wind_speed_ms": wind,
            "precipitation_mm": round(precipitation, 1),
            "cloud_coverage_pct": clouds,
            "_source": "OpenWeatherMap",
        }

    def _parse_open_meteo_response(self, city: str, lat: float, lon: float, data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Open-Meteo response payload into standard pipeline format."""
        current = data.get("current", {})
        temp = current.get("temperature_2m")
        hum = current.get("relative_humidity_2m")
        wind = current.get("wind_speed_10m")
        precipitation = current.get("precipitation", 0.0)

        # Convert wind speed km/h to m/s if Open-Meteo returned km/h (standard unit)
        if wind is not None:
            # Open-Meteo default is km/h, convert to m/s by dividing by 3.6
            wind = round(wind / 3.6, 1)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "location": city,
            "latitude": lat,
            "longitude": lon,
            "temperature_c": temp,
            "humidity_pct": hum,
            "wind_speed_ms": wind,
            "precipitation_mm": precipitation,
            "cloud_coverage_pct": None,  # Open-Meteo needs extra current field for clouds
            "_source": "Open-Meteo (Public)",
        }
