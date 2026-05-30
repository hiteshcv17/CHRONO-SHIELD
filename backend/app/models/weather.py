from sqlalchemy import Column, String, Float, DateTime, BigInteger, Index
from app.models.base import Base


class WeatherRecordModel(Base):
    """
    SQLAlchemy representation of historical atmospheric weather telemetry.
    """

    __tablename__ = "weather_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    location = Column(String(100), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    temperature_c = Column(Float)
    humidity_pct = Column(Float)
    wind_speed_ms = Column(Float)
    precipitation_mm = Column(Float)
    cloud_coverage_pct = Column(Float)

    # Composite index for optimized chronological range queries
    __table_args__ = (Index("idx_weather_loc_time", "location", timestamp.desc()),)
