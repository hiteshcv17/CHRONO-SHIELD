"""
Phase 28 — Explainable AI Reasoning System
Pydantic schemas for the explanation engine.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ContributingFactor(BaseModel):
    """A single identified causal or amplifying factor."""
    factor_id: str
    name: str
    factor_type: str          # PRIMARY | AMPLIFIER | CORRELATE | ENVIRONMENTAL | TEMPORAL
    description: str
    confidence: float         # 0.0–1.0
    weight: float             # relative contribution weight 0.0–1.0
    category: str             # POWER | TRAFFIC | WATER | INTERNET | WEATHER | TEMPORAL
    evidence: List[str]       # Supporting data points or signals
    metric_refs: List[str]    # Metric names this factor relates to


class CorrelationLink(BaseModel):
    """A single edge in the causal correlation chain."""
    from_factor: str
    to_factor: str
    relationship: str         # CAUSED | AMPLIFIED | CORRELATED | PRECEDED | TRIGGERED
    strength: float           # 0.0–1.0
    lag_minutes: int          # Time lag between from and to events


class ReasoningStep(BaseModel):
    """One step in the chain-of-thought explanation."""
    step_index: int
    step_type: str            # OBSERVE | HYPOTHESIZE | CORRELATE | CONCLUDE | RECOMMEND
    title: str
    detail: str
    confidence: float
    supporting_factors: List[str]   # factor_ids


class AnomalyExplanation(BaseModel):
    """
    Full explainable AI output for a single anomaly event.
    """
    anomaly_id: str
    metric_name: str
    severity: str
    category: str
    timestamp: str
    district: str
    score: float

    # ── Natural language outputs ──────────────────────────────────────────────
    headline: str             # One-liner: "Traffic congestion spiked due to…"
    summary: str              # 2–3 sentence narrative explanation
    causal_narrative: str     # Full paragraph with all factors woven in

    # ── Structured reasoning ──────────────────────────────────────────────────
    contributing_factors: List[ContributingFactor]
    correlation_chain: List[CorrelationLink]
    reasoning_steps: List[ReasoningStep]

    # ── Metadata ──────────────────────────────────────────────────────────────
    overall_confidence: float       # 0.0–1.0
    explanation_quality: str        # STRONG | MODERATE | SPECULATIVE
    primary_cause: str
    cascade_risk: str               # LOW | MODERATE | HIGH | CRITICAL
    impacted_systems: List[str]
    recommended_actions: List[str]
    ai_model_version: str
    explanation_latency_ms: int


class ExplainBatchResponse(BaseModel):
    """Batch explanation response — multiple anomalies at once."""
    explanations: List[AnomalyExplanation]
    total_analyzed: int
    high_confidence_count: int
    cross_incident_patterns: List[str]   # Patterns visible across multiple incidents
    system_narrative: str                # Overall system-level narrative
