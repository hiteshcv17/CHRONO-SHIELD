"""
app/core/registry — Pipeline Registry.

Decouples model selection from benchmark orchestration.
Callers request a pipeline by name; the registry resolves it.

Usage:
    pipeline = PipelineRegistry.get("Prophet")
    result = pipeline.run(train, test)

To register a new model:
    PipelineRegistry.register("MyModel", MyModelPipeline)
"""

from typing import Dict, Type
from app.core.pipeline import (
    ForecastingPipeline,
    ProphetPipeline,
    ArimaPipeline,
    EtsPipeline,
)


class PipelineRegistry:
    """
    Static registry mapping model names to pipeline classes.
    Instances are created fresh per benchmark run to ensure state isolation.
    """

    _registry: Dict[str, Type[ForecastingPipeline]] = {
        "Prophet": ProphetPipeline,
        "ARIMA": ArimaPipeline,
        "ETS": EtsPipeline,
    }

    @classmethod
    def register(cls, name: str, pipeline_class: Type[ForecastingPipeline]) -> None:
        """Register a new pipeline class under the given name."""
        cls._registry[name] = pipeline_class

    @classmethod
    def get(cls, name: str, **kwargs) -> ForecastingPipeline:
        """
        Instantiate a fresh pipeline by name.

        Args:
            name: Registered model name (e.g. "Prophet", "ARIMA", "ETS").
            **kwargs: Forwarded to the pipeline constructor.

        Raises:
            KeyError: If the model name is not registered.
        """
        if name not in cls._registry:
            registered = list(cls._registry.keys())
            raise KeyError(
                f"Unknown pipeline '{name}'. Registered models: {registered}"
            )
        return cls._registry[name](**kwargs)

    @classmethod
    def available(cls) -> list:
        """Return a sorted list of all registered model names."""
        return sorted(cls._registry.keys())
