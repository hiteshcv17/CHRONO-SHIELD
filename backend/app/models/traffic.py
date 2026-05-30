from sqlalchemy import Column, String, Float, DateTime, BigInteger, Integer, Index
from app.models.base import Base


class TrafficRecordModel(Base):
    """
    SQLAlchemy representation of historical highway corridor traffic telemetry.
    """

    __tablename__ = "traffic_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    corridor_id = Column(String(50), nullable=False, index=True)
    bbox = Column(String(200))
    flow_speed_kmh = Column(Float)
    free_flow_speed_kmh = Column(Float)
    jam_factor = Column(Float)
    congestion_level = Column(String(20))
    incident_count = Column(Integer)
    travel_time_seconds = Column(Integer)

    # Composite index for optimized chronological range queries
    __table_args__ = (
        Index("idx_traffic_corridor_time", "corridor_id", timestamp.desc()),
    )
