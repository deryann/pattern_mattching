// Pattern model: single source of truth uses (cx, cy, w, h, angle).
// angle in degrees, CCW positive (screen coords have y-down, so angle is the visual
// rotation of the rect about its center).

export function makeId() {
  return "p-" + Math.random().toString(36).slice(2, 10);
}

export function createPattern({ role, shape, cx, cy, w, h, angle = 0, score = null }) {
  const now = new Date().toISOString();
  return {
    id: makeId(),
    role,                 // 'template' | 'match'
    shape,                // 'rect' | 'rrect'
    cx, cy, w, h, angle,
    score,
    createdAt: now,
    updatedAt: now,
  };
}

// Convert (cx,cy,w,h,angle[deg]) -> 4 corners (TL,TR,BR,BL) in image coords (y-down).
// Positive angle rotates CCW visually. In y-down coordinates CCW is angle -> -angle when
// applied with standard math matrices, so we use -angle for the rotation.
export function patternToCorners(p) {
  const rad = (-p.angle) * Math.PI / 180;
  const cos = Math.cos(rad), sin = Math.sin(rad);
  const hw = p.w / 2, hh = p.h / 2;
  const local = [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]];
  return local.map(([x, y]) => [p.cx + x * cos - y * sin, p.cy + x * sin + y * cos]);
}

// Convert 4 corners back to (cx,cy,w,h,angle). Mirrors backend geometry.corners_to_rrect.
export function cornersToPattern(corners) {
  const [tl, tr, br, bl] = corners;
  const cx = (tl[0] + tr[0] + br[0] + bl[0]) / 4;
  const cy = (tl[1] + tr[1] + br[1] + bl[1]) / 4;
  const w = Math.hypot(tr[0] - tl[0], tr[1] - tl[1]);
  const h = Math.hypot(bl[0] - tl[0], bl[1] - tl[1]);
  const dx = tr[0] - tl[0], dy = tr[1] - tl[1];
  let angle = -Math.atan2(dy, dx) * 180 / Math.PI;
  angle = ((angle + 180) % 360) - 180;
  if (angle <= -180) angle += 360;
  return { cx, cy, w, h, angle };
}

// Sync helpers for Fabric.js rect objects.
// Fabric's `angle` property is CW-positive in y-down screen coords, which matches
// our "visual" expectation; our stored angle is CCW-positive (math convention),
// so sign needs flipping when bridging.
export function fabricToPattern(obj) {
  const cx = obj.left + (obj.width * obj.scaleX) / 2 * Math.cos(fabric.util.degreesToRadians(obj.angle))
           - (obj.height * obj.scaleY) / 2 * Math.sin(fabric.util.degreesToRadians(obj.angle));
  const cy = obj.top + (obj.width * obj.scaleX) / 2 * Math.sin(fabric.util.degreesToRadians(obj.angle))
           + (obj.height * obj.scaleY) / 2 * Math.cos(fabric.util.degreesToRadians(obj.angle));
  // Simpler: use getCenterPoint()
  const c = obj.getCenterPoint();
  return {
    cx: c.x,
    cy: c.y,
    w: obj.width * obj.scaleX,
    h: obj.height * obj.scaleY,
    angle: -obj.angle,
  };
}

export function patternToFabricProps(p) {
  return {
    width: p.w,
    height: p.h,
    scaleX: 1,
    scaleY: 1,
    angle: -p.angle,
    originX: "center",
    originY: "center",
    left: p.cx,
    top: p.cy,
  };
}
