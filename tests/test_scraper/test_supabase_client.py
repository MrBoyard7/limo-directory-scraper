"""
tests/test_scraper/test_supabase_client.py
-------------------------------------------
Tests for the Supabase client utility functions.
All tests mock the Supabase client — no real DB connection needed.
"""

from unittest.mock import MagicMock, patch


def _make_mock_client(return_data=None):
    """Return a fully mocked Supabase client."""
    return_data = return_data or [{"id": "abc-123", "name": "Test Co", "url": "https://test.com"}]

    mock_result = MagicMock()
    mock_result.data = return_data

    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.insert.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.upsert.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.not_.return_value = mock_query
    mock_query.is_.return_value = mock_query
    mock_query.in_.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = mock_result

    mock_client = MagicMock()
    mock_client.table.return_value = mock_query
    return mock_client


class TestUpsertCompany:
    def test_upsert_returns_row(self):
        from scraper.utils.supabase_client import upsert_company

        mock_client = _make_mock_client()
        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            result = upsert_company({"name": "Test Co", "url": "https://test.com"})
        assert result["id"] == "abc-123"

    def test_upsert_calls_table(self):
        from scraper.utils.supabase_client import upsert_company

        mock_client = _make_mock_client()
        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            upsert_company({"name": "Test Co", "url": "https://test.com"})
        mock_client.table.assert_called_with("companies")


class TestGetCompanyByUrl:
    def test_returns_company_when_found(self):
        from scraper.utils.supabase_client import get_company_by_url

        mock_client = _make_mock_client()
        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            result = get_company_by_url("https://test.com")
        assert result["id"] == "abc-123"

    def test_returns_none_when_not_found(self):
        from scraper.utils.supabase_client import get_company_by_url

        mock_result = MagicMock()
        mock_result.data = []
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_query
        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            result = get_company_by_url("https://notfound.com")
        assert result is None


class TestInsertVehicle:
    def test_insert_returns_row(self):
        from scraper.utils.supabase_client import insert_vehicle

        mock_client = _make_mock_client([{"id": "veh-001", "primary_color": "red"}])
        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            result = insert_vehicle({"company_id": "abc-123", "primary_color": "red"})
        assert result["id"] == "veh-001"


class TestUpsertVehicleImage:
    def test_upsert_image_returns_row(self):
        from scraper.utils.supabase_client import upsert_vehicle_image

        mock_client = _make_mock_client(
            [{"id": "img-001", "original_url": "https://img.com/car.jpg"}]
        )
        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            result = upsert_vehicle_image({"original_url": "https://img.com/car.jpg"})
        assert result["id"] == "img-001"


class TestTagCompanyEvents:
    def test_tag_calls_upsert(self):
        from scraper.utils.supabase_client import tag_company_events

        mock_result = MagicMock()
        mock_result.data = [{"id": 1, "slug": "wedding"}]
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.in_.return_value = mock_query
        mock_query.upsert.return_value = mock_query
        mock_query.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_query

        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            tag_company_events("abc-123", ["wedding"], source="keyword")

    def test_tag_skips_empty_slugs(self):
        from scraper.utils.supabase_client import tag_company_events

        mock_client = _make_mock_client()
        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            tag_company_events("abc-123", [], source="keyword")
        mock_client.table.assert_not_called()


class TestScrapeLogs:
    def test_start_scrape_log_returns_id(self):
        from scraper.utils.supabase_client import start_scrape_log

        mock_client = _make_mock_client([{"id": 42}])
        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            log_id = start_scrape_log("test_spider", state="TX")
        assert log_id == 42

    def test_finish_scrape_log_calls_update(self):
        from scraper.utils.supabase_client import finish_scrape_log

        mock_client = _make_mock_client()
        with patch("scraper.utils.supabase_client.get_client", return_value=mock_client):
            finish_scrape_log(1, status="done", companies_found=10, companies_new=5)
        mock_client.table.assert_called_with("scrape_logs")


class TestGetClient:
    def test_get_client_returns_singleton(self):
        from scraper.utils import supabase_client

        supabase_client._client = None

        mock_client = MagicMock()
        with patch("scraper.utils.supabase_client.create_client", return_value=mock_client):
            with patch("scraper.utils.supabase_client.settings") as mock_settings:
                mock_settings.SUPABASE_URL = "https://test.supabase.co"
                mock_settings.SUPABASE_KEY = "test-key"
                client1 = supabase_client.get_client()
                client2 = supabase_client.get_client()

        assert client1 is client2
        supabase_client._client = None  # reset after test
