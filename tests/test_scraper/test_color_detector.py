"""
tests/test_scraper/test_color_detector.py
------------------------------------------
Unit tests for the vehicle color detection logic.
No network calls — tests use synthetic pixel data.
"""

import io
from PIL import Image
import numpy as np

from scraper.processors.color_detector import classify_color, detect_colors_from_image


def _make_image_bytes(r: int, g: int, b: int, size: int = 150) -> bytes:
    """Create a solid-color PNG in memory."""
    arr = np.full((size, size, 3), [r, g, b], dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestClassifyColor:
    def test_pure_red(self):
        assert classify_color(220, 30, 30) == "red"

    def test_pure_black(self):
        assert classify_color(10, 10, 10) == "black"

    def test_pure_white(self):
        assert classify_color(250, 250, 250) == "white"

    def test_silver_gray(self):
        result = classify_color(180, 180, 180)
        assert result in ("silver", "gray")

    def test_pure_blue(self):
        assert classify_color(30, 80, 200) == "blue"

    def test_pink(self):
        assert classify_color(220, 80, 160) == "pink"

    def test_gold_champagne(self):
        # Champagne / gold range
        result = classify_color(210, 190, 140)
        assert result in ("gold", "champagne", "silver", "yellow", "other")  # acceptable set


class TestDetectColorsFromImage:
    def test_solid_red_image(self):
        image_bytes = _make_image_bytes(220, 20, 20)
        result = detect_colors_from_image(image_bytes)
        assert len(result) > 0
        assert result[0]["color"] == "red"
        assert result[0]["confidence"] > 0.5

    def test_solid_black_image(self):
        image_bytes = _make_image_bytes(15, 15, 15)
        result = detect_colors_from_image(image_bytes)
        assert any(c["color"] == "black" for c in result)

    def test_solid_white_image(self):
        image_bytes = _make_image_bytes(252, 252, 252)
        # White pixels are filtered as background; result may be empty
        result = detect_colors_from_image(image_bytes)
        # Just ensure it doesn't crash and returns a list
        assert isinstance(result, list)

    def test_invalid_bytes(self):
        result = detect_colors_from_image(b"not an image")
        assert result == []

    def test_confidence_between_0_and_1(self):
        image_bytes = _make_image_bytes(30, 80, 200)  # blue
        result = detect_colors_from_image(image_bytes)
        for item in result:
            assert 0.0 <= item["confidence"] <= 1.0
