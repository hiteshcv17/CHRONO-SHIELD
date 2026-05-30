"""
ai-engine/src/ingestion/sources/energy.py

EnergyDataSource — stub for EIA Open Data / OpenEI / ENTSO-E Transparency Platform.

Planned fields per record:
  - timestamp, region, demand_mwh, net_generation_mwh,
    interchange_mwh, fuel_mix (dict), carbon_intensity_gco2_kwh

Phase implementation: returns a structured IngestionResult with
status=SKIPPED and a schema blueprint. No real HTTP calls.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

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

logger = logging.getLogger("ingestion.sources.energy")


@register_source("energy")
class EnergyDataSource(BaseDataSource):
    """
    Data source for regional electric grid metrics and energy demand telemetry.

    Planned API integrations:
        - EIA Open Data API v2 (U.S. Energy Information Administration)
        - OpenEI Utility Rate Database
        - ENTSO-E Transparency Platform (European grid data)

    Supported output fields:
        demand_mwh, net_generation_mwh, interchange_mwh,
        fuel_mix (dict: coal/gas/nuclear/wind/solar/hydro),
        carbon_intensity_gco2_kwh, peak_demand_mwh
    """

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            name="energy",
            version="0.1.0",
            category=SourceCategory.ENERGY,
            description=(
                "Regional electric grid demand, generation mix, and carbon "
                "intensity measurements from ISO/RTO reporting nodes."
            ),
            interval_seconds=self.config.interval_seconds,
            supported_fields=[
                "timestamp",
                "region",
                "demand_mwh",
                "net_generation_mwh",
                "interchange_mwh",
                "peak_demand_mwh",
                "carbon_intensity_gco2_kwh",
                "fuel_mix_coal_pct",
                "fuel_mix_gas_pct",
                "fuel_mix_nuclear_pct",
                "fuel_mix_wind_pct",
                "fuel_mix_solar_pct",
                "fuel_mix_hydro_pct",
            ],
            tags=["energy", "grid", "electricity", "carbon", "sustainability"],
        )

    async def fetch(self) -> IngestionResult:
        """
        Placeholder fetch — returns SKIPPED with per-region schema blueprint.
        Replace with real EIA API request when API key is set.
        """
        meta = self.get_metadata()
        logger.info(
            f"[{meta.name}] fetch() triggered — "
            f"endpoint={self.config.endpoint!r} | "
            f"PLACEHOLDER: no real HTTP request in Phase 5."
        )

        if not self.config.enabled:
            return IngestionResult(
                source_name=meta.name,
                status=IngestionStatus.SKIPPED,
                error_message="Source is disabled in configuration.",
            )

        if not self.config.api_key:
            logger.warning(
                f"[{meta.name}] API key not configured. "
                "Set CHRONOSHIELD_ENERGY_API_KEY env var to activate."
            )

        regions: List[str] = self.config.extra.get("regions", [])
        placeholder_records = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "region": region,
                "demand_mwh": None,
                "net_generation_mwh": None,
                "interchange_mwh": None,
                "peak_demand_mwh": None,
                "carbon_intensity_gco2_kwh": None,
                "fuel_mix": {
                    "coal": None,
                    "gas": None,
                    "nuclear": None,
                    "wind": None,
                    "solar": None,
                    "hydro": None,
                },
                "_placeholder": True,
            }
            for region in regions
        ]

        return IngestionResult(
            source_name=meta.name,
            status=IngestionStatus.SKIPPED,
            record_count=len(placeholder_records),
            records=placeholder_records,
            error_message="Placeholder: real API integration pending API key configuration.",
            metadata={"endpoint": self.config.endpoint, "phase": "stub"},
        )

    async def health_check(self) -> SourceHealthStatus:
        return SourceHealthStatus(
            source_name=self.get_metadata().name,
            state=HealthState.UNKNOWN,
            detail=(
                "Connectivity probe not yet active. "
                "Configure CHRONOSHIELD_ENERGY_API_KEY to enable."
            ),
        )
