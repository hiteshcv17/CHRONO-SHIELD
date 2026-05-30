from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime
from app.models.base import Base


class AnomalyRecord(Base):
    """
    SQLAlchemy transactional representation of anomalous temporal telemetry signatures.
    """

    __tablename__ = "anomaly_records"

    id = Column(String(50), primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # CRITICAL, WARNING, INFO
    score = Column(Float, nullable=False)  # Reconstruction loss scoring [0.0 - 1.0]
    description = Column(String(500), nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False, index=True)
