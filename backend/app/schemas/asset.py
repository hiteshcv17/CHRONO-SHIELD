from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssetBase(BaseModel):
    name: str = Field(..., description="Human-readable asset identifier")
    asset_type: Literal["TRANSFORMER", "TRAFFIC_ZONE", "WATER_PIPELINE", "PUBLIC_SYSTEM"] = Field(..., description="Infrastructure category")
    status: Literal["NOMINAL", "WARNING", "CRITICAL", "MAINTENANCE", "DECOMMISSIONED"] = Field("NOMINAL", description="Operational health status")
    region: str = Field(..., description="Operational geographic region tag")
    dynamic_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Dynamic key-value asset attributes")
    installation_date: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Date of installation")
    last_maintenance: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Date of last maintenance check")

    @field_validator("name", "region")
    @classmethod
    def sanitize_fields(cls, v: str) -> str:
        from app.utils.security import sanitize_text
        return sanitize_text(v)


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[Literal["TRANSFORMER", "TRAFFIC_ZONE", "WATER_PIPELINE", "PUBLIC_SYSTEM"]] = None
    status: Optional[Literal["NOMINAL", "WARNING", "CRITICAL", "MAINTENANCE", "DECOMMISSIONED"]] = None
    region: Optional[str] = None
    dynamic_metadata: Optional[Dict[str, Any]] = None
    installation_date: Optional[datetime] = None
    last_maintenance: Optional[datetime] = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    asset_type: Literal["TRANSFORMER", "TRAFFIC_ZONE", "WATER_PIPELINE", "PUBLIC_SYSTEM"]
    status: Literal["NOMINAL", "WARNING", "CRITICAL", "MAINTENANCE", "DECOMMISSIONED"]
    region: str
    dynamic_metadata: Optional[Dict[str, Any]] = None
    installation_date: datetime
    last_maintenance: datetime
    created_at: datetime
    updated_at: datetime
