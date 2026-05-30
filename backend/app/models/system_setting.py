from sqlalchemy import Column, String
from app.models.base import Base


class SystemSetting(Base):
    """
    SQLAlchemy model representing dynamic system configurations.
    Used for storing toggles and flags (e.g. rate_limiting_enabled).
    """
    __tablename__ = "system_settings"

    key = Column(String(50), primary_key=True, index=True)
    value = Column(String(200), nullable=False)
