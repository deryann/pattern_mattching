from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .ccoeff import CCoeffNormedMatcher


class CCoeffEdgeMatcher(CCoeffNormedMatcher):
    """Edge-based template matching.

    Runs Canny on both image and template before TM_CCOEFF_NORMED. Useful when
    instances share shape/outline but differ in internal texture (e.g. parking
    slots with different numbers, printed forms with varying text inside a frame).
    """

    id = "ccoeff_edge"
    name = "Edge (Canny) + CCOEFF Normed"
    supports_rotation = False
    default_params = {
        **CCoeffNormedMatcher.default_params,
        "threshold": 0.4,
        "canny_low": 80,
        "canny_high": 200,
        "blur_ksize": 3,
    }

    def _preprocess(self, gray: np.ndarray, params: dict[str, Any]) -> np.ndarray:
        low = int(params.get("canny_low", 50))
        high = int(params.get("canny_high", 150))
        k = int(params.get("blur_ksize", 3))
        if k > 1:
            if k % 2 == 0:
                k += 1  # Gaussian kernel size must be odd
            blurred = cv2.GaussianBlur(gray, (k, k), 0)
        else:
            blurred = gray
        return cv2.Canny(blurred, low, high)
