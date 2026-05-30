"""
backend/app/tests/test_database.py

Unit tests verifying PostgreSQL database tables, index definitions,
and composite time-series optimizations.

Run with:
    cd backend
    PYTHONPATH=. pytest app/tests/test_database.py -v
"""

from sqlalchemy import inspect
from app.models.base import Base
from app.models.anomaly import AnomalyRecord
from app.models.weather import WeatherRecordModel
from app.models.traffic import TrafficRecordModel


class TestDatabaseScaffolding:

    def test_anomaly_table_metadata(self):
        """Verify the anomaly_records table structure."""
        model = AnomalyRecord
        assert model.__tablename__ == "anomaly_records"
        
        # Verify core columns exist
        columns = [c.name for c in model.__table__.columns]
        assert "id" in columns
        assert "timestamp" in columns
        assert "metric_name" in columns
        assert "severity" in columns
        assert "score" in columns
        assert "acknowledged" in columns

    def test_weather_table_metadata(self):
        """Verify the weather_records table structure and composite indices."""
        model = WeatherRecordModel
        assert model.__tablename__ == "weather_records"

        columns = [c.name for c in model.__table__.columns]
        assert "id" in columns
        assert "timestamp" in columns
        assert "location" in columns
        assert "temperature_c" in columns
        assert "humidity_pct" in columns
        assert "wind_speed_ms" in columns
        assert "precipitation_mm" in columns

        # Verify composite index exists
        indexes = model.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert "idx_weather_loc_time" in index_names, "Composite index idx_weather_loc_time is missing!"

        # Verify index columns
        composite_idx = next(idx for idx in indexes if idx.name == "idx_weather_loc_time")
        idx_cols = [col.name for col in composite_idx.columns]
        assert "location" in idx_cols
        assert "timestamp" in idx_cols

    def test_traffic_table_metadata(self):
        """Verify the traffic_records table structure and composite indices."""
        model = TrafficRecordModel
        assert model.__tablename__ == "traffic_records"

        columns = [c.name for c in model.__table__.columns]
        assert "id" in columns
        assert "timestamp" in columns
        assert "corridor_id" in columns
        assert "flow_speed_kmh" in columns
        assert "jam_factor" in columns
        assert "congestion_level" in columns
        assert "travel_time_seconds" in columns

        # Verify composite index exists
        indexes = model.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert "idx_traffic_corridor_time" in index_names, "Composite index idx_traffic_corridor_time is missing!"

        composite_idx = next(idx for idx in indexes if idx.name == "idx_traffic_corridor_time")
        idx_cols = [col.name for col in composite_idx.columns]
        assert "corridor_id" in idx_cols
        assert "timestamp" in idx_cols

    def test_unified_base_registration(self):
        """Verify all three time-series models register to the same declarative Base metadata."""
        registered_tables = Base.metadata.tables.keys()
        assert "anomaly_records" in registered_tables
        assert "weather_records" in registered_tables
        assert "traffic_records" in registered_tables
