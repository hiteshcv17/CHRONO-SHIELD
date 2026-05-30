from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime
from app.models.base import Base


class PrioritizedAlertRecord(Base):
    """
    SQLAlchemy transactional representation of intelligent, prioritized infrastructure alerts.
    Supports de-duplication count monitoring, cooldown timelines, SLA escalation states,
    and z-score priority ranks.
    """
    __tablename__ = "prioritized_alerts"

    id = Column(String(50), primary_key=True, index=True)
    anomaly_id = Column(String(50), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    original_severity = Column(String(20), nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    current_severity = Column(String(20), nullable=False, index=True)
    priority_score = Column(Float, nullable=False, index=True) # Calculated priority [0.0 - 100.0]
    status = Column(String(30), nullable=False, index=True) # ACTIVE, ACKNOWLEDGED, SUPPRESSED, ESCALATED, RESOLVED
    occurrence_count = Column(Integer, nullable=False, default=1) # De-duplication counter
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_occurrence = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    cooldown_until = Column(DateTime, nullable=True, index=True) # If active cooldown block
    escalation_level = Column(Integer, nullable=False, default=0) # 0 = none, 1 = SLA breach tier 1
    description = Column(String(500), nullable=False)
