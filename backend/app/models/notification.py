from datetime import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from app.models.base import Base


class NotificationChannelConfig(Base):
    """
    SQLAlchemy model representing dynamic user/operator configurations for delivery channels.
    Includes state toggling and JSON-serialized credentials/endpoints.
    """

    __tablename__ = "notification_channel_configs"

    id = Column(
        String(50),
        primary_key=True,
        index=True,
        default=lambda: f"cfg-{uuid.uuid4().hex[:8]}",
    )
    channel_type = Column(
        String(20), unique=True, index=True, nullable=False
    )  # EMAIL, TELEGRAM, WEBHOOK
    config = Column(String(1000), nullable=False)  # JSON string representation
    enabled = Column(Boolean, default=True, nullable=False)


class NotificationDeliveryLog(Base):
    """
    SQLAlchemy model representing delivery logs, status tracking, and retry counts
    for multi-channel notifications.
    """

    __tablename__ = "notification_delivery_logs"

    id = Column(
        String(50),
        primary_key=True,
        index=True,
        default=lambda: f"log-{uuid.uuid4().hex[:8]}",
    )
    alert_id = Column(String(50), nullable=True, index=True)
    channel = Column(String(20), nullable=False, index=True)  # EMAIL, TELEGRAM, WEBHOOK
    recipient = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(String(2000), nullable=False)
    priority = Column(
        String(20), nullable=False, index=True
    )  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(20), nullable=False, index=True)  # PENDING, SENT, FAILED
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error_message = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
