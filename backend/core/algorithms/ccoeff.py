from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from ..geometry import RRect, extract_template, iou_rrect
from .base import AbstractMatcher, MatchResult, PatternSpec


class CCoeffNormedMatcher(AbstractMatcher):
    id = "ccoeff_normed"
    name = "OpenCV CCOEFF Normed"
    supports_rotation = False
    default_params = {
        "threshold": 0.85,
        "max_results": 50,
        "nms_iou": 0.3,
        "multi_scale": False,
        "scales": [1.0],
        "multi_angle": False,
        "angle_range": [-15, 15],
        "angle_step": 5,
    }

    def _preprocess(self, gray: np.ndarray, params: dict[str, Any]) -> np.ndarray:
        """Hook for subclasses to apply edge/gradient preprocessing."""
        return gray

    def match(
        self,
        image: np.ndarray,
        pattern: PatternSpec,
        params: dict[str, Any],
    ) -> list[MatchResult]:
        merged = {**self.default_params, **(params or {})}
        if merged.get("multi_scale") or merged.get("multi_angle"):
            raise NotImplementedError(
                "multi_scale / multi_angle are not supported in v0.1"
            )

        threshold = float(merged["threshold"])
        max_results = int(merged["max_results"])
        nms_iou = float(merged["nms_iou"])

        template = extract_template(image, pattern.corners)
        th, tw = template.shape[:2]
        ih, iw = image.shape[:2]
        if th < 4 or tw < 4:
            raise ValueError("template too small (must be >= 4x4)")
        if th > ih or tw > iw:
            raise ValueError("template is larger than image")

        # Work in grayscale for matchTemplate stability.
        img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        tmpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if template.ndim == 3 else template

        img_p = self._preprocess(img_gray, merged)
        tmpl_p = self._preprocess(tmpl_gray, merged)
        scores = cv2.matchTemplate(img_p, tmpl_p, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(scores >= threshold)
        if ys.size == 0:
            return []

        template_angle = pattern.rrect.angle
        candidates: list[MatchResult] = []
        for y, x in zip(ys.tolist(), xs.tolist()):
            s = float(scores[y, x])
            cx = x + tw / 2.0
            cy = y + th / 2.0
            rr = RRect(cx=cx, cy=cy, w=float(tw), h=float(th), angle=template_angle)
            candidates.append(MatchResult.from_rrect(rr, score=s))

        candidates.sort(key=lambda m: m.score, reverse=True)
        kept: list[MatchResult] = []
        for cand in candidates:
            cand_rr = RRect(cx=cand.cx, cy=cand.cy, w=cand.w, h=cand.h, angle=cand.angle)
            if any(
                iou_rrect(cand_rr, RRect(cx=k.cx, cy=k.cy, w=k.w, h=k.h, angle=k.angle))
                >= nms_iou
                for k in kept
            ):
                continue
            kept.append(cand)
            if len(kept) >= max_results:
                break
        return kept
