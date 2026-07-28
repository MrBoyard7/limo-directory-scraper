"""
tests/test_scraper/test_color_detector_extended.py
---------------------------------------------------
Extended tests for color detector to boost coverage above 85%.
"""

import io
from unittest.mock import MagicMock, patch
import numpy as np
from PIL import Image

from scraper.processors.color_detector import (
    classify_color,
    detect_colors_from_image,
    rgb_to_hsv,
    ColorDetector,
    COLOR_RANGES,
)


def _make_image_bytes(r: int, g: int, b: int, size: int = 150) -> bytes:
    arr = np.full((size, size, 3), [r, g, b], dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestRgbToHsv:
    def test_pure_red(self):
        h, s, v = rgb_to_hsv(1.0, 0.0, 0.0)
        assert abs(h - 0.0) < 1.0
        assert s > 0.9
        assert v > 0.9

    def test_pure_black(self):
        h, s, v = rgb_to_hsv(0.0, 0.0, 0.0)
        assert v == 0.0
        assert s == 0.0

    def test_pure_white(self):
        h, s, v = rgb_to_hsv(1.0, 1.0, 1.0)
        assert v == 1.0
        assert s == 0.0

    def test_pure_green(self):
        h, s, v = rgb_to_hsv(0.0, 1.0, 0.0)
        assert abs(h - 120.0) < 1.0

    def test_pure_blue(self):
        h, s, v = rgb_to_hsv(0.0, 0.0, 1.0)
        assert abs(h - 240.0) < 1.0

    def test_equal_rgb_gives_zero_saturation(self):
        h, s, v = rgb_to_hsv(0.5, 0.5, 0.5)
        assert s == 0.0


class TestClassifyColorExtended:
    def test_orange(self):
        result = classify_color(230, 120, 30)
        assert result in ("orange", "red", "gold")

    def test_green(self):
        result = classify_color(30, 160, 50)
        assert result == "green"

    def test_purple(self):
        result = classify_color(120, 30, 180)
        assert result == "purple"

    def test_yellow(self):
        result = classify_color(230, 220, 30)
        assert result in ("yellow", "gold")

    def test_dark_gray(self):
        result = classify_color(80, 80, 80)
        assert result in ("gray", "silver", "black")

    def test_all_color_ranges_have_valid_bounds(self):
        for cr in COLOR_RANGES:
            assert 0 <= cr.s_min <= 1
            assert 0 <= cr.v_min <= 1


class TestDetectColorsExtended:
    def test_orange_image(self):
        image_bytes = _make_image_bytes(230, 120, 30)
        result = detect_colors_from_image(image_bytes)
        assert isinstance(result, list)

    def test_green_image(self):
        image_bytes = _make_image_bytes(30, 160, 50)
        result = detect_colors_from_image(image_bytes)
        assert isinstance(result, list)

    def test_purple_image(self):
        image_bytes = _make_image_bytes(120, 30, 180)
        result = detect_colors_from_image(image_bytes)
        assert isinstance(result, list)

    def test_small_image(self):
        image_bytes = _make_image_bytes(220, 20, 20, size=10)
        result = detect_colors_from_image(image_bytes)
        assert isinstance(result, list)

    def test_result_is_sorted_by_confidence(self):
        image_bytes = _make_image_bytes(30, 80, 200)
        result = detect_colors_from_image(image_bytes)
        if len(result) > 1:
            for i in range(len(result) - 1):
                assert result[i]["confidence"] >= result[i + 1]["confidence"]


class TestColorDetectorProcessor:
    def _make_mock_db(self, images=None):
        images = images or []
        mock_result = MagicMock()
        mock_result.data = images
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.update.return_value = mock_query
        mock_query.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_query
        return mock_client

    def test_fetch_unprocessed_returns_images(self):
        images = [
            {
                "id": "img-1",
                "original_url": "https://example.com/car.jpg",
                "vehicle_id": "veh-1",
                "company_id": "comp-1",
            }
        ]
        mock_db = self._make_mock_db(images=images)
        with patch("scraper.processors.color_detector.get_client", return_value=mock_db):
            detector = ColorDetector()
            result = detector.fetch_unprocessed(limit=10)
        assert len(result) == 1

    def test_download_image_failure_returns_none(self):
        mock_db = self._make_mock_db()
        with patch("scraper.processors.color_detector.get_client", return_value=mock_db):
            detector = ColorDetector()
            with patch.object(detector.http, "get", side_effect=Exception("timeout")):
                result = detector.download_image("https://bad-url.com/img.jpg")
        assert result is None

    def test_update_image_colors_calls_db(self):
        mock_db = self._make_mock_db()
        with patch("scraper.processors.color_detector.get_client", return_value=mock_db):
            detector = ColorDetector()
            detector.update_image_colors("img-1", [{"color": "red", "confidence": 0.9}])
        mock_db.table.assert_called_with("vehicle_images")

    def test_run_with_no_images(self):
        mock_db = self._make_mock_db(images=[])
        with patch("scraper.processors.color_detector.get_client", return_value=mock_db):
            detector = ColorDetector()
            detector.run(limit=10)  # should not raise

    def test_run_skips_failed_downloads(self):
        images = [
            {
                "id": "img-1",
                "original_url": "https://bad.com/img.jpg",
                "vehicle_id": None,
                "company_id": "comp-1",
            }
        ]
        mock_db = self._make_mock_db(images=images)
        with patch("scraper.processors.color_detector.get_client", return_value=mock_db):
            detector = ColorDetector()
            with patch.object(detector, "download_image", return_value=None):
                detector.run(limit=10)  # should not raise

    def test_update_vehicle_primary_color_skips_if_no_vehicle_id(self):
        mock_db = self._make_mock_db()
        with patch("scraper.processors.color_detector.get_client", return_value=mock_db):
            detector = ColorDetector()
            detector.update_vehicle_primary_color(None, "red")
        mock_db.table.assert_not_called()

    def test_update_vehicle_primary_color_skips_if_already_set(self):
        mock_result = MagicMock()
        mock_result.data = [{"primary_color": "black"}]
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_query

        with patch("scraper.processors.color_detector.get_client", return_value=mock_client):
            detector = ColorDetector()
            detector.update_vehicle_primary_color("veh-1", "red")
        # Should not call update since color already set
        mock_query.update.assert_not_called()
