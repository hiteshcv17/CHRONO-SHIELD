"""
ai-engine/src/ingestion/registry.py

Central source registry for ChronoShield AI data ingestion.

Usage — registering a new source:

    from src.ingestion.registry import register_source
    from src.ingestion.base import BaseDataSource

    @register_source("my_source")
    class MyDataSource(BaseDataSource):
        ...

The decorator handles all wiring automatically. The SourceRegistry
singleton is then queryable from the orchestrator and scheduler.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type, TYPE_CHECKING

from src.ingestion.base import BaseDataSource

if TYPE_CHECKING:
    from src.ingestion.config_manager import SourceConfig

logger = logging.getLogger("ingestion.registry")


# ==============================================================================
# Registry Singleton
# ==============================================================================

class SourceRegistry:
    """
    Thread-safe registry mapping source names → their concrete classes.
    Sources self-register via the @register_source decorator at import time,
    requiring zero boilerplate wiring in orchestrator or scheduler.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Type[BaseDataSource]] = {}

    # ------------------------------------------------------------------
    # Registration API
    # ------------------------------------------------------------------

    def register(self, name: str, cls: Type[BaseDataSource]) -> None:
        """Manually register a source class under a given name."""
        if name in self._registry:
            logger.warning(
                f"Source '{name}' is already registered — overwriting with {cls.__name__}."
            )
        self._registry[name] = cls
        logger.debug(f"Registered source: '{name}' → {cls.__name__}")

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_class(self, name: str) -> Optional[Type[BaseDataSource]]:
        """Return the source class registered under `name`, or None."""
        return self._registry.get(name.lower())

    def instantiate(
        self, name: str, config: "SourceConfig"
    ) -> Optional[BaseDataSource]:
        """Instantiate a registered source with the given config."""
        cls = self.get_class(name)
        if cls is None:
            logger.error(
                f"Cannot instantiate source '{name}': not registered. "
                f"Available: {self.list_names()}"
            )
            return None
        instance = cls(config)
        logger.info(f"Instantiated source: {instance!r}")
        return instance

    def list_names(self) -> List[str]:
        """Return all registered source names."""
        return sorted(self._registry.keys())

    def list_classes(self) -> List[Type[BaseDataSource]]:
        """Return all registered source classes."""
        return list(self._registry.values())

    def count(self) -> int:
        return len(self._registry)

    def summary(self) -> str:
        names = ", ".join(self.list_names()) or "<none>"
        return f"SourceRegistry: {self.count()} source(s) registered → [{names}]"

    def __repr__(self) -> str:
        return f"<SourceRegistry sources={self.list_names()}>"


# Module-level singleton — shared across the entire ai-engine process
registry = SourceRegistry()


# ==============================================================================
# @register_source Decorator
# ==============================================================================

def register_source(name: str):
    """
    Class decorator that self-registers a BaseDataSource subclass
    into the global registry at import time.

    Example:
        @register_source("weather")
        class WeatherDataSource(BaseDataSource):
            ...
    """
    def decorator(cls: Type[BaseDataSource]) -> Type[BaseDataSource]:
        if not issubclass(cls, BaseDataSource):
            raise TypeError(
                f"@register_source: {cls.__name__} must subclass BaseDataSource."
            )
        registry.register(name.lower(), cls)
        return cls
    return decorator
