"""
ai-engine/tests/test_weather.py

Unit tests for real-time WeatherDataSource ingestion.
Covers metadata, API requests, fallbacks, retries, and health checks.

Run with:
    cd ai-engine
    PYTHONPATH=. pytest tests/test_weather.py -v
"""

import asyncio
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import aiohttp

from src.ingestion.base import IngestionResult, IngestionStatus, HealthState, SourceCategory
from src.ingestion.config_manager import SourceConfig
from src.ingestion.sources.weather import WeatherDataSource


# ==============================================================================
# Helper Fixtures & Builders
# ==============================================================================

def make_weather_config(
    api_key: str = "",
    enabled: bool = True,
    max_retries: int = 1,
    retry_backoff: float = 0.1,
) -> SourceConfig:
    return SourceConfig(
        name="weather",
        enabled=enabled,
        endpoint="https://api.openweathermap.org/data/2.5/weather",
        api_key=api_key,
        interval_seconds=600,
        timeout_seconds=5,
        max_retries=max_retries,
        retry_backoff=retry_backoff,
        extra={
            "locations": [
                {"city": "New York", "lat": 40.7128, "lon": -74.0060},
                {"city": "London", "lat": 51.5074, "lon": -0.1278},
            ]
        },
    )


# ==============================================================================
# Weather Telemetry Tests
# ==============================================================================

class TestWeatherDataSource:

    def test_weather_metadata(self):
        """Verify the static metadata contract."""
        cfg = make_weather_config()
        src = WeatherDataSource(cfg)
        meta = src.get_metadata()

        assert meta.name == "weather"
        assert meta.category == SourceCategory.WEATHER
        assert meta.version == "1.0.0"
        assert "temperature_c" in meta.supported_fields
        assert "humidity_pct" in meta.supported_fields
        assert "wind_speed_ms" in meta.supported_fields
        assert "precipitation_mm" in meta.supported_fields

    def test_validation_rules(self):
        """Ensure validation catches empty endpoint configurations."""
        cfg = make_weather_config()
        src = WeatherDataSource(cfg)
        assert src.validate() is True

        cfg_empty = make_weather_config()
        cfg_empty.endpoint = ""
        src_empty = WeatherDataSource(cfg_empty)
        assert src_empty.validate() is False

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_fetch_open_meteo_fallback(self, mock_get):
        """Verify fallback to public Open-Meteo API when no API key is specified."""
        cfg = make_weather_config(api_key="")  # No key
        src = WeatherDataSource(cfg)

        # Mock Open-Meteo responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "current": {
                "temperature_2m": 22.5,
                "relative_humidity_2m": 60,
                "wind_speed_10m": 18.0,  # 18 km/h = 5.0 m/s
                "precipitation": 1.5,
            }
        })

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get.return_value = mock_context

        result = await src.fetch()

        assert isinstance(result, IngestionResult)
        assert result.status == IngestionStatus.SUCCESS
        assert result.record_count == 2
        assert result.metadata["api_used"] == "Open-Meteo"

        # Check fields match translated Open-Meteo parser rules
        rec = result.records[0]
        assert rec["location"] == "New York"
        assert rec["temperature_c"] == 22.5
        assert rec["humidity_pct"] == 60
        assert rec["wind_speed_ms"] == 5.0  # converted 18.0 / 3.6 = 5.0
        assert rec["precipitation_mm"] == 1.5

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_fetch_open_weather_map_success(self, mock_get):
        """Verify successful fetch using OpenWeatherMap when API key is set."""
        cfg = make_weather_config(api_key="valid-owm-token-998")
        src = WeatherDataSource(cfg)

        # Mock OpenWeatherMap payload response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "main": {
                "temp": 17.2,
                "humidity": 75,
            },
            "wind": {
                "speed": 4.1,
            },
            "clouds": {
                "all": 40,
            },
            "rain": {
                "1h": 0.5,
            }
        })

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get.return_value = mock_context

        result = await src.fetch()

        assert result.status == IngestionStatus.SUCCESS
        assert result.record_count == 2
        assert result.metadata["api_used"] == "OpenWeatherMap"

        rec = result.records[0]
        assert rec["location"] == "New York"
        assert rec["temperature_c"] == 17.2
        assert rec["humidity_pct"] == 75
        assert rec["wind_speed_ms"] == 4.1
        assert rec["precipitation_mm"] == 0.5
        assert rec["cloud_coverage_pct"] == 40

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_owm_401_unauthorized_triggers_fallback(self, mock_get):
        """Verify 401 Unauthorized OWM Key triggers instant fallback to Open-Meteo on the fly."""
        cfg = make_weather_config(api_key="invalid-owm-token")
        src = WeatherDataSource(cfg)

        # Mock first call unauthorized (401), second call fallback success (200)
        mock_response_401 = AsyncMock()
        mock_response_401.status = 401
        
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.json = AsyncMock(return_value={
            "current": {
                "temperature_2m": 12.0,
                "relative_humidity_2m": 85,
                "wind_speed_10m": 7.2,  # 7.2 km/h = 2.0 m/s
                "precipitation": 0.0,
            }
        })

        # Set up side effect context managers
        ctx_401 = MagicMock()
        ctx_401.__aenter__ = AsyncMock(return_value=mock_response_401)
        ctx_401.__aexit__ = AsyncMock(return_value=None)

        ctx_200 = MagicMock()
        ctx_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        ctx_200.__aexit__ = AsyncMock(return_value=None)

        mock_get.side_effect = [ctx_401, ctx_200, ctx_401, ctx_200]

        result = await src.fetch()

        assert result.status == IngestionStatus.SUCCESS
        assert result.record_count == 2
        
        rec = result.records[0]
        assert rec["temperature_c"] == 12.0
        assert rec["wind_speed_ms"] == 2.0

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_health_check_reachable(self, mock_get):
        """Verify health check reports REACHABLE on status 200."""
        cfg = make_weather_config()
        src = WeatherDataSource(cfg)

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
        cfg = make_weather_config()
        src = WeatherDataSource(cfg)

        mock_conn_key = MagicMock()
        mock_conn_key.ssl = False
        mock_get.side_effect = aiohttp.ClientConnectorError(
            connection_key=mock_conn_key,
            os_error=ConnectionRefusedError()
        )

        health = await src.health_check()
        assert health.state == HealthState.UNREACHABLE
        assert "Connection failed" in health.detail
