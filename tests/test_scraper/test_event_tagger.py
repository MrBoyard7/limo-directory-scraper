"""
tests/test_scraper/test_event_tagger.py
----------------------------------------
Tests for the event tagging processor.
"""

import pytest
from scraper.processors.event_tagger import tag_company, EVENT_KEYWORD_MAP


class TestTagCompany:
    def test_wedding_detected_from_description(self):
        company = {"name": "Star Limo", "description": "Perfect for weddings and receptions."}
        tags = tag_company(company)
        assert "wedding" in tags

    def test_prom_detected_from_name(self):
        company = {"name": "Prom Night Limos", "description": "Luxury rides."}
        tags = tag_company(company)
        assert "prom" in tags

    def test_bachelorette_detected(self):
        company = {"name": "Party Bus Co", "description": "Best bachelorette party buses in town."}
        tags = tag_company(company)
        assert "bachelorette" in tags

    def test_bachelor_detected(self):
        company = {"name": "Bros Limo", "description": "Bachelor party transportation specialists."}
        tags = tag_company(company)
        assert "bachelor" in tags

    def test_corporate_detected(self):
        company = {"name": "Executive Transport", "description": "Corporate events and business travel."}
        tags = tag_company(company)
        assert "corporate" in tags

    def test_airport_detected(self):
        company = {"name": "Airport Limo", "description": "Airport pickup and drop-off services."}
        tags = tag_company(company)
        assert "airport" in tags

    def test_birthday_detected(self):
        company = {"name": "Party Rides", "description": "Sweet 16 and birthday party buses."}
        tags = tag_company(company)
        assert "birthday" in tags

    def test_wine_tour_detected(self):
        company = {"name": "Napa Limo", "description": "Wine tour and vineyard transportation."}
        tags = tag_company(company)
        assert "wine_tour" in tags

    def test_concert_detected(self):
        company = {"name": "Stadium Limo", "description": "Concert and sports event rides."}
        tags = tag_company(company)
        assert "concert" in tags

    def test_quinceanera_detected(self):
        company = {"name": "Fiesta Limo", "description": "Quinceañera and sweet 15 services."}
        tags = tag_company(company)
        assert "quinceañera" in tags

    def test_no_tags_for_generic_company(self):
        company = {"name": "Generic Transport", "description": "We drive people around."}
        tags = tag_company(company)
        assert isinstance(tags, list)

    def test_multiple_tags_detected(self):
        company = {
            "name": "All Events Limo",
            "description": "Wedding, prom, and airport transportation.",
        }
        tags = tag_company(company)
        assert "wedding" in tags
        assert "prom" in tags
        assert "airport" in tags

    def test_none_description_handled(self):
        company = {"name": "Limo Co", "description": None}
        tags = tag_company(company)
        assert isinstance(tags, list)

    def test_none_name_handled(self):
        company = {"name": None, "description": "Wedding limos available."}
        tags = tag_company(company)
        assert "wedding" in tags

    def test_case_insensitive(self):
        company = {"name": "WEDDING LIMO", "description": "PERFECT FOR PROM NIGHT."}
        tags = tag_company(company)
        assert "wedding" in tags
        assert "prom" in tags

    def test_all_event_types_have_keywords(self):
        for event_slug, keywords in EVENT_KEYWORD_MAP.items():
            assert len(keywords) > 0, f"{event_slug} has no keywords"
            for kw in keywords:
                assert isinstance(kw, str)
                assert len(kw) > 0
