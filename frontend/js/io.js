// File I/O helpers: upload via FileReader, download JSON via Blob.

import { patternToCorners } from "/static/js/pattern.js";

export function readImageFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({ filename: file.name, dataURL: reader.result });
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export function dataUrlToBase64(dataURL) {
  const comma = dataURL.indexOf(",");
  return comma === -1 ? dataURL : dataURL.slice(comma + 1);
}

export function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function buildExportPayload(state) {
  return {
    version: "0.1",
    image: {
      filename: state.image?.filename ?? null,
      width: state.image?.width ?? null,
      height: state.image?.height ?? null,
    },
    patterns: state.patterns.map((p) => ({
      id: p.id,
      role: p.role,
      shape: p.shape,
      cx: p.cx, cy: p.cy, w: p.w, h: p.h, angle: p.angle,
      corners: patternToCorners(p),
      score: p.score,
    })),
    exportedAt: new Date().toISOString(),
  };
}
