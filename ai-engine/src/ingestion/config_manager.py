"""
ai-engine/src/ingestion/config_manager.py

Per-source configuration management.
Loads source definitions from a YAML file (sources.yaml) or falls back
to environment variables. Provides runtime reload support.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

logger = logging.getLogger("ingestion.config_manager")

# Default path to sources YAML — ai-engine/configs/sources.yaml
# __file__ = ai-engine/src/ingestion/config_manager.py → parents[2] = ai-engine/
_DEFAULT_CONFIG_PATH = Path(__file__).parents[2] / "configs" / "sources.yaml"


# ==============================================================================
# SourceConfig Dataclass
# ==============================================================================

@dataclass
class SourceConfig:
    """
    Complete configuration for a single data source.
    Populated by ConfigManager from YAML or environment variables.
    """
    name:              str
    enabled:           bool            = True
    endpoint:          str             = ""
    api_key:           str             = ""          # Loaded from env var at runtime
    interval_seconds:  int             = 300         # Default: every 5 minutes
    timeout_seconds:   int             = 10
    max_retries:       int             = 3
    retry_backoff:     float           = 1.5         # Exponential back-off multiplier
    extra:             Dict            = field(default_factory=dict)

    def mask_secrets(self) -> Dict:
        """Return a safe-to-log representation without exposing the API key."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "endpoint": self.endpoint,
            "api_key": "***" if self.api_key else "<not set>",
            "interval_seconds": self.interval_seconds,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_backoff": self.retry_backoff,
            "extra": self.extra,
        }


# ==============================================================================
# ConfigManager
# ==============================================================================

class ConfigManager:
    """
    Loads and manages SourceConfig instances.

    Priority order:
        1. Environment variables (CHRONOSHIELD_<SOURCE>_API_KEY, etc.)
        2. YAML config file (configs/sources.yaml)
        3. Sensible defaults on SourceConfig
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._path: Path = config_path or _DEFAULT_CONFIG_PATH
        self._configs: Dict[str, SourceConfig] = {}
        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """
        Parse the YAML config file and build SourceConfig objects.
        Injects API keys from matching environment variables.
        """
        raw: Dict = {}

        if _YAML_AVAILABLE and self._path.exists():
            with open(self._path, "r") as fh:
                raw = yaml.safe_load(fh) or {}
            logger.info(f"Loaded source configs from: {self._path}")
        else:
            if not _YAML_AVAILABLE:
                logger.warning("PyYAML not installed — using default SourceConfig values only.")
            else:
                logger.warning(f"Config file not found at {self._path} — using defaults.")

        sources_raw: List[Dict] = raw.get("sources", [])
        self._configs = {}

        for entry in sources_raw:
            name = entry.get("name", "").lower()
            if not name:
                logger.warning("Skipping source entry with no 'name' field.")
                continue

            # Inject API key from environment variable if available
            env_key_name = f"CHRONOSHIELD_{name.upper()}_API_KEY"
            api_key = os.environ.get(env_key_name, entry.get("api_key", ""))

            config = SourceConfig(
                name=name,
                enabled=entry.get("enabled", True),
                endpoint=entry.get("endpoint", ""),
                api_key=api_key,
                interval_seconds=entry.get("interval_seconds", 300),
                timeout_seconds=entry.get("timeout_seconds", 10),
                max_retries=entry.get("max_retries", 3),
                retry_backoff=entry.get("retry_backoff", 1.5),
                extra=entry.get("extra", {}),
            )
            self._configs[name] = config
            logger.debug(f"Registered source config: {config.mask_secrets()}")

        self._loaded = True
        logger.info(
            f"ConfigManager loaded {len(self._configs)} source(s): "
            f"{list(self._configs.keys())}"
        )

    def reload(self) -> None:
        """Hot-reload config from disk without restarting the process."""
        logger.info("Reloading source configurations from disk...")
        self.load()

    def get(self, source_name: str) -> Optional[SourceConfig]:
        """Return config for a specific source, or None if unknown."""
        self._ensure_loaded()
        return self._configs.get(source_name.lower())

    def list_all(self) -> List[SourceConfig]:
        """Return configs for all registered sources."""
        self._ensure_loaded()
        return list(self._configs.values())

    def list_enabled(self) -> List[SourceConfig]:
        """Return configs for all sources where enabled=True."""
        return [c for c in self.list_all() if c.enabled]

    def summary(self) -> str:
        total   = len(self._configs)
        enabled = len(self.list_enabled())
        return f"ConfigManager: {total} sources registered, {enabled} enabled."

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()


# Module-level singleton
config_manager = ConfigManager()
