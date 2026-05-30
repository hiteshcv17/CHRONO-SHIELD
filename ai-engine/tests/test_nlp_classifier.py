"""
ai-engine/tests/test_nlp_classifier.py

Unit tests for the new explainable NLP Complaint Classifier and Dynamic Clustering Engine.
"""

from __future__ import annotations

import pytest
from src.nlp.classifier import InfrastructureNLPClassifier, ComplaintClusteringEngine


def test_classifier_categories():
    classifier = InfrastructureNLPClassifier()

    # Test POWER category trigger
    res = classifier.classify("Our neighborhood has a major blackout! Help!")
    assert res["category"] == "POWER"
    assert "blackout" in res["keywords"]
    assert res["urgency_score"] > 60.0

    # Test TRAFFIC category trigger
    res = classifier.classify("Terrible gridlock on the main highway, avoidable traffic jam!")
    assert res["category"] == "TRAFFIC"
    assert "traffic jam" in res["keywords"]

    # Test WATER category trigger
    res = classifier.classify("Massive water leakage near Broadway due to a burst pipe!")
    assert res["category"] == "WATER"
    assert "water leakage" in res["keywords"]

    # Test INTERNET category trigger
    res = classifier.classify("Fiber cut is reported! No signal and wifi failed in the whole building!")
    assert res["category"] == "INTERNET"
    assert "wifi failed" in res["keywords"]

    # Test PUBLIC_INFRASTRUCTURE category trigger
    res = classifier.classify("Broken street light is making Broadway unsafe because of potholes.")
    assert res["category"] == "PUBLIC_INFRASTRUCTURE"
    assert "broken street light" in res["keywords"] or "pothole" in res["keywords"]


def test_sentiment_and_severity_modulations():
    classifier = InfrastructureNLPClassifier()

    # Standard positive/resolved tweet
    res = classifier.classify("Thankfully the burst pipe is fixed and flooding is resolved!")
    assert res["sentiment_score"] > 0.60
    assert res["severity"] == "INFO"
    assert res["urgency_score"] < 50.0  # Reduced by positive indicators

    # Extremely critical negative tweet
    res = classifier.classify("EMERGENCY! Power outage is catastrophic! Stuck inside elevators!")
    assert res["sentiment_score"] < 0.20
    assert res["severity"] == "CRITICAL"
    assert res["urgency_score"] > 80.0  # Urgency boosted by modifiers and capital letters/exclamation marks


def test_urgency_scoring():
    classifier = InfrastructureNLPClassifier()

    # Standard neutral general complaint
    res = classifier.classify("Normal feedback about infrastructure.")
    assert res["category"] == "GENERAL"
    assert res["urgency_score"] < 50.0

    # Urgent general complaint
    res = classifier.classify("EMERGENCY! Immediate danger! Urgent help needed!")
    assert res["urgency_score"] > 60.0


def test_explainability_rationales():
    classifier = InfrastructureNLPClassifier()

    res = classifier.classify("Wifi failed again! Catastrophic offline outage!")
    assert "explanation" in res
    assert "INTERNET" in res["explanation"]
    assert "offline" in res["keywords"]


def test_unsupervised_clustering_engine():
    engine = ComplaintClusteringEngine()

    complaints = [
        {"text": "Severe power outage and blackout in sector 4.", "category": "POWER"},
        {"text": "Complete gridlock and heavy traffic jam on I-95.", "category": "TRAFFIC"},
        {"text": "Burst pipe leakage causes massive flooding on Main St.", "category": "WATER"},
        {"text": "Wifi failed completely, fiber cut internet is down.", "category": "INTERNET"},
        {"text": "Potholes and broken street lights on the avenue.", "category": "PUBLIC_INFRASTRUCTURE"}
    ]

    # Cluster these 5 complaints into 3 categories
    clustered = engine.cluster_complaints(complaints, n_clusters=3)
    assert len(clustered) == 5
    for c in clustered:
        assert "cluster_tag" in c
        assert isinstance(c["cluster_tag"], str)
        assert len(c["cluster_tag"]) > 0
