// Thin wrapper over Fabric.js canvas for drawing image + patterns.
// Emits high-level events via callbacks; all mutations flow back through app.js.

import { fabricToPattern, patternToFabricProps } from "/static/js/pattern.js";

const STROKE_TEMPLATE = "#1f6feb";
const STROKE_MATCH = "#1a7f37";

export class Board {
  constructor(canvasEl, handlers) {
    this.canvas = new fabric.Canvas(canvasEl, {
      backgroundColor: "#ffffff",
      selection: false,
      preserveObjectStacking: true,
      uniformScaling: false,
    });
    this.handlers = handlers;
    this.imageObject = null;
    this.objectsById = new Map();
    this.suppressEvents = false;

    this._bindEvents();
  }

  _bindEvents() {
    this.canvas.on("mouse:move", (opt) => {
      const p = this.canvas.getPointer(opt.e);
      this.handlers.onCursorMove?.(p.x, p.y);
    });

    // Wheel zoom centered on cursor.
    this.canvas.on("mouse:wheel", (opt) => {
      const delta = opt.e.deltaY;
      let zoom = this.canvas.getZoom();
      zoom *= Math.pow(0.999, delta);
      zoom = Math.max(0.1, Math.min(zoom, 8));
      this.canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, zoom);
      opt.e.preventDefault();
      opt.e.stopPropagation();
      this.handlers.onZoom?.(zoom);
    });

    // Space+drag pan
    this._spaceDown = false;
    this._panLast = null;
    window.addEventListener("keydown", (e) => {
      if (e.code === "Space") this._spaceDown = true;
    });
    window.addEventListener("keyup", (e) => {
      if (e.code === "Space") { this._spaceDown = false; this._panLast = null; this.canvas.defaultCursor = "default"; }
    });
    this.canvas.on("mouse:down", (opt) => {
      if (this._spaceDown) { this._panLast = { x: opt.e.clientX, y: opt.e.clientY }; this.canvas.defaultCursor = "grabbing"; }
    });
    this.canvas.on("mouse:move", (opt) => {
      if (this._spaceDown && this._panLast) {
        const dx = opt.e.clientX - this._panLast.x;
        const dy = opt.e.clientY - this._panLast.y;
        const vpt = this.canvas.viewportTransform;
        vpt[4] += dx; vpt[5] += dy;
        this.canvas.requestRenderAll();
        this._panLast = { x: opt.e.clientX, y: opt.e.clientY };
      }
    });
    this.canvas.on("mouse:up", () => { this._panLast = null; if (!this._spaceDown) this.canvas.defaultCursor = "default"; });

    this.canvas.on("selection:created", (e) => this._handleSelection(e));
    this.canvas.on("selection:updated", (e) => this._handleSelection(e));
    this.canvas.on("selection:cleared", () => this.handlers.onSelect?.(null));

    this.canvas.on("object:modified", (e) => {
      if (this.suppressEvents) return;
      const t = e.target;
      if (!t || !t.patternId) return;
      const p = fabricToPattern(t);
      this.handlers.onPatternChanged?.(t.patternId, p);
    });
  }

  _handleSelection(e) {
    const t = e.selected?.[0] ?? this.canvas.getActiveObject();
    if (t && t.patternId) this.handlers.onSelect?.(t.patternId);
  }

  setImage(dataURL, done) {
    fabric.Image.fromURL(dataURL, (img) => {
      if (this.imageObject) this.canvas.remove(this.imageObject);
      img.set({
        left: 0, top: 0, originX: "left", originY: "top",
        selectable: false, evented: false,
      });
      this.imageObject = img;
      this.canvas.setWidth(img.width);
      this.canvas.setHeight(img.height);
      this.canvas.add(img);
      this.canvas.sendToBack(img);
      this.canvas.requestRenderAll();
      done?.({ width: img.width, height: img.height });
    });
  }

  addPattern(p) {
    const stroke = p.role === "template" ? STROKE_TEMPLATE : STROKE_MATCH;
    const rect = new fabric.Rect({
      ...patternToFabricProps(p),
      fill: "rgba(0,0,0,0)",
      stroke,
      strokeWidth: 2,
      strokeUniform: true,
      cornerColor: stroke,
      cornerSize: 10,
      transparentCorners: false,
      hasRotatingPoint: true,
      lockUniScaling: false,
      selectable: p.role === "template" ? true : true,
    });
    rect.patternId = p.id;
    this.objectsById.set(p.id, rect);
    this.canvas.add(rect);
    this.canvas.requestRenderAll();
  }

  updatePattern(p) {
    const obj = this.objectsById.get(p.id);
    if (!obj) return;
    this.suppressEvents = true;
    obj.set(patternToFabricProps(p));
    obj.setCoords();
    this.canvas.requestRenderAll();
    this.suppressEvents = false;
  }

  removePattern(id) {
    const obj = this.objectsById.get(id);
    if (!obj) return;
    this.canvas.remove(obj);
    this.objectsById.delete(id);
    this.canvas.requestRenderAll();
  }

  selectPattern(id) {
    if (!id) {
      this.canvas.discardActiveObject();
      this.canvas.requestRenderAll();
      return;
    }
    const obj = this.objectsById.get(id);
    if (!obj) return;
    this.canvas.setActiveObject(obj);
    this.canvas.requestRenderAll();
  }

  clearPatterns() {
    for (const [, obj] of this.objectsById) this.canvas.remove(obj);
    this.objectsById.clear();
    this.canvas.requestRenderAll();
  }

  // Draw-rect tool: click-drag to place a pattern.
  enterDrawMode({ shape, onFinish }) {
    let startX = 0, startY = 0, rect = null, down = false;
    const canvas = this.canvas;
    canvas.defaultCursor = "crosshair";
    canvas.selection = false;
    canvas.forEachObject((o) => (o.selectable = false));

    const onDown = (opt) => {
      if (!this.imageObject) return;
      const p = canvas.getPointer(opt.e);
      startX = p.x; startY = p.y; down = true;
      rect = new fabric.Rect({
        left: startX, top: startY,
        originX: "left", originY: "top",
        width: 1, height: 1,
        fill: "rgba(31,111,235,0.1)",
        stroke: STROKE_TEMPLATE, strokeWidth: 2, strokeUniform: true,
        selectable: false, evented: false,
      });
      canvas.add(rect);
    };
    const onMove = (opt) => {
      if (!down || !rect) return;
      const p = canvas.getPointer(opt.e);
      const w = p.x - startX, h = p.y - startY;
      rect.set({
        left: Math.min(startX, p.x), top: Math.min(startY, p.y),
        width: Math.abs(w), height: Math.abs(h),
      });
      canvas.requestRenderAll();
    };
    const onUp = () => {
      if (!down || !rect) return;
      down = false;
      const patternData = {
        shape,
        cx: rect.left + rect.width / 2,
        cy: rect.top + rect.height / 2,
        w: rect.width,
        h: rect.height,
        angle: 0,
      };
      canvas.remove(rect);
      rect = null;
      this._exitDrawMode();
      if (patternData.w >= 4 && patternData.h >= 4) onFinish(patternData);
      else onFinish(null);
    };

    canvas.on("mouse:down", onDown);
    canvas.on("mouse:move", onMove);
    canvas.on("mouse:up", onUp);
    this._drawHandlers = { onDown, onMove, onUp };
  }

  _exitDrawMode() {
    const canvas = this.canvas;
    const h = this._drawHandlers;
    if (h) {
      canvas.off("mouse:down", h.onDown);
      canvas.off("mouse:move", h.onMove);
      canvas.off("mouse:up", h.onUp);
      this._drawHandlers = null;
    }
    canvas.defaultCursor = "default";
    canvas.forEachObject((o) => {
      if (o.patternId) o.selectable = true;
    });
  }

  cancelDraw() { this._exitDrawMode(); }
}
