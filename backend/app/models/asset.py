from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime
from app.models.base import Base


class Asset(Base):
    """
    SQLAlchemy model representing physical infrastructure assets
    (e.g., transformers, traffic zones, water pipelines, public systems)
    with dynamic key-value metadata.
    """
    __tablename__ = "assets"

    id = Column(String(50), primary_key=True, index=True, default=lambda: f"ast-{uuid.uuid4().hex[:8]}")
    name = Column(String(255), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False, index=True)  # TRANSFORMER, TRAFFIC_ZONE, WATER_PIPELINE, PUBLIC_SYSTEM
    status = Column(String(50), default="NOMINAL", nullable=False, index=True)  # NOMINAL, WARNING, CRITICAL, MAINTENANCE, DECOMMISSIONED
    region = Column(String(100), nullable=False, index=True)  # e.g., North Sector, Downtown Grid, etc.
    metadata_json = Column(String(4000), nullable=True)  # JSON-serialized metadata attributes
    installation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_maintenance = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def dynamic_metadata(self):
        import json
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}

    @dynamic_metadata.setter
    def dynamic_metadata(self, value):
        import json
        if value is None:
            self.metadata_json = None
        else:
            self.metadata_json = json.dumps(value)
