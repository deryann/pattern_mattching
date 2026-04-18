from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..geometry import Corners, RRect, corners_to_rrect, rrect_to_corners


@dataclass(frozen=True)
class PatternSpec:
    corners: Corners
    shape: str  # 'rect' | 'rrect'

    def __post_init__(self) -> None:
        if self.shape not in ("rect", "rrect"):
            raise ValueError(f"unsupported shape: {self.shape}")
        if len(self.corners) != 4:
            raise ValueError("corners must have exactly 4 points")

    @property
    def rrect(self) -> RRect:
        return corners_to_rrect(self.corners)

    @property
    def cx(self) -> float: return self.rrect.cx
    @property
    def cy(self) -> float: return self.rrect.cy
    @property
    def w(self) -> float: return self.rrect.w
    @property
    def h(self) -> float: return self.rrect.h
    @property
    def angle(self) -> float: return self.rrect.angle


@dataclass(frozen=True)
class MatchResult:
    corners: Corners
    cx: float
    cy: float
    w: float
    h: float
    angle: float
    score: float

    @classmethod
    def from_rrect(cls, rr: RRect, score: float) -> "MatchResult":
        return cls(
            corners=rrect_to_corners(rr),
            cx=rr.cx, cy=rr.cy, w=rr.w, h=rr.h, angle=rr.angle,
            score=score,
        )


@dataclass(frozen=True)
class AlgorithmInfo:
    id: str
    name: str
    supports_rotation: bool
    default_params: dict[str, Any] = field(default_factory=dict)


class AbstractMatcher(ABC):
    id: str = "abstract"
    name: str = "Abstract Matcher"
    supports_rotation: bool = False
    default_params: dict[str, Any] = {}

    def info(self) -> AlgorithmInfo:
        return AlgorithmInfo(
            id=self.id,
            name=self.name,
            supports_rotation=self.supports_rotation,
            default_params=dict(self.default_params),
        )

    @abstractmethod
    def match(
        self,
        image: np.ndarray,
        pattern: PatternSpec,
        params: dict[str, Any],
    ) -> list[MatchResult]:
        ...
