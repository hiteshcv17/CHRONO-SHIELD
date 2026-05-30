import pytest
from datetime import datetime
from app.models.base import Base
from app.models.energy import EnergyRecordModel
from app.services.correlation_service import CorrelationService


class TestCorrelationScaffolding:

    def test_energy_table_metadata(self):
        """Verify the energy_records table structure and composite index."""
        model = EnergyRecordModel
        assert model.__tablename__ == "energy_records"

        columns = [c.name for c in model.__table__.columns]
        assert "id" in columns
        assert "timestamp" in columns
        assert "location" in columns
        assert "grid_load_kw" in columns
        assert "solar_output_kw" in columns
        assert "energy_demand_kw" in columns
        assert "grid_stability_pct" in columns

        # Verify composite index exists
        indexes = model.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert "idx_energy_loc_time" in index_names

        composite_idx = next(idx for idx in indexes if idx.name == "idx_energy_loc_time")
        idx_cols = [col.name for col in composite_idx.columns]
        assert "location" in idx_cols
        assert "timestamp" in idx_cols

    def test_unified_base_registration(self):
        """Verify all time-series models including energy register to the declarative Base."""
        registered_tables = Base.metadata.tables.keys()
        assert "anomaly_records" in registered_tables
        assert "weather_records" in registered_tables
        assert "traffic_records" in registered_tables
        assert "energy_records" in registered_tables

    def test_pearson_correlation_math(self):
        """Verify Pearson correlation calculation with known mathematical vectors."""
        # Perfect positive correlation (r = 1.0)
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert pytest.approx(CorrelationService.pearson_correlation(x, y)) == 1.0

        # Perfect negative correlation (r = -1.0)
        y_neg = [10.0, 8.0, 6.0, 4.0, 2.0]
        assert pytest.approx(CorrelationService.pearson_correlation(x, y_neg)) == -1.0

        # Zero correlation / zero variance safety check
        flat_x = [1.0, 1.0, 1.0, 1.0, 1.0]
        assert CorrelationService.pearson_correlation(flat_x, y) == 0.0

    def test_timestamp_rounding(self):
        """Verify datetime rounder bucketizes correctly to the nearest 10-minute slot."""
        dt1 = datetime(2026, 5, 28, 15, 27, 43)
        dt2 = datetime(2026, 5, 28, 15, 20, 0)
        # Should round down to 15:20:00
        assert CorrelationService.round_timestamp(dt1) == datetime(2026, 5, 28, 15, 20, 0)
        assert CorrelationService.round_timestamp(dt2) == datetime(2026, 5, 28, 15, 20, 0)

    def test_activity_intensity_calculation(self):
        """Verify the 24x7 activity intensity grid is calculated correctly."""
        import asyncio
        async def run_test():
            return await CorrelationService.get_activity_intensity(None, "New York")
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        days, hours, matrix = loop.run_until_complete(run_test())
        assert len(days) == 7
        assert len(hours) == 24
        assert len(matrix) == 7
        assert len(matrix[0]) == 24
        # Validate grid values are between 0 and 1
        for row in matrix:
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_anomaly_concentration_calculation(self):
        """Verify the 24x7 anomaly concentration grid is calculated correctly."""
        import asyncio
        async def run_test():
            return await CorrelationService.get_anomaly_concentration(None, "New York")
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        days, hours, matrix = loop.run_until_complete(run_test())
        assert len(days) == 7
        assert len(hours) == 24
        assert len(matrix) == 7
        assert len(matrix[0]) == 24
        # Validate grid values are integers and >= 0
        for row in matrix:
            for val in row:
                assert isinstance(val, int)
                assert val >= 0


class TestCorrelationAPI:
    """
    Verification suite testing multi-source temporal correlation routers,
    synchronized anomaly detectors, lag analysis, and rolling windowing.
    """

    @classmethod
    def setup_class(cls):
        from fastapi.testclient import TestClient
        from app.main import app
        cls.client = TestClient(app)

    def test_get_correlation_matrix_api(self):
        """Assert GET /matrix returns valid 2D matrix including complaints variables."""
        response = self.client.get("/api/v1/correlation/matrix?city=New York")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "variables" in data
        assert "matrix" in data

        # Check complaints metrics are included in variables
        variables = data["variables"]
        assert any("complaints" in v.lower() for v in variables)
        assert any("urgency" in v.lower() for v in variables)
        assert any("sentiment" in v.lower() for v in variables)

        # Check matrix dimensions match variables
        n = len(variables)
        assert len(data["matrix"]) == n
        for row in data["matrix"]:
            assert len(row) == n
            for val in row:
                assert -1.0 <= val <= 1.0

    def test_get_correlation_matrix_with_window_days(self):
        """Assert GET /matrix filters results correctly with window_days parameter."""
        response = self.client.get("/api/v1/correlation/matrix?city=New York&window_days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["variables"]) > 0

    def test_get_correlation_graph_api(self):
        """Assert GET /graph returns nodes and edges above threshold."""
        response = self.client.get("/api/v1/correlation/graph?city=New York&threshold=0.3")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "nodes" in data
        assert "edges" in data

        # Nodes should have id, label, and group
        for node in data["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "group" in node
            assert node["group"] in ["weather", "traffic", "energy", "anomaly", "social"]

        # Edges should connect valid nodes and have weight above threshold
        node_ids = {node["id"] for node in data["nodes"]}
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "weight" in edge
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids
            assert abs(edge["weight"]) >= 0.3

    def test_get_time_overlays_api(self):
        """Assert GET /overlays aligns timestamps and parallel series."""
        response = self.client.get("/api/v1/correlation/overlays?city=New York&window_days=1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "timestamps" in data
        assert "series" in data

        # Timestamps and series list lengths must be aligned
        timestamps = data["timestamps"]
        series = data["series"]
        
        # Verify social metrics exist in aligned series
        assert "complaints_count" in series
        assert "complaints_urgency" in series
        assert "complaints_sentiment" in series

        n = len(timestamps)
        for key, s_values in series.items():
            assert len(s_values) == n

    def test_get_synchronized_anomalies_api(self):
        """Assert GET /synchronized-anomalies returns concurrent events."""
        response = self.client.get("/api/v1/correlation/synchronized-anomalies?city=New York")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "anomalies" in data

        for anom in data["anomalies"]:
            assert "id" in anom
            assert "timestamp" in anom
            assert "metrics" in anom
            assert "severity" in anom
            assert "description" in anom
            assert anom["severity"] in ["HIGH", "MEDIUM", "LOW"]
            assert len(anom["metrics"]) > 0

    def test_get_lag_analysis_api(self):
        """Assert GET /lag-analysis computes temporal shifts correctly."""
        response = self.client.get("/api/v1/correlation/lag-analysis?city=New York")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "relationships" in data

        for rel in data["relationships"]:
            assert "metric_a" in rel
            assert "metric_b" in rel
            assert "lag_minutes" in rel
            assert "correlation" in rel
            assert "description" in rel
            assert -60 <= rel["lag_minutes"] <= 60
            assert -1.0 <= rel["correlation"] <= 1.0



