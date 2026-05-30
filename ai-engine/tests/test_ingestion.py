"""
ai-engine/tests/test_ingestion.py

Unit tests for the ChronoShield AI multi-source ingestion architecture.

Run with:
    cd ai-engine
    python -m pytest tests/test_ingestion.py -v
"""

import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Trigger self-registration of all source stubs
import src.ingestion.sources.weather   # noqa: F401
import src.ingestion.sources.traffic   # noqa: F401
import src.ingestion.sources.energy    # noqa: F401
import src.ingestion.sources.social    # noqa: F401

from src.ingestion.base import (
    IngestionResult,
    IngestionStatus,
    SourceCategory,
    HealthState,
)
from src.ingestion.config_manager import ConfigManager, SourceConfig
from src.ingestion.registry import SourceRegistry, registry
from src.ingestion.sources.weather import WeatherDataSource
from src.ingestion.sources.traffic import TrafficDataSource
from src.ingestion.sources.energy import EnergyDataSource
from src.ingestion.sources.social import SocialMediaDataSource
from src.ingestion.orchestrator import IngestionOrchestrator


# ==============================================================================
# Fixtures
# ==============================================================================

def make_config(
    name: str = "test",
    enabled: bool = True,
    endpoint: str = "https://example.com/api",
    interval_seconds: int = 300,
    extra: dict = None,
) -> SourceConfig:
    return SourceConfig(
        name=name,
        enabled=enabled,
        endpoint=endpoint,
        api_key="",
        interval_seconds=interval_seconds,
        extra=extra or {},
    )


def run_async(coro):
    """Helper to run coroutines synchronously in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ==============================================================================
# Tests: Source Registry
# ==============================================================================

class TestSourceRegistry:

    def test_all_four_sources_registered(self):
        """All four concrete sources must self-register via @register_source."""
        names = registry.list_names()
        assert "weather" in names, "weather source not registered"
        assert "traffic" in names, "traffic source not registered"
        assert "energy"  in names, "energy source not registered"
        assert "social"  in names, "social source not registered"

    def test_registry_count_at_least_four(self):
        assert registry.count() >= 4

    def test_get_class_returns_correct_type(self):
        cls = registry.get_class("weather")
        assert cls is WeatherDataSource

        cls = registry.get_class("traffic")
        assert cls is TrafficDataSource

        cls = registry.get_class("energy")
        assert cls is EnergyDataSource

        cls = registry.get_class("social")
        assert cls is SocialMediaDataSource

    def test_get_class_case_insensitive(self):
        assert registry.get_class("WEATHER") is WeatherDataSource
        assert registry.get_class("Weather") is WeatherDataSource

    def test_get_class_unknown_returns_none(self):
        assert registry.get_class("nonexistent_source") is None

    def test_instantiate_weather(self):
        cfg = make_config("weather")
        instance = registry.instantiate("weather", cfg)
        assert isinstance(instance, WeatherDataSource)

    def test_instantiate_unknown_returns_none(self):
        cfg = make_config("ghost")
        instance = registry.instantiate("ghost", cfg)
        assert instance is None

    def test_registry_summary_string(self):
        summary = registry.summary()
        assert "SourceRegistry" in summary
        assert "weather" in summary

    def test_register_source_typechecks_base_class(self):
        from src.ingestion.registry import register_source
        with pytest.raises(TypeError):
            @register_source("bad_source")
            class NotASource:
                pass


# ==============================================================================
# Tests: SourceConfig & ConfigManager
# ==============================================================================

class TestConfigManager:

    def test_source_config_defaults(self):
        cfg = SourceConfig(name="test")
        assert cfg.enabled is True
        assert cfg.interval_seconds == 300
        assert cfg.max_retries == 3

    def test_source_config_mask_secrets(self):
        cfg = SourceConfig(name="test", api_key="super-secret-123")
        masked = cfg.mask_secrets()
        assert masked["api_key"] == "***"
        assert "super-secret-123" not in str(masked)

    def test_source_config_mask_no_key(self):
        cfg = SourceConfig(name="test", api_key="")
        assert cfg.mask_secrets()["api_key"] == "<not set>"

    def test_config_manager_loads_yaml(self, tmp_path):
        yaml_content = """
sources:
  - name: weather
    enabled: true
    endpoint: "https://api.example.com/weather"
    interval_seconds: 600
  - name: traffic
    enabled: false
    endpoint: "https://api.example.com/traffic"
    interval_seconds: 300
"""
        config_file = tmp_path / "sources.yaml"
        config_file.write_text(yaml_content)

        mgr = ConfigManager(config_path=config_file)
        mgr.load()

        assert len(mgr.list_all()) == 2
        weather_cfg = mgr.get("weather")
        assert weather_cfg is not None
        assert weather_cfg.enabled is True
        assert weather_cfg.interval_seconds == 600
        assert weather_cfg.endpoint == "https://api.example.com/weather"

    def test_config_manager_list_enabled_filters(self, tmp_path):
        yaml_content = """
sources:
  - name: source_a
    enabled: true
    endpoint: "https://a.com"
  - name: source_b
    enabled: false
    endpoint: "https://b.com"
"""
        config_file = tmp_path / "sources.yaml"
        config_file.write_text(yaml_content)

        mgr = ConfigManager(config_path=config_file)
        all_cfgs = mgr.list_all()
        enabled_cfgs = mgr.list_enabled()

        assert len(all_cfgs) == 2
        assert len(enabled_cfgs) == 1
        assert enabled_cfgs[0].name == "source_a"

    def test_config_manager_get_unknown_returns_none(self, tmp_path):
        yaml_content = "sources: []"
        config_file = tmp_path / "sources.yaml"
        config_file.write_text(yaml_content)

        mgr = ConfigManager(config_path=config_file)
        assert mgr.get("nonexistent") is None

    def test_config_manager_api_key_from_env(self, tmp_path, monkeypatch):
        yaml_content = """
sources:
  - name: weather
    enabled: true
    endpoint: "https://api.example.com"
"""
        config_file = tmp_path / "sources.yaml"
        config_file.write_text(yaml_content)

        monkeypatch.setenv("CHRONOSHIELD_WEATHER_API_KEY", "env-injected-key-xyz")
        mgr = ConfigManager(config_path=config_file)
        cfg = mgr.get("weather")
        assert cfg.api_key == "env-injected-key-xyz"


# ==============================================================================
# Tests: BaseDataSource — Validate
# ==============================================================================

class TestBaseDataSourceValidation:

    def test_validate_passes_with_required_fields(self):
        cfg = make_config("weather", endpoint="https://api.openweathermap.org")
        src = WeatherDataSource(cfg)
        assert src.validate() is True

    def test_validate_fails_missing_endpoint(self):
        cfg = make_config("weather", endpoint="")
        src = WeatherDataSource(cfg)
        assert src.validate() is False


# ==============================================================================
# Tests: Concrete Source Stubs — get_metadata()
# ==============================================================================

class TestSourceMetadata:

    def test_weather_metadata(self):
        cfg = make_config("weather")
        src = WeatherDataSource(cfg)
        meta = src.get_metadata()
        assert meta.name == "weather"
        assert meta.category == SourceCategory.WEATHER
        assert meta.version == "1.0.0"
        assert "temperature_c" in meta.supported_fields

    def test_traffic_metadata(self):
        cfg = make_config("traffic")
        src = TrafficDataSource(cfg)
        meta = src.get_metadata()
        assert meta.name == "traffic"
        assert meta.category == SourceCategory.TRAFFIC
        assert "jam_factor" in meta.supported_fields

    def test_energy_metadata(self):
        cfg = make_config("energy")
        src = EnergyDataSource(cfg)
        meta = src.get_metadata()
        assert meta.name == "energy"
        assert meta.category == SourceCategory.ENERGY
        assert "demand_mwh" in meta.supported_fields

    def test_social_metadata(self):
        cfg = make_config("social")
        src = SocialMediaDataSource(cfg)
        meta = src.get_metadata()
        assert meta.name == "social"
        assert meta.category == SourceCategory.SOCIAL_MEDIA
        assert "sentiment_score" in meta.supported_fields


# ==============================================================================
# Tests: Concrete Source Stubs — fetch()
# ==============================================================================

class TestSourceFetch:

    def test_weather_fetch_returns_ingestion_result(self):
        cfg = make_config("weather", extra={"locations": [{"city": "London", "lat": 51.5, "lon": -0.1}]})
        src = WeatherDataSource(cfg)
        result = run_async(src.fetch())
        assert isinstance(result, IngestionResult)
        assert result.source_name == "weather"
        assert result.status == IngestionStatus.SUCCESS
        assert result.record_count == 1
        assert "temperature_c" in result.records[0] or "_placeholder" in result.records[0]

    def test_traffic_fetch_returns_correct_shape(self):
        cfg = make_config("traffic", extra={"corridors": [{"id": "NYC-I95", "bbox": "..."}]})
        src = TrafficDataSource(cfg)
        result = run_async(src.fetch())
        assert result.source_name == "traffic"
        assert result.status == IngestionStatus.SUCCESS
        assert len(result.records) == 1
        assert "jam_factor" in result.records[0]

    def test_energy_fetch_returns_correct_shape(self):
        cfg = make_config("energy", extra={"regions": ["NYIS", "ERCO"]})
        src = EnergyDataSource(cfg)
        result = run_async(src.fetch())
        assert result.source_name == "energy"
        assert result.status == IngestionStatus.SKIPPED
        assert len(result.records) == 2
        for rec in result.records:
            assert "fuel_mix" in rec
            assert isinstance(rec["fuel_mix"], dict)

    def test_social_fetch_skipped_when_disabled(self):
        cfg = make_config("social", enabled=False)
        src = SocialMediaDataSource(cfg)
        result = run_async(src.fetch())
        assert result.source_name == "social"
        assert result.status == IngestionStatus.SKIPPED
        assert result.record_count == 0

    def test_all_fetch_results_have_timestamp(self):
        sources_and_extra = [
            (WeatherDataSource, make_config("weather")),
            (TrafficDataSource, make_config("traffic")),
            (EnergyDataSource,  make_config("energy")),
        ]
        for cls, cfg in sources_and_extra:
            src = cls(cfg)
            result = run_async(src.fetch())
            assert result.fetched_at is not None


# ==============================================================================
# Tests: Health Check
# ==============================================================================

class TestHealthCheck:

    def test_all_sources_health_check_returns_unknown(self):
        cfgs = [
            make_config("weather"), make_config("traffic"),
            make_config("energy"),  make_config("social", enabled=False),
        ]
        classes = [WeatherDataSource, TrafficDataSource, EnergyDataSource, SocialMediaDataSource]
        expected_states = [HealthState.REACHABLE, HealthState.REACHABLE, HealthState.UNKNOWN, HealthState.UNKNOWN]

        for cls, cfg, expected in zip(classes, cfgs, expected_states):
            src = cls(cfg)
            health = run_async(src.health_check())
            assert health.state == expected
            assert health.source_name == src.get_metadata().name


# ==============================================================================
# Tests: Orchestrator
# ==============================================================================

class TestOrchestrator:

    def test_orchestrator_status_shape(self, tmp_path):
        yaml_content = """
sources:
  - name: weather
    enabled: true
    endpoint: "https://api.openweathermap.org"
    interval_seconds: 600
  - name: traffic
    enabled: false
    endpoint: "https://traffic.ls.hereapi.com"
    interval_seconds: 300
"""
        config_file = tmp_path / "sources.yaml"
        config_file.write_text(yaml_content)

        mgr = ConfigManager(config_path=config_file)
        orch = IngestionOrchestrator(config_manager=mgr)
        run_async(orch.initialize())

        status = orch.status()
        assert "total_sources" in status
        assert "enabled_sources" in status
        assert "sources" in status
        assert status["total_sources"] == 2
        assert status["enabled_sources"] == 1

        source_names = [s["name"] for s in status["sources"]]
        assert "weather" in source_names
        assert "traffic" in source_names

    def test_orchestrator_registered_flag(self, tmp_path):
        yaml_content = """
sources:
  - name: weather
    enabled: true
    endpoint: "https://api.openweathermap.org"
    interval_seconds: 600
"""
        config_file = tmp_path / "sources.yaml"
        config_file.write_text(yaml_content)

        mgr = ConfigManager(config_path=config_file)
        orch = IngestionOrchestrator(config_manager=mgr)
        run_async(orch.initialize())

        status = orch.status()
        weather_status = next(
            s for s in status["sources"] if s["name"] == "weather"
        )
        assert weather_status["registered"] is True
