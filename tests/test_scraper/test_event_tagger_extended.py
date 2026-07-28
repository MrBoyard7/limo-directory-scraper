"""
tests/test_scraper/test_event_tagger_extended.py
-------------------------------------------------
Extended tests for event_tagger to boost coverage.
"""

from unittest.mock import MagicMock, patch
from scraper.processors.event_tagger import tag_company, EventTagger


class TestEventTaggerProcessor:
    def _make_mock_db(self, companies=None, tagged_ids=None):
        companies = companies or []
        tagged_ids = tagged_ids or []

        mock_tagged_result = MagicMock()
        mock_tagged_result.data = [{"company_id": cid} for cid in tagged_ids]

        mock_companies_result = MagicMock()
        mock_companies_result.data = companies

        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.side_effect = [mock_tagged_result, mock_companies_result]

        mock_client = MagicMock()
        mock_client.table.return_value = mock_query
        return mock_client

    def test_fetch_untagged_excludes_already_tagged(self):
        companies = [
            {"id": "aaa", "name": "Wedding Limo", "description": "Wedding services."},
            {"id": "bbb", "name": "Prom Limo", "description": "Prom night."},
        ]
        mock_db = self._make_mock_db(companies=companies, tagged_ids=["aaa"])

        with patch("scraper.processors.event_tagger.get_client", return_value=mock_db):
            tagger = EventTagger()
            untagged = tagger.fetch_untagged(limit=10)

        assert all(c["id"] != "aaa" for c in untagged)

    def test_run_tags_companies(self):
        companies = [
            {"id": "ccc", "name": "Wedding Limo", "description": "Perfect for weddings."},
        ]
        mock_db = self._make_mock_db(companies=companies, tagged_ids=[])

        with patch("scraper.processors.event_tagger.get_client", return_value=mock_db):
            with patch("scraper.processors.event_tagger.tag_company_events") as mock_tag:
                tagger = EventTagger()
                tagger.run(limit=10)
                mock_tag.assert_called_once()

    def test_run_skips_unmatched_companies(self):
        companies = [
            {"id": "ddd", "name": "Generic Transport", "description": "We drive."},
        ]
        mock_db = self._make_mock_db(companies=companies, tagged_ids=[])

        with patch("scraper.processors.event_tagger.get_client", return_value=mock_db):
            with patch("scraper.processors.event_tagger.tag_company_events") as mock_tag:
                tagger = EventTagger()
                tagger.run(limit=10)
                mock_tag.assert_not_called()

    def test_run_with_empty_company_list(self):
        mock_db = self._make_mock_db(companies=[], tagged_ids=[])
        with patch("scraper.processors.event_tagger.get_client", return_value=mock_db):
            tagger = EventTagger()
            tagger.run(limit=10)  # should not raise

    def test_brewery_tour_detected(self):
        company = {"name": "Hop Limo", "description": "Brewery tour and pub crawl specialists."}
        tags = tag_company(company)
        assert "brewery_tour" in tags

    def test_funeral_detected(self):
        company = {
            "name": "Grace Limo",
            "description": "Funeral and memorial service transportation.",
        }
        tags = tag_company(company)
        assert "funeral" in tags

    def test_sightseeing_detected(self):
        company = {"name": "City Tours", "description": "Sightseeing and city tour services."}
        tags = tag_company(company)
        assert "sightseeing" in tags

    def test_returns_list_type(self):
        company = {"name": "Limo Co", "description": "Luxury rides."}
        result = tag_company(company)
        assert isinstance(result, list)

    def test_empty_strings_handled(self):
        company = {"name": "", "description": ""}
        result = tag_company(company)
        assert isinstance(result, list)
