from __future__ import annotations

import cv2
import numpy as np
import pytest

from backend.core.algorithms import CCoeffEdgeMatcher
from backend.core.algorithms.base import PatternSpec


def _corners(x: int, y: int, w: int, h: int) -> list[tuple[float, float]]:
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


@pytest.fixture(scope="module")
def image() -> np.ndarray:
    """Canvas with two identical rectangles but different text inside — mimics
    parking slots numbered differently."""
    img = np.full((240, 400, 3), 255, dtype=np.uint8)
    for i, (x, text) in enumerate([(40, "215"), (180, "216"), (280, "217")]):
        cv2.rectangle(img, (x, 80), (x + 80, 150), (0, 0, 0), 2)
        cv2.putText(img, text, (x + 10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    return img


def test_edge_matcher_finds_all_three(image):
    # template is the first box (x=40..120), Canny should erase the "215" differences
    pattern = PatternSpec(corners=_corners(38, 78, 84, 74), shape="rect")
    matcher = CCoeffEdgeMatcher()
    results = matcher.match(image, pattern, {"threshold": 0.5, "max_results": 10, "nms_iou": 0.3})
    assert len(results) >= 3, f"expected >=3 matches, got {len(results)}"
    xs = sorted(int(r.cx) for r in results[:3])
    # centers should land near 80, 220, 320 (within a few px)
    for expected, actual in zip((80, 220, 320), xs):
        assert abs(actual - expected) <= 6, f"match center off: {actual} vs {expected}"


def test_edge_matcher_default_threshold(image):
    """Default threshold for edge matcher should already surface all 3 slots."""
    pattern = PatternSpec(corners=_corners(38, 78, 84, 74), shape="rect")
    matcher = CCoeffEdgeMatcher()
    results = matcher.match(image, pattern, {})
    assert len(results) >= 3


def test_edge_matcher_info():
    m = CCoeffEdgeMatcher()
    info = m.info()
    assert info.id == "ccoeff_edge"
    assert "canny_low" in info.default_params
    assert "canny_high" in info.default_params
