from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


class NotificationChannelConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_type: Literal["EMAIL", "TELEGRAM", "WEBHOOK"]
    config: str  # Contains JSON-serialized configuration dict
    enabled: bool


class NotificationChannelConfigUpdate(BaseModel):
    config: Optional[str] = Field(
        None, description="JSON string representation of config"
    )
    enabled: Optional[bool] = Field(None, description="Whether the channel is active")


class NotificationDeliveryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    alert_id: Optional[str] = None
    channel: Literal["EMAIL", "TELEGRAM", "WEBHOOK"]
    recipient: str
    title: str
    message: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    status: Literal["PENDING", "SENT", "FAILED"]
    retry_count: int
    max_retries: int
    error_message: Optional[str] = None
    timestamp: datetime
    sent_at: Optional[datetime] = None


class NotificationTestPayload(BaseModel):
    channel: Literal["EMAIL", "TELEGRAM", "WEBHOOK"]
    recipient: str = Field(..., description="Target address/ID/URL for test")
    message: str = Field(
        "This is a ChronoShield AI test notification.", description="Test content"
    )
