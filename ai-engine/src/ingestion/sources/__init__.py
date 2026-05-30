"""
ChronoShield AI — Ingestion Sources Sub-Package

Concrete data source implementations.
Import any source to trigger @register_source self-registration.
"""

from src.ingestion.sources.weather import WeatherDataSource
from src.ingestion.sources.traffic import TrafficDataSource
from src.ingestion.sources.energy  import EnergyDataSource
from src.ingestion.sources.social  import SocialMediaDataSource

__all__ = [
    "WeatherDataSource",
    "TrafficDataSource",
    "EnergyDataSource",
    "SocialMediaDataSource",
]
