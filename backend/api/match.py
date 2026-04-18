from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException

from ..core import algorithms as algo_pkg
from ..core.algorithms import get as get_algo
from ..core.algorithms import list_all as list_algos
from ..core.algorithms.base import PatternSpec
from ..core.algorithms.registry import AlgorithmNotFoundError
from ..core.geometry import is_inside_image
from ..core.image_io import (
    ImageDecodeError,
    ImageTooLargeError,
    decode_base64,
)
from ..schemas import (
    AlgorithmInfoOut,
    AlgorithmListResponse,
    MatchItem,
    MatchRequest,
    MatchResponse,
)

# ensure matchers are registered
_ = algo_pkg

router = APIRouter(prefix="/api", tags=["match"])
logger = logging.getLogger("pattern_matching.match")


@router.get("/algorithms", response_model=AlgorithmListResponse)
def list_algorithms() -> AlgorithmListResponse:
    items = [
        AlgorithmInfoOut(
            id=m.info().id,
            name=m.info().name,
            supports_rotation=m.info().supports_rotation,
            default_params=m.info().default_params,
        )
        for m in list_algos()
    ]
    return AlgorithmListResponse(algorithms=items)


@router.post("/match", response_model=MatchResponse)
def run_match(req: MatchRequest) -> MatchResponse:
    try:
        image = decode_base64(req.image.data_base64)
    except ImageTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ImageDecodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ih, iw = image.shape[:2]
    corners = req.template.as_tuples()
    if not is_inside_image(corners, iw, ih):
        raise HTTPException(status_code=400, detail="template corners out of image bounds")

    try:
        pattern = PatternSpec(corners=corners, shape=req.template.shape)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        matcher = get_algo(req.algorithm)
    except AlgorithmNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"unknown algorithm: {req.algorithm}") from exc

    t0 = time.perf_counter()
    try:
        results = matcher.match(image, pattern, req.params)
    except NotImplementedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    logger.info(
        "match algo=%s filename=%s matches=%d elapsed_ms=%d",
        req.algorithm, req.image.filename, len(results), elapsed_ms,
    )

    return MatchResponse(
        algorithm=req.algorithm,
        elapsed_ms=elapsed_ms,
        matches=[
            MatchItem(
                corners=[list(pt) for pt in r.corners],
                cx=r.cx, cy=r.cy, w=r.w, h=r.h, angle=r.angle, score=r.score,
            )
            for r in results
        ],
    )
