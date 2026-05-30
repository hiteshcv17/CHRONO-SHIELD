from datetime import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from app.models.base import Base


class User(Base):
    """
    SQLAlchemy model representing a system operator / user.
    """
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, index=True, default=lambda: f"usr-{uuid.uuid4().hex[:8]}")
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(String(20), default="VIEWER", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
