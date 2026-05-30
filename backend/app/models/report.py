from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime
from app.models.base import Base


class Report(Base):
    """
    SQLAlchemy model representing generated platform executive summaries,
    with static URLs to PDF and CSV packages.
    """
    __tablename__ = "reports"

    id = Column(String(50), primary_key=True, index=True, default=lambda: f"rep-{uuid.uuid4().hex[:8]}")
    title = Column(String(255), nullable=False)
    report_type = Column(String(20), nullable=False, index=True)  # DAILY, WEEKLY
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="GENERATING", nullable=False)  # GENERATING, READY, FAILED
    summary = Column(String(3000), nullable=True)  # JSON-serialized stats dictionary
    pdf_path = Column(String(500), nullable=True)
    csv_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
