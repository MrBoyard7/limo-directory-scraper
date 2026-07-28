"""
tests/test_api/test_vehicles_endpoint.py
-----------------------------------------
Tests for GET /vehicles and the API root endpoints.
"""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

MOCK_VEHICLE = {
    "id": "veh-001",
    "name": "Red Hummer Limo",
    "description": "16-passenger red Hummer limousine.",
    "capacity": 16,
    "primary_color": "red",
    "secondary_color": None,
    "amenities": ["bar", "LED lights", "TV"],
    "price_per_hour": 150.00,
    "price_per_day": None,
    "vehicle_types": {"slug": "hummer_limo", "label": "Hummer Limousine"},
    "companies": {
        "id": "comp-001",
        "name": "Star Limo",
        "city": "Dallas",
        "state": "TX",
        "phone": "+1-214-555-0100",
        "url": "https://starlimo.example.com",
        "rating": 4.7,
    },
}


def _mock_vehicles_db(data=None):
    mock_result = MagicMock()
    mock_result.data = data if data is not None else [MOCK_VEHICLE]

    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = mock_result

    mock_client = MagicMock()
    mock_client.table.return_value = mock_query
    return mock_client


class TestListVehicles:
    def test_returns_200(self):
        with patch("api.routers.vehicles.get_client", return_value=_mock_vehicles_db()):
            resp = client.get("/vehicles")
        assert resp.status_code == 200

    def test_returns_data_list(self):
        with patch("api.routers.vehicles.get_client", return_value=_mock_vehicles_db()):
            resp = client.get("/vehicles")
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    def test_color_filter(self):
        with patch("api.routers.vehicles.get_client", return_value=_mock_vehicles_db()):
            resp = client.get("/vehicles?color=red")
        assert resp.status_code == 200

    def test_capacity_filter(self):
        with patch("api.routers.vehicles.get_client", return_value=_mock_vehicles_db()):
            resp = client.get("/vehicles?min_capacity=10&max_capacity=20")
        assert resp.status_code == 200

    def test_type_filter(self):
        with patch("api.routers.vehicles.get_client", return_value=_mock_vehicles_db()):
            resp = client.get("/vehicles?type_slug=hummer_limo")
        assert resp.status_code == 200

    def test_state_filter(self):
        with patch("api.routers.vehicles.get_client", return_value=_mock_vehicles_db()):
            resp = client.get("/vehicles?state=TX")
        assert resp.status_code == 200

    def test_pagination(self):
        with patch("api.routers.vehicles.get_client", return_value=_mock_vehicles_db()):
            resp = client.get("/vehicles?page=1&limit=10")
        body = resp.json()
        assert body["page"] == 1
        assert body["limit"] == 10

    def test_limit_too_large_rejected(self):
        resp = client.get("/vehicles?limit=999")
        assert resp.status_code == 422

    def test_empty_results(self):
        with patch("api.routers.vehicles.get_client", return_value=_mock_vehicles_db(data=[])):
            resp = client.get("/vehicles")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestAPIRoot:
    def test_root_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_returns_ok_status(self):
        resp = client.get("/")
        assert resp.json()["status"] == "ok"

    def test_docs_available(self):
        resp = client.get("/docs")
        assert resp.status_code == 200
