from sqlalchemy import Column, String, Float, DateTime, BigInteger, Index
from app.models.base import Base


class EnergyRecordModel(Base):
    """
    SQLAlchemy representation of historical power grid and energy consumer telemetry.
    """
    __tablename__ = "energy_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    location = Column(String(100), nullable=False, index=True)
    grid_load_kw = Column(Float)
    solar_output_kw = Column(Float)
    energy_demand_kw = Column(Float)
    grid_stability_pct = Column(Float)

    # Composite index for optimized chronological range queries
    __table_args__ = (
        Index("idx_energy_loc_time", "location", timestamp.desc()),
    )
