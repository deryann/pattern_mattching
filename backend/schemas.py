from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ImagePayload(BaseModel):
    filename: str = Field(..., min_length=1, max_length=512)
    data_base64: str = Field(..., min_length=1)


class TemplatePayload(BaseModel):
    shape: Literal["rect", "rrect"]
    corners: list[list[float]] = Field(..., min_length=4, max_length=4)

    @field_validator("corners")
    @classmethod
    def _check_points(cls, v: list[list[float]]) -> list[list[float]]:
        for pt in v:
            if len(pt) != 2:
                raise ValueError("each corner must be [x, y]")
        return v

    def as_tuples(self) -> list[tuple[float, float]]:
        return [(float(x), float(y)) for x, y in self.corners]


class MatchRequest(BaseModel):
    image: ImagePayload
    template: TemplatePayload
    algorithm: str = "ccoeff_normed"
    params: dict[str, Any] = Field(default_factory=dict)


class MatchItem(BaseModel):
    corners: list[list[float]]
    cx: float
    cy: float
    w: float
    h: float
    angle: float
    score: float


class MatchResponse(BaseModel):
    algorithm: str
    elapsed_ms: int
    matches: list[MatchItem]


class AlgorithmInfoOut(BaseModel):
    id: str
    name: str
    supports_rotation: bool
    default_params: dict[str, Any]


class AlgorithmListResponse(BaseModel):
    algorithms: list[AlgorithmInfoOut]


class HealthResponse(BaseModel):
    status: str
    version: str
