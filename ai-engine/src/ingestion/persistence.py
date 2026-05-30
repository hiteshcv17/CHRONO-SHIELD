"""
ai-engine/src/ingestion/persistence.py

Persistence layer for syncing IngestionResults with Redis Cache & PostgreSQL.
Used by IngestionScheduler to register dynamic telemetry chronologically.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from redis.asyncio import Redis, from_url
from src.config import ai_settings
from src.ingestion.base import IngestionResult

logger = logging.getLogger("ingestion.persistence")


def _get_redis_url() -> str:
    """Helper to assemble the Redis connection URL from settings."""
    host = ai_settings.REDIS_HOST
    port = ai_settings.REDIS_PORT
    pw = ai_settings.REDIS_PASSWORD
    db = ai_settings.REDIS_DB

    if pw:
        return f"redis://:{pw}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


async def persist_ingestion_result(result: IngestionResult) -> None:
    """
    Persists a successfully fetched IngestionResult to Redis and PostgreSQL.
    """
    if not result.is_successful():
        logger.warning(
            f"[Persistence] Skipping persistence for source='{result.source_name}' "
            f"due to unsuccessful status={result.status}"
        )
        return

    if result.source_name == "weather":
        await _persist_weather_result(result)
    elif result.source_name == "traffic":
        await _persist_traffic_result(result)
    elif result.source_name == "social":
        await _persist_social_result(result)
    else:
        logger.debug(
            f"[Persistence] Persistor not yet mapped for source='{result.source_name}'. "
            "Data was successfully fetched but not written to cache."
        )


async def _persist_weather_result(result: IngestionResult) -> None:
    """
    Persists weather observations:
      1. Writes current state for all cities to `weather:current` Redis JSON string.
      2. Appends city-specific telemetry point to `weather:history:{city}` Redis lists.
      3. Persists historical observations to PostgreSQL `weather_records` table.
    """
    if not result.records:
        logger.warning("[Persistence] No weather records to cache.")
        return

    # 1. Sync to Redis Cache
    redis_url = _get_redis_url()
    try:
        async with from_url(
            redis_url, encoding="utf-8", decode_responses=True
        ) as redis:
            current_payload = json.dumps(result.records)
            await redis.set("weather:current", current_payload)
            logger.info(
                f"[Persistence] Successfully cached latest weather:current "
                f"({len(result.records)} records)."
            )

            for record in result.records:
                city = record.get("location")
                if not city:
                    continue

                city_slug = city.lower().strip()
                history_key = f"weather:history:{city_slug}"

                record_payload = json.dumps(record)
                await redis.lpush(history_key, record_payload)
                await redis.ltrim(history_key, 0, 49)

            logger.info(
                f"[Persistence] Successfully pushed weather trends to Redis for {len(result.records)} cities."
            )

            # Trigger baseline statistical anomaly detection
            for record in result.records:
                city = record.get("location")
                if not city:
                    continue
                city_slug = city.lower().strip()
                await _detect_and_persist_weather_anomalies(redis, city_slug, city)
    except Exception as e:
        logger.error(
            f"[Persistence] Redis execution error during weather telemetry cache: {e}"
        )

    # 2. Sync to PostgreSQL Database (Time-Series)
    await _persist_weather_to_db(result.records)


async def _persist_traffic_result(result: IngestionResult) -> None:
    """
    Persists traffic observations:
      1. Writes current state for all corridors to `traffic:current` Redis JSON string.
      2. Appends corridor-specific telemetry point to `traffic:history:{corridor}` Redis lists.
      3. Persists historical observations to PostgreSQL `traffic_records` table.
    """
    if not result.records:
        logger.warning("[Persistence] No traffic records to cache.")
        return

    # 1. Sync to Redis Cache
    redis_url = _get_redis_url()
    try:
        async with from_url(
            redis_url, encoding="utf-8", decode_responses=True
        ) as redis:
            current_payload = json.dumps(result.records)
            await redis.set("traffic:current", current_payload)
            logger.info(
                f"[Persistence] Successfully cached latest traffic:current "
                f"({len(result.records)} records)."
            )

            for record in result.records:
                corridor = record.get("corridor_id")
                if not corridor:
                    continue

                corridor_slug = corridor.lower().strip()
                history_key = f"traffic:history:{corridor_slug}"

                record_payload = json.dumps(record)
                await redis.lpush(history_key, record_payload)
                await redis.ltrim(history_key, 0, 49)

            logger.info(
                f"[Persistence] Successfully pushed traffic trends to Redis for {len(result.records)} corridors."
            )

            # Trigger baseline statistical anomaly detection
            for record in result.records:
                corridor = record.get("corridor_id")
                if not corridor:
                    continue
                corridor_slug = corridor.lower().strip()
                await _detect_and_persist_traffic_anomalies(
                    redis, corridor_slug, corridor
                )
    except Exception as e:
        logger.error(
            f"[Persistence] Redis execution error during traffic telemetry cache: {e}"
        )

    # 2. Sync to PostgreSQL Database (Time-Series)
    await _persist_traffic_to_db(result.records)


# ==============================================================================
# PostgreSQL Database Persistence Sync Helpers (Resilient Drivers)
# ==============================================================================


async def _persist_weather_to_db(records: List[Dict[str, Any]]) -> None:
    """Synchronize weather observations to PostgreSQL weather_records table."""
    try:
        import asyncpg
    except ImportError:
        logger.warning(
            "[Persistence] asyncpg not installed — skipping PostgreSQL weather sync."
        )
        return

    if not ai_settings.DATABASE_URL:
        logger.warning(
            "[Persistence] DATABASE_URL not configured — skipping PostgreSQL weather sync."
        )
        return

    # Clean connection URL for asyncpg compatibility
    pg_url = ai_settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = await asyncpg.connect(pg_url)
        try:
            for r in records:
                # Convert ISO timestamp string back to Python datetime object for postgres
                ts = datetime.fromisoformat(r["timestamp"])
                await conn.execute(
                    """
                    INSERT INTO weather_records (
                        timestamp, location, latitude, longitude,
                        temperature_c, humidity_pct, wind_speed_ms,
                        precipitation_mm, cloud_coverage_pct
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    ts,
                    r["location"],
                    r["latitude"],
                    r["longitude"],
                    r["temperature_c"],
                    r["humidity_pct"],
                    r["wind_speed_ms"],
                    r["precipitation_mm"],
                    r["cloud_coverage_pct"],
                )
            logger.info(
                f"[Persistence] Successfully persisted {len(records)} weather records to PostgreSQL."
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.error(
            f"[Persistence] PostgreSQL execution error during weather sync: {e}"
        )


async def _persist_traffic_to_db(records: List[Dict[str, Any]]) -> None:
    """Synchronize traffic observations to PostgreSQL traffic_records table."""
    try:
        import asyncpg
    except ImportError:
        logger.warning(
            "[Persistence] asyncpg not installed — skipping PostgreSQL traffic sync."
        )
        return

    if not ai_settings.DATABASE_URL:
        logger.warning(
            "[Persistence] DATABASE_URL not configured — skipping PostgreSQL traffic sync."
        )
        return

    pg_url = ai_settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = await asyncpg.connect(pg_url)
        try:
            for r in records:
                ts = datetime.fromisoformat(r["timestamp"])
                await conn.execute(
                    """
                    INSERT INTO traffic_records (
                        timestamp, corridor_id, bbox, flow_speed_kmh,
                        free_flow_speed_kmh, jam_factor, congestion_level,
                        incident_count, travel_time_seconds
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    ts,
                    r["corridor_id"],
                    r["bbox"],
                    r["flow_speed_kmh"],
                    r["free_flow_speed_kmh"],
                    r["jam_factor"],
                    r["congestion_level"],
                    r["incident_count"],
                    r["travel_time_seconds"],
                )
            logger.info(
                f"[Persistence] Successfully persisted {len(records)} traffic records to PostgreSQL."
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.error(
            f"[Persistence] PostgreSQL execution error during traffic sync: {e}"
        )


# ==============================================================================
# Statistical Anomaly Detection Run & Persist Helpers
# ==============================================================================


async def _detect_and_persist_weather_anomalies(
    redis: Redis, city_slug: str, city_name: str
) -> None:
    """Runs statistical anomaly detection on the sliding window history from Redis."""
    try:
        import pandas as pd
    except ImportError:
        logger.warning(
            "[Persistence] pandas not installed — skipping weather anomaly detection."
        )
        return

    history_key = f"weather:history:{city_slug}"
    try:
        raw_history = await redis.lrange(history_key, 0, -1)
        if len(raw_history) < 3:
            return

        records = [json.loads(x) for x in raw_history]
        records.reverse()  # oldest to newest
        df = pd.DataFrame(records)

        from src.models.statistical_detector import StatisticalAnomalyDetector

        anomalies = []
        # Monitor temperature, humidity, and wind speed
        if "temperature_c" in df.columns:
            anomalies.extend(
                StatisticalAnomalyDetector.detect_anomalies(
                    df,
                    "temperature_c",
                    "timestamp",
                    window=10,
                    z_threshold=2.5,
                    metric_label=f"Weather: {city_name} Temperature",
                )
            )
        if "humidity_pct" in df.columns:
            anomalies.extend(
                StatisticalAnomalyDetector.detect_anomalies(
                    df,
                    "humidity_pct",
                    "timestamp",
                    window=10,
                    z_threshold=2.5,
                    metric_label=f"Weather: {city_name} Humidity",
                )
            )
        if "wind_speed_ms" in df.columns:
            anomalies.extend(
                StatisticalAnomalyDetector.detect_anomalies(
                    df,
                    "wind_speed_ms",
                    "timestamp",
                    window=10,
                    z_threshold=2.5,
                    metric_label=f"Weather: {city_name} Wind Speed",
                )
            )

        if not anomalies:
            return

        latest_record = records[-1]
        latest_ts_str = latest_record.get("timestamp")
        if not latest_ts_str:
            return

        latest_ts = datetime.fromisoformat(
            latest_ts_str.replace("Z", "+00:00")
        ).replace(tzinfo=None)

        latest_anomalies = []
        for anom in anomalies:
            anom_ts = anom["timestamp"].replace(tzinfo=None)
            if abs((anom_ts - latest_ts).total_seconds()) < 1.0:
                latest_anomalies.append(anom)

        if latest_anomalies:
            await _persist_anomalies_to_db(latest_anomalies)

    except Exception as e:
        logger.error(
            f"[Persistence] Error detecting weather anomalies: {e}", exc_info=True
        )


async def _detect_and_persist_traffic_anomalies(
    redis: Redis, corridor_slug: str, corridor_id: str
) -> None:
    """Runs statistical anomaly detection on the traffic history from Redis."""
    try:
        import pandas as pd
    except ImportError:
        logger.warning(
            "[Persistence] pandas not installed — skipping traffic anomaly detection."
        )
        return

    history_key = f"traffic:history:{corridor_slug}"
    try:
        raw_history = await redis.lrange(history_key, 0, -1)
        if len(raw_history) < 3:
            return

        records = [json.loads(x) for x in raw_history]
        records.reverse()  # oldest to newest
        df = pd.DataFrame(records)

        from src.models.statistical_detector import StatisticalAnomalyDetector

        anomalies = []
        # Monitor flow speed, travel time, and jam factor
        if "flow_speed_kmh" in df.columns:
            anomalies.extend(
                StatisticalAnomalyDetector.detect_anomalies(
                    df,
                    "flow_speed_kmh",
                    "timestamp",
                    window=10,
                    z_threshold=2.5,
                    metric_label=f"Traffic: {corridor_id} Flow Speed",
                )
            )
        if "travel_time_seconds" in df.columns:
            anomalies.extend(
                StatisticalAnomalyDetector.detect_anomalies(
                    df,
                    "travel_time_seconds",
                    "timestamp",
                    window=10,
                    z_threshold=2.5,
                    metric_label=f"Traffic: {corridor_id} Travel Time",
                )
            )
        if "jam_factor" in df.columns:
            anomalies.extend(
                StatisticalAnomalyDetector.detect_anomalies(
                    df,
                    "jam_factor",
                    "timestamp",
                    window=10,
                    z_threshold=2.5,
                    metric_label=f"Traffic: {corridor_id} Jam Factor",
                )
            )

        if not anomalies:
            return

        latest_record = records[-1]
        latest_ts_str = latest_record.get("timestamp")
        if not latest_ts_str:
            return

        latest_ts = datetime.fromisoformat(
            latest_ts_str.replace("Z", "+00:00")
        ).replace(tzinfo=None)

        latest_anomalies = []
        for anom in anomalies:
            anom_ts = anom["timestamp"].replace(tzinfo=None)
            if abs((anom_ts - latest_ts).total_seconds()) < 1.0:
                latest_anomalies.append(anom)

        if latest_anomalies:
            await _persist_anomalies_to_db(latest_anomalies)

    except Exception as e:
        logger.error(
            f"[Persistence] Error detecting traffic anomalies: {e}", exc_info=True
        )


async def _persist_anomalies_to_db(anomalies: List[Dict[str, Any]]) -> None:
    """Inserts a list of statistical anomalies into the PostgreSQL database."""
    try:
        import asyncpg
    except ImportError:
        logger.warning(
            "[Persistence] asyncpg not installed — skipping PostgreSQL anomaly sync."
        )
        return

    if not ai_settings.DATABASE_URL:
        logger.warning(
            "[Persistence] DATABASE_URL not configured — skipping PostgreSQL anomaly sync."
        )
        return

    pg_url = ai_settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = await asyncpg.connect(pg_url)
        try:
            for anom in anomalies:
                ts = anom["timestamp"].replace(tzinfo=None)
                await conn.execute(
                    """
                    INSERT INTO anomaly_records (
                        id, timestamp, metric_name, severity, score, description, acknowledged
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    anom["id"],
                    ts,
                    anom["metric_name"],
                    anom["severity"],
                    anom["score"],
                    anom["description"],
                    anom["acknowledged"],
                )
            logger.info(
                f"[Persistence] Successfully persisted {len(anomalies)} anomalies to PostgreSQL."
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.error(
            f"[Persistence] PostgreSQL execution error during anomaly sync: {e}"
        )


# ==============================================================================
# Social Media Ingestion Run & Persist Helpers
# ==============================================================================


async def _persist_social_result(result: IngestionResult) -> None:
    """
    Persists social media observations:
      1. Writes current state to `social:current` Redis JSON string.
      2. Appends telemetry complaints to `social:history` Redis lists.
      3. Persists historical observations to PostgreSQL `social_complaints` table.
    """
    if not result.records:
        logger.warning("[Persistence] No social complaints to cache.")
        return

    # 1. Sync to Redis Cache
    redis_url = _get_redis_url()
    try:
        async with from_url(
            redis_url, encoding="utf-8", decode_responses=True
        ) as redis:
            current_payload = json.dumps(result.records)
            await redis.set("social:current", current_payload)
            logger.info(
                f"[Persistence] Successfully cached latest social:current "
                f"({len(result.records)} records)."
            )

            for record in result.records:
                record_payload = json.dumps(record)
                await redis.lpush("social:history", record_payload)
                await redis.ltrim("social:history", 0, 49)

            logger.info(
                f"[Persistence] Successfully pushed social trends to Redis history list."
            )
    except Exception as e:
        logger.error(f"[Persistence] Redis execution error during social cache: {e}")

    # 2. Sync to PostgreSQL Database
    await _persist_social_to_db(result.records)


async def _persist_social_to_db(records: List[Dict[str, Any]]) -> None:
    """Synchronize social media complaints to PostgreSQL social_complaints table."""
    try:
        import asyncpg
    except ImportError:
        logger.warning(
            "[Persistence] asyncpg not installed — skipping PostgreSQL social sync."
        )
        return

    if not ai_settings.DATABASE_URL:
        logger.warning(
            "[Persistence] DATABASE_URL not configured — skipping PostgreSQL social sync."
        )
        return

    pg_url = ai_settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = await asyncpg.connect(pg_url)
        try:
            for r in records:
                # Parse timestamp safely
                ts = datetime.fromisoformat(
                    r["timestamp"].replace("Z", "+00:00")
                ).replace(tzinfo=None)
                post_id = r["post_id"]
                complaint_id = f"complaint-tw-{post_id}"

                await conn.execute(
                    """
                    INSERT INTO social_complaints (
                        id, timestamp, platform, text, author,
                        matched_keyword, category, severity, sentiment_score,
                        urgency_score, explanation, keywords, cluster_tag
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    complaint_id,
                    ts,
                    r["platform"],
                    r["text"],
                    r["author_id"],
                    r["matched_query_term"],
                    r["category"],
                    r["severity"],
                    r["sentiment_score"],
                    r.get("urgency_score", 0.0),
                    r.get("explanation"),
                    r.get("keywords"),
                    r.get("cluster_tag"),
                )
            logger.info(
                f"[Persistence] Successfully persisted {len(records)} social complaints to PostgreSQL."
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.error(
            f"[Persistence] PostgreSQL execution error during social sync: {e}"
        )
