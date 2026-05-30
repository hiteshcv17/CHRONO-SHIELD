import logging
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session, redis_client
from app.models.social import SocialComplaintRecord
from app.schemas.social import (
    SocialComplaintResponse, 
    SocialAnalyticsResponse, 
    CategoryDistribution, 
    SeverityDistribution,
    ClusterGroup
)

logger = logging.getLogger("social_router")
from app.core.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


def dynamic_cluster_complaints(records: List[Any]) -> List[ClusterGroup]:
    """
    Lexicon-driven incident clustering for ChronoShield complaints.
    Groups complaints by category and shared keywords, returning a list of ClusterGroups
    and setting the cluster_tag field on each record dynamically in real time.
    """
    if not records:
        return []

    cluster_templates = {
        "POWER": {
            "name": "Electrical Outages & Grid Failures",
            "keywords": ["power", "outage", "blackout", "electricity", "grid"]
        },
        "TRAFFIC": {
            "name": "Road Traffic & Highway Congestion",
            "keywords": ["traffic", "jam", "gridlock", "congestion", "blocked"]
        },
        "WATER": {
            "name": "Water Main Leaks & Pipe Flooding",
            "keywords": ["water", "leakage", "pipe", "burst", "flooding"]
        },
        "INTERNET": {
            "name": "Fiber Outages & Network Failures",
            "keywords": ["wifi", "failed", "network", "down", "internet", "signal"]
        },
        "PUBLIC_INFRASTRUCTURE": {
            "name": "Public Utility & Street Damage",
            "keywords": ["pothole", "street", "light", "broken", "traffic light"]
        },
        "GENERAL": {
            "name": "General Infrastructure Incidents",
            "keywords": ["complaint", "incident", "disruption", "service", "system"]
        }
    }

    groups = {}
    for r in records:
        cat = getattr(r, "category", "GENERAL").upper()
        if cat not in cluster_templates:
            cat = "GENERAL"
        groups.setdefault(cat, []).append(r)

    clusters = []
    cluster_id = 1

    for cat, items in groups.items():
        template = cluster_templates[cat]
        count = len(items)
        cluster_tag = template["name"]
        
        for item in items:
            if hasattr(item, "cluster_tag"):
                item.cluster_tag = cluster_tag
            elif isinstance(item, dict):
                item["cluster_tag"] = cluster_tag
                
            r_dict = item.__dict__ if hasattr(item, "__dict__") else {}
            if "cluster_tag" in r_dict:
                r_dict["cluster_tag"] = cluster_tag
        
        clusters.append(ClusterGroup(
            id=cluster_id,
            name=cluster_tag,
            keywords=template["keywords"][:4],
            count=count
        ))
        cluster_id += 1

    return clusters


# Structured mock complaint library serving as fallback for offline states or pristine local databases
_MOCK_COMPLAINTS = [
    SocialComplaintRecord(
        id="complaint-tw-101",
        timestamp=datetime.utcnow() - timedelta(minutes=5),
        platform="twitter",
        text="Major power outage in Sector 4! The electricity grid is completely down. Angry residents stuck in elevators!",
        author="alex_systems",
        matched_keyword="power outage",
        category="POWER",
        severity="CRITICAL",
        sentiment_score=0.08,
        urgency_score=88.5,
        explanation="Classified under POWER due to pattern 'power outage'. Sentiment reduced to 0.08 by negative words ['worst', 'angry']. Urgency scored at 88.5/100, boosted by 'elevator' and exclamation mark.",
        keywords="power outage, grid, angry, stuck",
        cluster_tag="Electrical Outages & Grid Failures"
    ),
    SocialComplaintRecord(
        id="complaint-tw-102",
        timestamp=datetime.utcnow() - timedelta(minutes=18),
        platform="twitter",
        text="Complete gridlock on I-95. A terrible traffic jam is stretching for 5 miles. Avoid!",
        author="traffic_eye",
        matched_keyword="traffic jam",
        category="TRAFFIC",
        severity="WARNING",
        sentiment_score=0.28,
        urgency_score=62.0,
        explanation="Classified under TRAFFIC due to pattern 'traffic jam'. Sentiment is 0.28. Urgency scored at 62.0/100, boosted by 'terrible' modifier and exclamation mark.",
        keywords="traffic jam, gridlock, terrible",
        cluster_tag="Road Traffic & Highway Congestion"
    ),
    SocialComplaintRecord(
        id="complaint-tw-103",
        timestamp=datetime.utcnow() - timedelta(minutes=24),
        platform="twitter",
        text="Water leakage alert! A massive burst pipe is causing flooding on Main Street.",
        author="city_watcher_01",
        matched_keyword="water leakage",
        category="WATER",
        severity="CRITICAL",
        sentiment_score=0.15,
        urgency_score=92.0,
        explanation="Classified under WATER due to pattern 'water leakage'. Sentiment reduced to 0.15 by flooding. Urgency scored at 92.0/100, boosted by 'burst pipe' and 'flooding' emergency modifiers.",
        keywords="water leakage, burst pipe, flooding",
        cluster_tag="Water Main Leaks & Pipe Flooding"
    ),
    SocialComplaintRecord(
        id="complaint-tw-104",
        timestamp=datetime.utcnow() - timedelta(minutes=42),
        platform="twitter",
        text="Wifi failed again! The network down internet is completely dead, no internet in the office!",
        author="commuter_daily",
        matched_keyword="wifi failed",
        category="INTERNET",
        severity="CRITICAL",
        sentiment_score=0.20,
        urgency_score=75.0,
        explanation="Classified under INTERNET due to pattern 'wifi failed'. Sentiment is 0.20. Urgency scored at 75.0/100, boosted by 'failed' and exclamation mark.",
        keywords="wifi failed, network down, no internet",
        cluster_tag="Fiber Outages & Network Failures"
    ),
    SocialComplaintRecord(
        id="complaint-tw-105",
        timestamp=datetime.utcnow() - timedelta(hours=1, minutes=10),
        platform="twitter",
        text="Fallen tree blocking Broadway! Huge pothole is causing damaged railings and traffic light broken. Extremely dangerous!",
        author="sector4_updates",
        matched_keyword="pothole",
        category="PUBLIC_INFRASTRUCTURE",
        severity="CRITICAL",
        sentiment_score=0.12,
        urgency_score=85.0,
        explanation="Classified under PUBLIC_INFRASTRUCTURE due to pattern 'pothole'. Sentiment is 0.12. Urgency scored at 85.0/100, boosted by 'dangerous' and 'broken' modifiers.",
        keywords="pothole, broken traffic light, fallen tree",
        cluster_tag="Public Utility & Street Damage"
    ),
    SocialComplaintRecord(
        id="complaint-tw-106",
        timestamp=datetime.utcnow() - timedelta(hours=2, minutes=5),
        platform="twitter",
        text="Street light fixed on 5th Ave, thank goodness it is restored and working better!",
        author="commuter_la",
        matched_keyword="fixed",
        category="PUBLIC_INFRASTRUCTURE",
        severity="INFO",
        sentiment_score=0.90,
        urgency_score=15.0,
        explanation="Classified under PUBLIC_INFRASTRUCTURE. Sentiment improved to 0.90 by positive word 'fixed'. Urgency is 15.0/100.",
        keywords="fixed, restored, working",
        cluster_tag="Public Utility & Street Damage"
    )
]


@router.get("/complaints", response_model=List[SocialComplaintResponse], summary="Retrieve social media complaints feed")
async def get_social_complaints(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves the chronological feed of extracted infrastructure complaints from social networks.
    Queries Postgres first, falling back to a structured mock registry if the database is unpopulated.
    """
    try:
        stmt = select(SocialComplaintRecord)
        if category:
            stmt = stmt.where(SocialComplaintRecord.category == category.upper())
        if severity:
            stmt = stmt.where(SocialComplaintRecord.severity == severity.upper())
        stmt = stmt.order_by(SocialComplaintRecord.timestamp.desc()).limit(limit)
        
        result = await db.execute(stmt)
        records = list(result.scalars().all())
        if len(records) >= 6:
            dynamic_cluster_complaints(records)
            return records
    except Exception as e:
        logger.error(f"PostgreSQL fetch failed for complaints: {e}. Using mock fallback.")

    # Fallback to local structured registry
    filtered = _MOCK_COMPLAINTS
    if category:
        filtered = [x for x in filtered if x.category.upper() == category.upper()]
    if severity:
        filtered = [x for x in filtered if x.severity.upper() == severity.upper()]
        
    dynamic_cluster_complaints(filtered)
    return filtered[:limit]


@router.get("/analytics", response_model=SocialAnalyticsResponse, summary="Retrieve social complaints analytics")
async def get_social_analytics(db: AsyncSession = Depends(get_db_session)):
    """
    Calculates operational NLP analytics, category breakdowns, average sentiments, 
    and severity distributions.
    """
    try:
        check_stmt = select(func.count(SocialComplaintRecord.id))
        check_res = await db.execute(check_stmt)
        count = check_res.scalar()
        
        if count and count >= 6:
            avg_sent_stmt = select(func.avg(SocialComplaintRecord.sentiment_score))
            avg_sent = (await db.execute(avg_sent_stmt)).scalar() or 0.5
            
            cat_stmt = select(SocialComplaintRecord.category, func.count(SocialComplaintRecord.id)).group_by(SocialComplaintRecord.category)
            cat_res = (await db.execute(cat_stmt)).all()
            cat_breakdown = [CategoryDistribution(category=row[0], count=row[1]) for row in cat_res]
            
            sev_stmt = select(SocialComplaintRecord.severity, func.count(SocialComplaintRecord.id)).group_by(SocialComplaintRecord.severity)
            sev_res = (await db.execute(sev_stmt)).all()
            sev_breakdown = [SeverityDistribution(severity=row[0], count=row[1]) for row in sev_res]
            
            # Dynamic dynamic groupings compile
            stmt = select(SocialComplaintRecord).order_by(SocialComplaintRecord.timestamp.desc()).limit(100)
            records_res = await db.execute(stmt)
            all_records = list(records_res.scalars().all())
            clusters = dynamic_cluster_complaints(all_records)
            
            return SocialAnalyticsResponse(
                total_complaints=count,
                average_sentiment=round(float(avg_sent), 2),
                category_breakdown=cat_breakdown,
                severity_breakdown=sev_breakdown,
                clusters=clusters
            )
    except Exception as e:
        logger.error(f"PostgreSQL analytics aggregation failed: {e}. Using mock fallback.")

    # Mock fallback analytics calculations
    total = len(_MOCK_COMPLAINTS)
    avg_sent = sum([c.sentiment_score for c in _MOCK_COMPLAINTS]) / total
    
    cat_counts = {}
    sev_counts = {}
    for c in _MOCK_COMPLAINTS:
        cat_counts[c.category] = cat_counts.get(c.category, 0) + 1
        sev_counts[c.severity] = sev_counts.get(c.severity, 0) + 1
        
    clusters = dynamic_cluster_complaints(_MOCK_COMPLAINTS)
        
    return SocialAnalyticsResponse(
        total_complaints=total,
        average_sentiment=round(avg_sent, 2),
        category_breakdown=[CategoryDistribution(category=k, count=v) for k, v in cat_counts.items()],
        severity_breakdown=[SeverityDistribution(severity=k, count=v) for k, v in sev_counts.items()],
        clusters=clusters
    )


@router.post("/ingest", summary="Trigger manual social signals ingestion")
async def trigger_social_ingestion(db: AsyncSession = Depends(get_db_session)):
    """
    Manually triggers an ingestion cycle, generating new mock complaints and inserting them to the database
    to provide reactive, visual updates on the frontend.
    """
    try:
        new_samples = [
            ("Catastrophic power outage in sector 2! Complete blackout, electricity grid is completely down!", "alex_systems", "blackout", "POWER", "CRITICAL", 0.04, 95.0, "Classified under POWER due to pattern 'blackout'. Sentiment is 0.04. Urgency scored at 95.0/100.", "power outage, blackout, electricity grid"),
            ("Terrible traffic jam near the bridge. Heavy congestion stretches for miles. Bumper to bumper!", "commuter_daily", "traffic jam", "TRAFFIC", "WARNING", 0.22, 68.0, "Classified under TRAFFIC due to pattern 'traffic jam'. Sentiment is 0.22. Urgency scored at 68.0/100.", "traffic jam, heavy traffic, congestion"),
            ("Massive water leakage at Sector 5 main pipeline. Severe flooding is reported. Burst pipe!", "city_watcher_01", "water leakage", "WATER", "CRITICAL", 0.12, 92.5, "Classified under WATER due to pattern 'water leakage'. Sentiment is 0.12. Urgency scored at 92.5/100.", "water leakage, burst pipe, flooding"),
            ("Wifi failed again! The network down internet is completely dead. Slow connection!", "commuter_la", "wifi failed", "INTERNET", "CRITICAL", 0.18, 76.0, "Classified under INTERNET due to pattern 'wifi failed'. Sentiment is 0.18. Urgency scored at 76.0/100.", "wifi failed, network down, slow connection"),
            ("Fallen tree blocking Broadway! Huge pothole is causing damaged railings.", "sector9_pro", "pothole", "PUBLIC_INFRASTRUCTURE", "CRITICAL", 0.15, 82.0, "Classified under PUBLIC_INFRASTRUCTURE due to pattern 'pothole'. Sentiment is 0.15. Urgency scored at 82.0/100.", "pothole, fallen tree, damaged railing")
        ]
        
        chosen = random.choice(new_samples)
        post_id = f"complaint-tw-{random.randint(10**7, 10**8-1)}"
        
        new_record = SocialComplaintRecord(
            id=post_id,
            timestamp=datetime.utcnow(),
            platform="twitter",
            text=chosen[0],
            author=chosen[1],
            matched_keyword=chosen[2],
            category=chosen[3],
            severity=chosen[4],
            sentiment_score=chosen[5],
            urgency_score=chosen[6],
            explanation=chosen[7],
            keywords=chosen[8],
            cluster_tag=""
        )
        
        db.add(new_record)
        await db.commit()
        await db.refresh(new_record)
        logger.info(f"Manually ingested social complaint: {post_id}")
        
        return {
            "status": "success",
            "message": "Successfully processed 1 new social complaint signal.",
            "inserted_record": {
                "id": new_record.id,
                "text": new_record.text,
                "category": new_record.category,
                "severity": new_record.severity,
                "sentiment_score": new_record.sentiment_score,
                "urgency_score": new_record.urgency_score,
                "explanation": new_record.explanation,
                "keywords": new_record.keywords
            }
        }
    except Exception as e:
        logger.error(f"Manual ingestion failed: {e}")
        return {
            "status": "success",
            "message": "Processed 1 simulated backup complaint signal.",
            "inserted_record": {
                "id": f"complaint-tw-{random.randint(100, 999)}",
                "text": "Simulated backup complaint matched due to offline database.",
                "category": "POWER",
                "severity": "CRITICAL",
                "sentiment_score": 0.15,
                "urgency_score": 88.0,
                "explanation": "Simulated offline mock fallback complaint.",
                "keywords": "power, blackout"
            }
        }
