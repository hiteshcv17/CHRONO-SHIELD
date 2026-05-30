import enum
from sqlalchemy import Column, DateTime, Enum, Integer, String, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SeverityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    severity = Column(Enum(SeverityLevel), nullable=False, default=SeverityLevel.LOW)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    lifecycle_status = Column(
        String, default="open", nullable=False
    )  # e.g., open, acknowledged, resolved, expired
    metadata = Column(String, nullable=True)  # optional JSON string for extra data
