import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.schemas.weather import WeatherRecord, CurrentWeatherResponse, WeatherTrendsResponse
from app.models.weather import WeatherRecordModel

logger = logging.getLogger("weather_service")

# Default coordinates and metadata for cities
CITY_METADATA = {
    "new york": {"city": "New York", "country": "US", "lat": 40.7128, "lon": -74.0060, "temp_base": 18.0, "hum_base": 65.0, "wind_base": 4.5},
    "london": {"city": "London", "country": "GB", "lat": 51.5074, "lon": -0.1278, "temp_base": 14.0, "hum_base": 78.0, "wind_base": 5.2},
    "singapore": {"city": "Singapore", "country": "SG", "lat": 1.3521, "lon": 103.8198, "temp_base": 28.5, "hum_base": 82.0, "wind_base": 2.5},
}


class WeatherService:
    """
    Service layer interacting with Redis and PostgreSQL to cache and query real-time environmental data.
    """

    @staticmethod
    async def get_current_weather(redis: Redis) -> CurrentWeatherResponse:
        """
        Fetch the current weather observations for all cities from Redis,
        falling back to simulated live observations if Redis is empty.
        """
        try:
            cached_data = await redis.get("weather:current")
            if cached_data:
                records_raw = json.loads(cached_data)
                records = [WeatherRecord(**r) for r in records_raw]
                logger.info("Retrieved current weather from Redis cache.")
                return CurrentWeatherResponse(
                    success=True,
                    fetched_at=datetime.utcnow(),
                    records=records
                )
        except Exception as e:
            logger.error(f"Failed to query current weather from Redis: {e}")

        # Fallback simulated data if Redis is empty/errors out
        logger.warning("Redis cache is empty or unavailable — generating fallback simulated current weather.")
        records = []
        now = datetime.utcnow()
        for idx, (slug, meta) in enumerate(CITY_METADATA.items()):
            # Dynamic fluctuations based on hour
            hour_factor = math_sin_factor(now.hour)
            temp = meta["temp_base"] + (3.0 * hour_factor) + (idx * 0.5)
            hum = min(100.0, max(0.0, meta["hum_base"] - (5.0 * hour_factor)))
            wind = max(0.0, meta["wind_base"] + (1.2 * hour_factor))
            rain = 0.0 if hour_factor < 0.2 else round((hour_factor - 0.2) * 5.0, 1)

            records.append(
                WeatherRecord(
                    timestamp=now,
                    location=meta["city"],
                    latitude=meta["lat"],
                    longitude=meta["lon"],
                    temperature_c=round(temp, 1),
                    humidity_pct=round(hum, 1),
                    wind_speed_ms=round(wind, 1),
                    precipitation_mm=round(rain, 1)
                )
            )

        return CurrentWeatherResponse(
            success=False,  # Indicated it's a fallback/simulation
            fetched_at=now,
            records=records
        )

    @staticmethod
    async def get_weather_trends(db: AsyncSession, city: str) -> WeatherTrendsResponse:
        """
        Fetch historical weather trends for the target city directly from PostgreSQL,
        enforcing sub-second chronological composite queries and falling back to stubs.
        """
        city_slug = city.lower().strip()
        meta = CITY_METADATA.get(city_slug)
        if not meta:
            # Try fuzzy matching
            matched = False
            for k, m in CITY_METADATA.items():
                if k in city_slug or city_slug in k:
                    meta = m
                    city_slug = k
                    matched = True
                    break
            if not matched:
                meta = CITY_METADATA["new york"]
                city_slug = "new york"

        city_name = meta["city"]
        records = []

        try:
            # Optimized temporal query leveraging the composite index (location, timestamp DESC)
            stmt = (
                select(WeatherRecordModel)
                .where(WeatherRecordModel.location == city_name)
                .order_by(WeatherRecordModel.timestamp.desc())
                .limit(50)
            )
            res = await db.execute(stmt)
            db_records = res.scalars().all()

            if db_records:
                # Sort chronologically (oldest to newest) to display cleanly on Plotly lines
                chronological_records = sorted(db_records, key=lambda x: x.timestamp)
                records = [
                    WeatherRecord(
                        timestamp=r.timestamp,
                        location=r.location,
                        latitude=r.latitude,
                        longitude=r.longitude,
                        temperature_c=r.temperature_c,
                        humidity_pct=r.humidity_pct,
                        wind_speed_ms=r.wind_speed_ms,
                        precipitation_mm=r.precipitation_mm
                    )
                    for r in chronological_records
                ]
                logger.info(f"Retrieved {len(records)} weather trend records from PostgreSQL.")
                return WeatherTrendsResponse(city=city_name, records=records)
        except Exception as e:
            logger.error(f"Failed to query weather history for {city_name} from PostgreSQL: {e}")

        # Fallback simulated history: 24 points at 10-minute intervals
        logger.warning(f"No PostgreSQL historical trends for {city_name} — generating simulated sequences.")
        now = datetime.utcnow()
        for i in range(24):
            time_offset = now - timedelta(minutes=(24 - i) * 10)
            hour_factor = math_sin_factor(time_offset.hour)
            
            temp = meta["temp_base"] + (4.0 * hour_factor)
            hum = min(100.0, max(0.0, meta["hum_base"] - (8.0 * hour_factor)))
            wind = max(0.0, meta["wind_base"] + (1.5 * hour_factor))
            rain = 0.0 if hour_factor < 0.3 else round((hour_factor - 0.3) * 4.0, 1)

            records.append(
                WeatherRecord(
                    timestamp=time_offset,
                    location=city_name,
                    latitude=meta["lat"],
                    longitude=meta["lon"],
                    temperature_c=round(temp, 1),
                    humidity_pct=round(hum, 1),
                    wind_speed_ms=round(wind, 1),
                    precipitation_mm=round(rain, 1)
                )
            )

        return WeatherTrendsResponse(city=city_name, records=records)


def math_sin_factor(hour: int) -> float:
    """Helper to generate smooth oscillation curves based on the time of day."""
    import math
    # Oscillate between -1.0 and 1.0 based on 24 hour cycle
    return math.sin((hour - 6) * math.pi / 12)
