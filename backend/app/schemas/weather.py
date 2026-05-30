from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class WeatherRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime = Field(..., description="Timestamp of the weather reading")
    location: str = Field(..., description="City or location name")
    latitude: float = Field(..., description="Latitude coordinate of the location")
    longitude: float = Field(..., description="Longitude coordinate of the location")
    temperature_c: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity_pct: Optional[float] = Field(
        None, description="Relative humidity percentage"
    )
    wind_speed_ms: Optional[float] = Field(
        None, description="Wind speed in meters per second"
    )
    precipitation_mm: Optional[float] = Field(
        None, description="Precipitation/rainfall in millimeters"
    )


class CurrentWeatherResponse(BaseModel):
    success: bool = Field(..., description="Indicator of a successful data fetch")
    fetched_at: datetime = Field(..., description="Timestamp when data was synced")
    records: List[WeatherRecord] = Field(
        default_factory=list, description="Latest weather readings"
    )


class WeatherTrendsResponse(BaseModel):
    city: str = Field(..., description="Target city for trends")
    records: List[WeatherRecord] = Field(
        default_factory=list, description="Historical time-series series"
    )
