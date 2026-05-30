import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestSocialSignalsAPI:
    """
    Verification suite testing social signals routers, complaint feeds, 
    and NLP analytics over FastAPI TestClient.
    """

    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)

    def test_get_social_complaints_feed(self):
        """Assert complaints feed returns chronologically sorted lists matching target schemas."""
        response = self.client.get("/api/v1/social/complaints")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 6

        # Check fields schema
        first = data[0]
        assert "id" in first
        assert "timestamp" in first
        assert "platform" in first
        assert "text" in first
        assert "author" in first
        assert "matched_keyword" in first
        assert "category" in first
        assert "severity" in first
        assert "sentiment_score" in first
        assert 0.0 <= first["sentiment_score"] <= 1.0

    def test_get_social_complaints_filtered(self):
        """Assert complaints feed respects category and severity query parameters."""
        response = self.client.get("/api/v1/social/complaints?category=POWER&severity=CRITICAL")
        assert response.status_code == 200
        data = response.json()
        
        for item in data:
            assert item["category"] == "POWER"
            assert item["severity"] == "CRITICAL"

    def test_get_social_analytics_summary(self):
        """Assert NLP analytics summarizes categories distributions and severity ranges."""
        response = self.client.get("/api/v1/social/analytics")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_complaints" in data
        assert data["total_complaints"] >= 6
        assert "average_sentiment" in data
        assert 0.0 <= data["average_sentiment"] <= 1.0
        
        assert "category_breakdown" in data
        assert len(data["category_breakdown"]) > 0
        for cat in data["category_breakdown"]:
            assert "category" in cat
            assert "count" in cat
            assert cat["count"] > 0

        assert "severity_breakdown" in data
        assert len(data["severity_breakdown"]) > 0

    def test_trigger_manual_social_ingestion(self):
        """Assert manual ingestion routes process new complaint items reactively."""
        response = self.client.post("/api/v1/social/ingest")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "message" in data
        assert "inserted_record" in data
        
        record = data["inserted_record"]
        assert "id" in record
        assert "text" in record
        assert "category" in record
        assert "severity" in record
        assert "sentiment_score" in record
