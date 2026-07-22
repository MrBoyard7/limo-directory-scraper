"""
tests/test_api/test_directories_endpoint.py
--------------------------------------------
Tests for GET /directories and GET /directories/{slug}.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

MOCK_DIRECTORY = {
    "slug": "red-limos",
    "title": "Red Limousines in the USA",
    "description": "Browse every red limousine company.",
    "meta_title": "Red Limos | Directory",
    "meta_description": "Find red limos near you.",
    "filter_config": {"vehicle_color": "red", "vehicle_type_slugs": ["stretch_limo"]},
    "is_active": True,
}

MOCK_COMPANY = {
    "id": "abc-123",
    "name": "Red Star Limo",
    "city": "Houston",
    "state": "TX",
    "rating": 4.5,
    "vehicle_colors": ["red"],
    "vehicle_type_slugs": ["stretch_limo"],
    "event_type_slugs": ["prom", "wedding"],
}


def _mock_db(directory_data=None, company_data=None):
    mock_dir_result = MagicMock()
    mock_dir_result.data = directory_data if directory_data is not None else [MOCK_DIRECTORY]

    mock_company_result = MagicMock()
    mock_company_result.data = company_data if company_data is not None else [MOCK_COMPANY]

    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.overlaps.return_value = mock_query
    mock_query.contains.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.range.return_value = mock_query

    call_count = [0]

    def execute_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_dir_result
        return mock_company_result

    mock_query.execute.side_effect = execute_side_effect

    mock_client = MagicMock()
    mock_client.table.return_value = mock_query
    return mock_client


class TestListDirectories:
    def test_returns_200(self):
        mock_result = MagicMock()
        mock_result.data = [MOCK_DIRECTORY]
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_query

        with patch("api.routers.directories.get_client", return_value=mock_client):
            resp = client.get("/directories")
        assert resp.status_code == 200

    def test_returns_list(self):
        mock_result = MagicMock()
        mock_result.data = [MOCK_DIRECTORY]
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_query

        with patch("api.routers.directories.get_client", return_value=mock_client):
            resp = client.get("/directories")
        assert isinstance(resp.json(), list)


class TestGetDirectory:
    def test_returns_404_for_unknown_slug(self):
        with patch("api.routers.directories.get_client", return_value=_mock_db(directory_data=[])):
            resp = client.get("/directories/nonexistent-slug")
        assert resp.status_code == 404

    def test_returns_200_for_valid_slug(self):
        with patch("api.routers.directories.get_client", return_value=_mock_db()):
            resp = client.get("/directories/red-limos")
        assert resp.status_code == 200

    def test_response_contains_directory_info(self):
        with patch("api.routers.directories.get_client", return_value=_mock_db()):
            resp = client.get("/directories/red-limos")
        body = resp.json()
        assert "directory" in body
        assert body["directory"]["slug"] == "red-limos"

    def test_response_contains_companies(self):
        with patch("api.routers.directories.get_client", return_value=_mock_db()):
            resp = client.get("/directories/red-limos")
        body = resp.json()
        assert "companies" in body

    def test_state_filter_accepted(self):
        with patch("api.routers.directories.get_client", return_value=_mock_db()):
            resp = client.get("/directories/red-limos?state=TX")
        assert resp.status_code == 200

    def test_pagination_params(self):
        with patch("api.routers.directories.get_client", return_value=_mock_db()):
            resp = client.get("/directories/red-limos?page=2&limit=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 2
        assert body["limit"] == 10
