"""
ai-engine/tests/test_traffic.py

Unit tests for real-time TrafficDataSource road telemetry.
Covers metadata, API requests, fallbacks, rush-hour simulations, and health probes.

Run with:
    cd ai-engine
    PYTHONPATH=. pytest tests/test_traffic.py -v
"""

import asyncio
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import aiohttp

from src.ingestion.base import IngestionResult, IngestionStatus, HealthState, SourceCategory
from src.ingestion.config_manager import SourceConfig
from src.ingestion.sources.traffic import TrafficDataSource


# ==============================================================================
# Helper Builders
# ==============================================================================

def make_traffic_config(
    api_key: str = "",
    enabled: bool = True,
    max_retries: int = 1,
    retry_backoff: float = 0.1,
) -> SourceConfig:
    return SourceConfig(
        name="traffic",
        enabled=enabled,
        endpoint="https://traffic.ls.hereapi.com/traffic/6.3/flow.json",
        api_key=api_key,
        interval_seconds=300,
        timeout_seconds=5,
        max_retries=max_retries,
        retry_backoff=retry_backoff,
        extra={
            "corridors": [
                {"id": "NYC-I95", "bbox": "-74.05,40.70,-73.97,40.78"},
                {"id": "LA-I405", "bbox": "-118.50,33.96,-118.38,34.08"},
            ]
        },
    )


# ==============================================================================
# Traffic Ingestion Tests
# ==============================================================================

class TestTrafficDataSource:

    def test_traffic_metadata(self):
        """Verify the static metadata contract."""
        cfg = make_traffic_config()
        src = TrafficDataSource(cfg)
        meta = src.get_metadata()

        assert meta.name == "traffic"
        assert meta.category == SourceCategory.TRAFFIC
        assert meta.version == "1.0.0"
        assert "flow_speed_kmh" in meta.supported_fields
        assert "jam_factor" in meta.supported_fields
        assert "congestion_level" in meta.supported_fields
        assert "incident_count" in meta.supported_fields
        assert "travel_time_seconds" in meta.supported_fields

    def test_validation_rules(self):
        """Ensure validation catches missing corridors or endpoints."""
        cfg = make_traffic_config()
        src = TrafficDataSource(cfg)
        assert src.validate() is True

        cfg_empty = make_traffic_config()
        cfg_empty.endpoint = ""
        src_empty = TrafficDataSource(cfg_empty)
        assert src_empty.validate() is False

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_fetch_here_api_success(self, mock_get):
        """Verify successful fetch using HERE Traffic Flow API mock responses."""
        cfg = make_traffic_config(api_key="valid-here-api-key-998")
        src = TrafficDataSource(cfg)

        # Mock HERE Flow JSON response structure
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "RWS": [
                {
                    "RW": [
                        {
                            "FIS": [
                                {
                                    "FI": [
                                        {
                                            "CF": [
                                                {
                                                    "SP": 72.5,
                                                    "FF": 100.0,
                                                    "JF": 3.8
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        })

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get.return_value = mock_context

        result = await src.fetch()

        assert result.status == IngestionStatus.SUCCESS
        assert result.record_count == 2
        assert result.metadata["api_used"] == "HERE Traffic Flow"

        rec = result.records[0]
        assert rec["corridor_id"] == "NYC-I95"
        assert rec["flow_speed_kmh"] == 72.5
        assert rec["free_flow_speed_kmh"] == 100.0
        assert rec["jam_factor"] == 3.8
        assert rec["congestion_level"] == "SLOW"
        assert rec["incident_count"] == 1  # 3.8 // 3 = 1

    @pytest.mark.asyncio
    async def test_fetch_simulation_fallback_peaks(self):
        """Verify stateful dynamic peak simulator fallback output when no key is present."""
        cfg = make_traffic_config(api_key="")  # No key
        src = TrafficDataSource(cfg)

        result = await src.fetch()

        assert result.status == IngestionStatus.SUCCESS
        assert result.record_count == 2
        assert result.metadata["api_used"] == "Peak-Hour Simulator Fallback"

        rec = result.records[0]
        assert rec["corridor_id"] == "NYC-I95"
        assert rec["flow_speed_kmh"] is not None
        assert rec["free_flow_speed_kmh"] == 90.0
        assert rec["jam_factor"] is not None
        assert rec["congestion_level"] in {"SAFE", "SLOW", "CONGESTED", "GRIDLOCK"}

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_health_check_reachable(self, mock_get):
        """Verify health check reports REACHABLE on status 200."""
        cfg = make_traffic_config()
        src = TrafficDataSource(cfg)

        mock_response = AsyncMock()
        mock_response.status = 200

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get.return_value = mock_context

        health = await src.health_check()
        assert health.state == HealthState.REACHABLE
        assert health.latency_ms is not None

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_health_check_unreachable(self, mock_get):
        """Verify health check reports UNREACHABLE on networking exceptions."""
        cfg = make_traffic_config(api_key="here-api-key")
        src = TrafficDataSource(cfg)

        mock_conn_key = MagicMock()
        mock_conn_key.ssl = False
        mock_get.side_effect = aiohttp.ClientConnectorError(
            connection_key=mock_conn_key,
            os_error=ConnectionRefusedError()
        )

        health = await src.health_check()
        assert health.state == HealthState.UNREACHABLE
        assert "Connection failed" in health.detail
