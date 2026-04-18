from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from backend.core.algorithms import CCoeffNormedMatcher
from backend.core.algorithms.base import PatternSpec

TEST_IMAGE = Path(__file__).resolve().parents[2] / "test_image" / "image_01.png"


@pytest.fixture(scope="module")
def image() -> np.ndarray:
    # deterministic synthetic canvas with a few distinctive shapes
    img = np.full((300, 400, 3), 240, dtype=np.uint8)
    cv2.rectangle(img, (50, 60), (120, 120), (20, 150, 200), -1)
    cv2.circle(img, (250, 180), 30, (40, 50, 220), -1)
    cv2.rectangle(img, (300, 40), (370, 100), (80, 200, 80), -1)
    cv2.putText(img, "AB", (200, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (10, 10, 10), 2)
    return img


@pytest.fixture(scope="module")
def real_image() -> np.ndarray:
    if not TEST_IMAGE.exists():
        pytest.skip(f"{TEST_IMAGE} missing")
    img = cv2.imread(str(TEST_IMAGE), cv2.IMREAD_COLOR)
    assert img is not None
    return img


def _corners_from_rect(x: int, y: int, w: int, h: int) -> list[tuple[float, float]]:
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def test_find_self_in_synthetic_image(image):
    # pick the "AB" text region — unique in the canvas
    tw, th = 70, 40
    x0, y0 = 195, 65
    corners = _corners_from_rect(x0, y0, tw, th)
    pattern = PatternSpec(corners=corners, shape="rect")

    matcher = CCoeffNormedMatcher()
    results = matcher.match(image, pattern, {"threshold": 0.9, "max_results": 5, "nms_iou": 0.3})
    assert results, "expected at least one match"
    top = max(results, key=lambda r: r.score)
    assert top.score > 0.99
    assert abs(top.cx - (x0 + tw / 2)) < 2
    assert abs(top.cy - (y0 + th / 2)) < 2


def test_real_image_loads_and_matches(real_image):
    """Ensure the pipeline runs on the provided test_image (loose assertion)."""
    h, w = real_image.shape[:2]
    x0, y0, tw, th = 10, 10, 100, 80
    corners = _corners_from_rect(x0, y0, tw, th)
    pattern = PatternSpec(corners=corners, shape="rect")
    matcher = CCoeffNormedMatcher()
    results = matcher.match(real_image, pattern, {"threshold": 0.9, "max_results": 10})
    assert results  # template is a patch from the image itself


def test_multi_angle_not_implemented(image):
    corners = _corners_from_rect(10, 10, 30, 30)
    pattern = PatternSpec(corners=corners, shape="rect")
    matcher = CCoeffNormedMatcher()
    with pytest.raises(NotImplementedError):
        matcher.match(image, pattern, {"multi_angle": True})


def test_threshold_filters_out_all(image):
    h, w = image.shape[:2]
    corners = _corners_from_rect(0, 0, 20, 20)
    pattern = PatternSpec(corners=corners, shape="rect")
    matcher = CCoeffNormedMatcher()
    results = matcher.match(image, pattern, {"threshold": 1.01})
    assert results == []
