import json
import logging
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.schemas.energy import EnergyRecord, CurrentEnergyResponse, EnergyTrendsResponse
from app.models.energy import EnergyRecordModel

logger = logging.getLogger("energy_service")

# Monitored locations and baseline values for simulation
GRID_METADATA = {
    "new york": {
        "location": "New York",
        "demand_base": 5000.0,
        "load_base": 4800.0,
        "stability_base": 98.5,
        "solar_base": 800.0,
    },
    "london": {
        "location": "London",
        "demand_base": 4000.0,
        "load_base": 3950.0,
        "stability_base": 97.2,
        "solar_base": 400.0,
    },
    "singapore": {
        "location": "Singapore",
        "demand_base": 6500.0,
        "load_base": 6400.0,
        "stability_base": 99.1,
        "solar_base": 1200.0,
    },
}


class EnergyService:
    """
    Decoupled service handling energy grid telemetry caching and database queries.
    """

    @staticmethod
    async def get_current_energy(redis: Redis) -> CurrentEnergyResponse:
        """
        Query current grid conditions across all locations from Redis.
        Falls back to sinusoidal simulated telemetry if Redis cache is empty.
        """
        try:
            cached = await redis.get("energy:current")
            if cached:
                raw_records = json.loads(cached)
                records = [EnergyRecord(**r) for r in raw_records]
                logger.info("Retrieved current energy telemetry from Redis.")
                return CurrentEnergyResponse(
                    success=True, fetched_at=datetime.utcnow(), records=records
                )
        except Exception as e:
            logger.error(f"Failed to query energy from Redis: {e}")

        # Sinusoidal simulation fallback
        logger.warning("Redis energy cache empty — generating simulated grid states.")
        records = []
        now = datetime.utcnow()
        for slug, meta in GRID_METADATA.items():
            demand, load, stability, solar = simulate_energy_state(now.hour, meta)
            records.append(
                EnergyRecord(
                    timestamp=now,
                    location=meta["location"],
                    grid_load_kw=round(load, 1),
                    solar_output_kw=round(solar, 1),
                    energy_demand_kw=round(demand, 1),
                    grid_stability_pct=round(stability, 1),
                )
            )

        return CurrentEnergyResponse(success=False, fetched_at=now, records=records)

    @staticmethod
    async def get_energy_trends(
        db: AsyncSession, location: str
    ) -> EnergyTrendsResponse:
        """
        Query historical energy telemetry trends directly from PostgreSQL.
        """
        loc_slug = location.lower().strip()
        meta = GRID_METADATA.get(loc_slug)
        if not meta:
            # Fuzzy match
            for k, m in GRID_METADATA.items():
                if k in loc_slug or loc_slug in k:
                    meta = m
                    break
            if not meta:
                meta = GRID_METADATA["new york"]

        loc_name = meta["location"]
        records = []

        try:
            # Chronological database query utilizing location composite index
            stmt = (
                select(EnergyRecordModel)
                .where(EnergyRecordModel.location == loc_name)
                .order_by(EnergyRecordModel.timestamp.desc())
                .limit(50)
            )
            res = await db.execute(stmt)
            db_records = res.scalars().all()

            if db_records:
                # Sort chronologically for frontend graphing
                chronological_records = sorted(db_records, key=lambda x: x.timestamp)
                records = [
                    EnergyRecord(
                        timestamp=r.timestamp,
                        location=r.location,
                        grid_load_kw=r.grid_load_kw,
                        solar_output_kw=r.solar_output_kw,
                        energy_demand_kw=r.energy_demand_kw,
                        grid_stability_pct=r.grid_stability_pct,
                    )
                    for r in chronological_records
                ]
                logger.info(
                    f"Retrieved {len(records)} energy trend records from PostgreSQL."
                )
                return EnergyTrendsResponse(location=loc_name, records=records)
        except Exception as e:
            logger.error(
                f"Failed to query energy history for {loc_name} from PostgreSQL: {e}"
            )

        # Fallback simulation history: 24 points at 10-minute offsets
        logger.warning(
            f"No PostgreSQL historical trends for {loc_name} — generating simulated sequences."
        )
        now = datetime.utcnow()
        for i in range(24):
            time_offset = now - timedelta(minutes=(24 - i) * 10)
            demand, load, stability, solar = simulate_energy_state(
                time_offset.hour, meta
            )
            records.append(
                EnergyRecord(
                    timestamp=time_offset,
                    location=loc_name,
                    grid_load_kw=round(load, 1),
                    solar_output_kw=round(solar, 1),
                    energy_demand_kw=round(demand, 1),
                    grid_stability_pct=round(stability, 1),
                )
            )

        return EnergyTrendsResponse(location=loc_name, records=records)


def simulate_energy_state(hour: float, meta: Dict[str, Any]) -> tuple:
    """
    Simulates demand peaking in the afternoon/evening, solar output peaking at midday,
    and load tracking demand with stability fluctuations.
    """
    # Solar peaks at 12:00 (midday)
    solar_factor = (
        max(0.0, math.sin((hour - 6) * math.pi / 12)) if 6.0 <= hour <= 18.0 else 0.0
    )
    solar = meta["solar_base"] * solar_factor

    # Demand peak at 18:00 (evening peak) and minor peak at 8:00 AM
    demand_factor = 0.7 + 0.3 * (
        0.4 * math.exp(-(((hour - 8.0) / 2.0) ** 2))
        + 0.8 * math.exp(-(((hour - 18.0) / 3.0) ** 2))
    )
    demand = meta["demand_base"] * demand_factor

    # Load follows demand closely with small stochastic variations
    load_variance = (math.sin(hour) * 100.0) + (solar * 0.1)
    load = demand * 0.95 + load_variance

    # Grid stability dips slightly during high load peaks
    stability_dip = (
        5.0 * (demand / meta["demand_base"]) if demand > meta["demand_base"] else 1.0
    )
    stability = max(80.0, min(100.0, meta["stability_base"] - stability_dip))

    return demand, load, stability, solar
