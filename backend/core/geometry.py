from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

Point = tuple[float, float]
Corners = list[Point]


@dataclass(frozen=True)
class RRect:
    cx: float
    cy: float
    w: float
    h: float
    angle: float  # degrees, 0 = axis-aligned; positive = counter-clockwise


def normalize_angle(deg: float) -> float:
    a = ((deg + 180.0) % 360.0) - 180.0
    return a if a > -180.0 else a + 360.0


def corners_to_rrect(corners: Corners) -> RRect:
    """Convert 4 corners (TL, TR, BR, BL order) to center/size/angle form."""
    if len(corners) != 4:
        raise ValueError("corners must have exactly 4 points")
    pts = np.asarray(corners, dtype=np.float64)
    tl, tr, br, bl = pts
    cx = float(pts[:, 0].mean())
    cy = float(pts[:, 1].mean())
    w = float(np.linalg.norm(tr - tl))
    h = float(np.linalg.norm(bl - tl))
    dx = tr[0] - tl[0]
    dy = tr[1] - tl[1]
    angle = normalize_angle(-math.degrees(math.atan2(dy, dx)))
    return RRect(cx=cx, cy=cy, w=w, h=h, angle=angle)


def rrect_to_corners(rr: RRect) -> Corners:
    """Return 4 corners in TL, TR, BR, BL order (image coords, y-down)."""
    cos_a = math.cos(math.radians(-rr.angle))
    sin_a = math.sin(math.radians(-rr.angle))
    hw, hh = rr.w / 2.0, rr.h / 2.0
    local = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    out: Corners = []
    for x, y in local:
        rx = x * cos_a - y * sin_a
        ry = x * sin_a + y * cos_a
        out.append((rr.cx + rx, rr.cy + ry))
    return out


def extract_template(image: np.ndarray, corners: Corners) -> np.ndarray:
    """Affine-warp the region defined by corners (TL,TR,BR,BL) to an axis-aligned
    template. Corners are continuous coordinates; output size = (round(w), round(h))
    with the three reference points mapped to dst=(0,0),(w,0),(w,h) so the mapping
    is a pure 1:1 scale/translation for axis-aligned rects on integer coords."""
    rr = corners_to_rrect(corners)
    w = max(1, int(round(rr.w)))
    h = max(1, int(round(rr.h)))
    src = np.asarray(corners[:3], dtype=np.float32)  # TL, TR, BR
    dst = np.asarray([[0, 0], [w, 0], [w, h]], dtype=np.float32)
    M = cv2.getAffineTransform(src, dst)
    warped = cv2.warpAffine(
        image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    )
    return warped


def is_inside_image(corners: Corners, width: int, height: int, margin: float = 0.5) -> bool:
    for x, y in corners:
        if x < -margin or y < -margin or x > width - 1 + margin or y > height - 1 + margin:
            return False
    return True


def iou_rrect(a: RRect, b: RRect) -> float:
    """Rotated-rect IoU via cv2.rotatedRectangleIntersection."""
    ra = ((a.cx, a.cy), (a.w, a.h), -a.angle)
    rb = ((b.cx, b.cy), (b.w, b.h), -b.angle)
    ret, inter = cv2.rotatedRectangleIntersection(ra, rb)
    if ret == 0 or inter is None:
        return 0.0
    inter_area = float(cv2.contourArea(inter))
    union = a.w * a.h + b.w * b.h - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union
