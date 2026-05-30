"""
ai-engine/src/nlp/classifier.py

Modular NLP Pipeline and Dynamic Unsupervised Clustering Engine for ChronoShield AI.
Includes lexicon classification, sentiment analysis, urgency scoring, explainability,
and TF-IDF + KMeans clustering.
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Any, Optional

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans

    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

logger = logging.getLogger("nlp.classifier")


class InfrastructureNLPClassifier:
    """
    Modular, rule-based and lexicon-driven NLP Classifier.
    Analyzes raw complaint text to compute:
      1. Infrastructure Category (POWER, TRAFFIC, WATER, INTERNET, PUBLIC_INFRASTRUCTURE)
      2. Polarity Sentiment Score [0.0 - 1.0]
      3. Urgency Score [0.0 - 100.0]
      4. Keyword Extraction
      5. Rationale Explainability
    """

    def __init__(self) -> None:
        # 1. Define Category Keywords and Base Weights
        self.category_patterns = {
            "POWER": [
                "power outage",
                "blackout",
                "no power",
                "electricity grid",
                "power line",
                "no electricity",
                "blown transformer",
                "substation down",
                "grid failure",
                "grid outage",
            ],
            "TRAFFIC": [
                "traffic jam",
                "gridlock",
                "congestion",
                "heavy traffic",
                "accident blocked",
                "road blocked",
                "bumper to bumper",
                "lanes closed",
                "highway block",
                "car crash",
            ],
            "WATER": [
                "water leakage",
                "burst pipe",
                "water main leak",
                "flooding",
                "no water",
                "water pressure",
                "sewer backup",
                "drain clogged",
                "pipe leak",
                "flooded street",
            ],
            "INTERNET": [
                "wifi failed",
                "wifi down",
                "network down",
                "no signal",
                "internet outage",
                "fiber cut",
                "offline",
                "slow connection",
                "broadband issue",
                "no internet",
                "network failure",
            ],
            "PUBLIC_INFRASTRUCTURE": [
                "pothole",
                "traffic light broken",
                "broken street light",
                "bridge damage",
                "fallen tree",
                "sidewalk cracked",
                "public park litter",
                "clogged storm drain",
                "damaged railing",
                "graffiti",
                "street light out",
            ],
        }

        # Base Urgency Levels
        self.base_urgencies = {
            "POWER": 65.0,
            "TRAFFIC": 45.0,
            "WATER": 70.0,
            "INTERNET": 50.0,
            "PUBLIC_INFRASTRUCTURE": 35.0,
            "GENERAL": 20.0,
        }

        # Modifiers that worsen sentiment and increase urgency
        self.negative_lexicon = {
            "terrible": 0.10,
            "worst": 0.15,
            "awful": 0.10,
            "catastrophic": 0.20,
            "emergency": 0.20,
            "stuck": 0.08,
            "broken": 0.08,
            "angry": 0.05,
            "danger": 0.15,
            "hazard": 0.12,
            "annoyed": 0.05,
            "urgent": 0.15,
            "helpless": 0.08,
            "unsafe": 0.15,
        }

        # Modifiers that improve sentiment and decrease severity
        self.positive_lexicon = {
            "resolved": 0.30,
            "fixed": 0.25,
            "restored": 0.30,
            "better": 0.15,
            "thankfully": 0.20,
            "cleared": 0.20,
            "solved": 0.25,
            "working": 0.15,
        }

    def classify(self, text: str) -> Dict[str, Any]:
        """
        Analyze a single complaint post text and return enriched classification.
        """
        text_lower = text.lower()
        matched_category = "GENERAL"
        matched_trigger = "general complaint"
        extracted_keywords = []

        # 1. Category Lexicon Matching
        max_match_len = 0
        for category, keywords in self.category_patterns.items():
            for kw in keywords:
                if kw in text_lower:
                    extracted_keywords.append(kw)
                    # Use longest matching keyword pattern to prevent ambiguity
                    if len(kw) > max_match_len:
                        matched_category = category
                        matched_trigger = kw
                        max_match_len = len(kw)

        # 2. Sentiment Analysis
        sentiment = 0.50  # Neutral baseline
        negatives_found = []
        positives_found = []

        for neg, weight in self.negative_lexicon.items():
            if neg in text_lower:
                sentiment -= weight
                negatives_found.append(neg)
                extracted_keywords.append(neg)

        for pos, weight in self.positive_lexicon.items():
            if pos in text_lower:
                sentiment += weight
                positives_found.append(pos)
                extracted_keywords.append(pos)

        # Clamp sentiment between 0.01 and 0.99
        sentiment = max(0.01, min(0.99, sentiment))

        # 3. Severity Classification based on sentiment
        if sentiment < 0.25:
            severity = "CRITICAL"
        elif sentiment < 0.50:
            severity = "WARNING"
        else:
            severity = "INFO"

        # 4. Urgency Calculation
        base_urgency = self.base_urgencies[matched_category]
        urgency = base_urgency

        # Negatives and low sentiment boost urgency
        sentiment_booster = (1.0 - sentiment) * 25.0
        urgency += sentiment_booster

        # Specific modifiers boosts
        for neg in negatives_found:
            if neg in ["emergency", "danger", "hazard", "urgent", "unsafe"]:
                urgency += 10.0
            else:
                urgency += 3.0

        # Punctuation/Capitalization indicators
        if "!" in text:
            urgency += 5.0

        # Check if > 30% of characters are uppercase (excluding spaces/numbers)
        alpha_chars = [c for c in text if c.isalpha()]
        if alpha_chars:
            cap_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if cap_ratio > 0.35:
                urgency += 8.0

        # Positives reduce urgency significantly
        if positives_found:
            urgency = max(10.0, urgency - 35.0)

        # Clamp urgency between 0.0 and 100.0
        urgency = round(max(0.0, min(100.0, urgency)), 1)
        sentiment = round(sentiment, 2)

        # 5. Rationale Generation (Explainability)
        explanation_parts = []
        if matched_category != "GENERAL":
            explanation_parts.append(
                f"Classified under {matched_category} due to pattern '{matched_trigger}'."
            )
        else:
            explanation_parts.append(
                "Classified under GENERAL due to no specific infrastructure pattern matching."
            )

        if negatives_found:
            explanation_parts.append(
                f"Sentiment reduced to {sentiment} by negative words {negatives_found}."
            )
        if positives_found:
            explanation_parts.append(
                f"Sentiment improved to {sentiment} by positive/resolution keywords {positives_found}."
            )

        explanation_parts.append(
            f"Urgency scored at {urgency}/100 (base: {base_urgency}, "
            f"sentiment adjustment: +{sentiment_booster:.1f}, "
            f"punctuation/caps boost: {'applied' if '!' in text or urgency > base_urgency + sentiment_booster else 'none'})."
        )
        explanation = " ".join(explanation_parts)

        # Remove duplicate keywords while preserving order
        unique_kws = []
        for k in extracted_keywords:
            if k not in unique_kws:
                unique_kws.append(k)

        return {
            "category": matched_category,
            "matched_keyword": matched_trigger,
            "sentiment_score": sentiment,
            "severity": severity,
            "urgency_score": urgency,
            "keywords": ", ".join(unique_kws) if unique_kws else matched_trigger,
            "explanation": explanation[:500],  # Cap at database length
        }


class ComplaintClusteringEngine:
    """
    Unsupervised text clustering engine grouping complaints dynamically using TF-IDF and K-Means.
    Falls back gracefully if scikit-learn is missing or complaint lists are small.
    """

    @staticmethod
    def cluster_complaints(
        complaints: List[Dict[str, Any]], n_clusters: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Dynamically group complaints, returning the enriched list with cluster_tag values
        along with summary info about the clusters.
        """
        if not complaints:
            return []

        # If scikit-learn is missing or too few complaints, assign default clusters
        if not _SKLEARN_AVAILABLE or len(complaints) < 3:
            logger.info(
                "Skipping K-Means clustering (scikit-learn missing or insufficient complaints)."
            )
            for c in complaints:
                # Assign default category-based cluster tags
                cat = c.get("category", "GENERAL").upper()
                c["cluster_tag"] = f"{cat} Event Hub"
            return complaints

        try:
            # 1. Vectorize text corpus
            texts = [c.get("text", "") for c in complaints]
            vectorizer = TfidfVectorizer(stop_words="english", max_features=100)
            X = vectorizer.fit_transform(texts)

            # 2. Fit K-Means
            k = min(n_clusters, len(complaints))
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)

            # 3. Extract top terms for each cluster to label it
            feature_names = vectorizer.get_feature_names_out()
            cluster_labels = {}

            for cluster_idx in range(k):
                # Get indices of complaints in this cluster
                indices = [i for i, label in enumerate(labels) if label == cluster_idx]
                if not indices:
                    cluster_labels[cluster_idx] = "General Incident Group"
                    continue

                # Compute mean centroid or top terms in this cluster
                cluster_centroid = kmeans.cluster_centers_[cluster_idx]
                top_term_indices = cluster_centroid.argsort()[::-1][:3]
                top_terms = [
                    feature_names[idx]
                    for idx in top_term_indices
                    if cluster_centroid[idx] > 0.01
                ]

                # Generate descriptive label
                if not top_terms:
                    cluster_labels[cluster_idx] = "General Infrastructure Hub"
                else:
                    title_terms = [t.capitalize() for t in top_terms]
                    cluster_labels[cluster_idx] = f"{' & '.join(title_terms)} Network"

            # 4. Map back to complaints
            for idx, c in enumerate(complaints):
                c["cluster_tag"] = cluster_labels[labels[idx]]

            return complaints

        except Exception as e:
            logger.error(
                f"Unsupervised clustering failed: {e}. Using category tag fallbacks."
            )
            for c in complaints:
                cat = c.get("category", "GENERAL").upper()
                c["cluster_tag"] = f"{cat} Cluster"
            return complaints
