from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app

TEST_IMAGE = Path(__file__).resolve().parents[2] / "test_image" / "image_01.png"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def image_b64() -> str:
    if not TEST_IMAGE.exists():
        pytest.skip("test image missing")
    return base64.b64encode(TEST_IMAGE.read_bytes()).decode("ascii")


def test_healthz(client):
    r = client.get("/api/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_list_algorithms(client):
    r = client.get("/api/algorithms")
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()["algorithms"]]
    assert "ccoeff_normed" in ids


def test_match_happy_path(client, image_b64):
    import cv2
    img = cv2.imread(str(TEST_IMAGE), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    tw, th = min(60, w // 4), min(40, h // 4)
    x0, y0 = w // 2 - tw // 2, h // 2 - th // 2
    corners = [[x0, y0], [x0 + tw - 1, y0], [x0 + tw - 1, y0 + th - 1], [x0, y0 + th - 1]]
    payload = {
        "image": {"filename": "image_01.png", "data_base64": image_b64},
        "template": {"shape": "rect", "corners": corners},
        "algorithm": "ccoeff_normed",
        "params": {"threshold": 0.95, "max_results": 3, "nms_iou": 0.3},
    }
    r = client.post("/api/match", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["algorithm"] == "ccoeff_normed"
    assert body["elapsed_ms"] >= 0
    assert len(body["matches"]) >= 1
    top = max(body["matches"], key=lambda m: m["score"])
    assert top["score"] > 0.99


def test_match_bad_base64(client):
    payload = {
        "image": {"filename": "x.png", "data_base64": "!!!!not-base64!!!"},
        "template": {"shape": "rect", "corners": [[0, 0], [1, 0], [1, 1], [0, 1]]},
    }
    r = client.post("/api/match", json=payload)
    assert r.status_code == 400


def test_match_unknown_algo(client, image_b64):
    payload = {
        "image": {"filename": "image_01.png", "data_base64": image_b64},
        "template": {"shape": "rect", "corners": [[0, 0], [10, 0], [10, 10], [0, 10]]},
        "algorithm": "does_not_exist",
    }
    r = client.post("/api/match", json=payload)
    assert r.status_code == 400


def test_match_template_out_of_bounds(client, image_b64):
    payload = {
        "image": {"filename": "image_01.png", "data_base64": image_b64},
        "template": {
            "shape": "rect",
            "corners": [[-10, -10], [10000, -10], [10000, 10000], [-10, 10000]],
        },
    }
    r = client.post("/api/match", json=payload)
    assert r.status_code == 400
