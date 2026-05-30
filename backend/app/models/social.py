from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime
from app.models.base import Base


class SocialComplaintRecord(Base):
    """
    SQLAlchemy transactional representation of infrastructure complaints extracted from social media.
    """
    __tablename__ = "social_complaints"

    id = Column(String(50), primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    platform = Column(String(30), nullable=False, default="twitter")
    text = Column(String(500), nullable=False)
    author = Column(String(100), nullable=False)
    matched_keyword = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # POWER, TRAFFIC, WATER, INTERNET, PUBLIC_INFRASTRUCTURE
    severity = Column(String(20), nullable=False)              # CRITICAL, WARNING, INFO
    sentiment_score = Column(Float, nullable=False)            # NLP sentiment score [0.0 - 1.0]
    urgency_score = Column(Float, nullable=False, default=0.0) # Calculated urgency score [0.0 - 100.0]
    explanation = Column(String(500), nullable=True)           # Explainable NLP rationale
    keywords = Column(String(250), nullable=True)              # Extracted key terms
    cluster_tag = Column(String(100), nullable=True)           # Unsupervised cluster grouping tag
