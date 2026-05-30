from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional


class SocialComplaintResponse(BaseModel):
    id: str = Field(..., description="Unique complaint record ID.")
    timestamp: datetime = Field(..., description="Timestamp of post creation.")
    platform: str = Field(..., description="Target platform label (e.g. twitter).")
    text: str = Field(..., description="Raw text of the post complaint.")
    author: str = Field(..., description="Post author username/handle.")
    matched_keyword: str = Field(..., description="Key NLP keyword trigger match.")
    category: str = Field(
        ...,
        description="Extracted category: POWER, TRAFFIC, WATER, INTERNET, PUBLIC_INFRASTRUCTURE.",
    )
    severity: str = Field(
        ..., description="Computed risk severity: CRITICAL, WARNING, INFO."
    )
    sentiment_score: float = Field(
        ..., description="Analyzed sentiment scoring bounded [0.0 - 1.0]."
    )
    urgency_score: float = Field(
        0.0, description="Calculated urgency score bounded [0.0 - 100.0]."
    )
    explanation: Optional[str] = Field(
        None, description="Step-by-step explainable NLP rationale."
    )
    keywords: Optional[str] = Field(
        None, description="Comma-separated list of extracted keywords."
    )
    cluster_tag: Optional[str] = Field(
        None, description="Dynamic incident cluster grouping tag."
    )

    model_config = ConfigDict(from_attributes=True)


class CategoryDistribution(BaseModel):
    category: str = Field(..., description="Incident category.")
    count: int = Field(..., description="Incident count.")


class SeverityDistribution(BaseModel):
    severity: str = Field(..., description="Computed risk severity.")
    count: int = Field(..., description="Incident count.")


class ClusterGroup(BaseModel):
    id: int = Field(..., description="Unique cluster ID.")
    name: str = Field(..., description="Generated incident cluster description name.")
    keywords: List[str] = Field(
        ..., description="Top key terms describing the incident cluster."
    )
    count: int = Field(..., description="Number of complaints inside this cluster.")


class SocialAnalyticsResponse(BaseModel):
    total_complaints: int = Field(
        ..., description="Aggregate total of logged complaints."
    )
    average_sentiment: float = Field(
        ..., description="Mean cluster sentiment score bounded [0.0 - 1.0]."
    )
    category_breakdown: List[CategoryDistribution] = Field(
        ..., description="Complaints count per domain category."
    )
    severity_breakdown: List[SeverityDistribution] = Field(
        ..., description="Complaints count per severity tier."
    )
    clusters: List[ClusterGroup] = Field(
        default=[], description="Unsupervised dynamic KMeans incident groupings."
    )
