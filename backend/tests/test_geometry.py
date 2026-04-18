from __future__ import annotations

import math

import numpy as np
import pytest

from backend.core.geometry import (
    RRect,
    corners_to_rrect,
    extract_template,
    is_inside_image,
    iou_rrect,
    normalize_angle,
    rrect_to_corners,
)


def test_normalize_angle():
    assert normalize_angle(0) == 0
    assert normalize_angle(180) in (-180.0, 180.0) or abs(normalize_angle(180)) <= 180
    assert abs(normalize_angle(370) - 10.0) < 1e-9
    assert abs(normalize_angle(-190) - 170.0) < 1e-9


def test_rrect_roundtrip_axis_aligned():
    rr = RRect(cx=100, cy=50, w=80, h=40, angle=0)
    corners = rrect_to_corners(rr)
    back = corners_to_rrect(corners)
    assert math.isclose(back.cx, rr.cx, abs_tol=1e-6)
    assert math.isclose(back.cy, rr.cy, abs_tol=1e-6)
    assert math.isclose(back.w, rr.w, abs_tol=1e-6)
    assert math.isclose(back.h, rr.h, abs_tol=1e-6)
    assert math.isclose(back.angle, rr.angle, abs_tol=1e-6)


@pytest.mark.parametrize("angle", [15.0, -30.0, 45.0, 90.0, 120.0, -170.0])
def test_rrect_roundtrip_rotated(angle):
    rr = RRect(cx=200, cy=150, w=60, h=30, angle=angle)
    corners = rrect_to_corners(rr)
    back = corners_to_rrect(corners)
    assert math.isclose(back.cx, rr.cx, abs_tol=1e-6)
    assert math.isclose(back.cy, rr.cy, abs_tol=1e-6)
    assert math.isclose(back.w, rr.w, abs_tol=1e-6)
    assert math.isclose(back.h, rr.h, abs_tol=1e-6)
    assert math.isclose(back.angle, normalize_angle(angle), abs_tol=1e-6)


def test_extract_template_axis_aligned():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[20:40, 30:70] = (10, 20, 30)
    corners = [(30.0, 20.0), (70.0, 20.0), (70.0, 40.0), (30.0, 40.0)]
    tmpl = extract_template(img, corners)
    assert tmpl.shape == (20, 40, 3)
    # output should be a 1:1 slice of the source region
    assert tuple(int(c) for c in tmpl[5, 5]) == (10, 20, 30)
    assert np.array_equal(tmpl, img[20:40, 30:70])


def test_is_inside_image():
    assert is_inside_image([(0, 0), (10, 0), (10, 10), (0, 10)], 100, 100)
    assert not is_inside_image([(0, 0), (150, 0), (150, 10), (0, 10)], 100, 100)


def test_iou_rrect_identical():
    a = RRect(cx=50, cy=50, w=20, h=20, angle=0)
    assert math.isclose(iou_rrect(a, a), 1.0, abs_tol=1e-3)


def test_iou_rrect_disjoint():
    a = RRect(cx=10, cy=10, w=10, h=10, angle=0)
    b = RRect(cx=100, cy=100, w=10, h=10, angle=0)
    assert iou_rrect(a, b) == 0.0
