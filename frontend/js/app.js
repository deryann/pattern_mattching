// Entry point: wires the UI, state, canvas, table, and API together.

import { Board } from "/static/js/canvas.js";
import { PatternTable } from "/static/js/table.js";
import { createPattern, patternToCorners } from "/static/js/pattern.js";
import { getAlgorithms, postMatch } from "/static/js/api.js";
import { readImageFile, dataUrlToBase64, downloadJson, buildExportPayload } from "/static/js/io.js";

const AppState = {
  image: null,                // { filename, width, height, dataURL }
  patterns: [],
  selection: { id: null },
  tool: "select",
  viewport: { scale: 1, offsetX: 0, offsetY: 0 },
  algorithms: [],
};

const $ = (sel) => document.querySelector(sel);
const statusEl = {
  cursor: $("#status-cursor"),
  zoom: $("#status-zoom"),
  selected: $("#status-selected"),
  msg: $("#status-msg"),
};

function toast(message, { error = false, duration = 2500 } = {}) {
  const el = document.createElement("div");
  el.className = "toast" + (error ? " error" : "");
  el.textContent = message;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.add("show"));
  setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.remove(), 250);
  }, duration);
}

const board = new Board($("#board"), {
  onCursorMove: (x, y) => {
    statusEl.cursor.textContent = `cursor: ${Math.round(x)}, ${Math.round(y)}`;
  },
  onZoom: (z) => {
    statusEl.zoom.textContent = `zoom: ${Math.round(z * 100)}%`;
  },
  onSelect: (id) => {
    AppState.selection.id = id;
    statusEl.selected.textContent = `selected: ${id ? id.slice(0, 10) : "-"}`;
    table.highlight(id);
  },
  onPatternChanged: (id, partial) => {
    const p = AppState.patterns.find((x) => x.id === id);
    if (!p) return;
    Object.assign(p, partial, { updatedAt: new Date().toISOString() });
    renderTable();
  },
});

const table = new PatternTable($("#pattern-table tbody"), {
  onSelect: (id) => {
    AppState.selection.id = id;
    board.selectPattern(id);
    statusEl.selected.textContent = `selected: ${id.slice(0, 10)}`;
    table.highlight(id);
  },
  onDelete: (id) => deletePattern(id),
});

function renderTable() {
  table.render(AppState.patterns, AppState.selection.id);
}

function addPattern(data, role) {
  const p = createPattern({ role, ...data });
  AppState.patterns.push(p);
  board.addPattern(p);
  renderTable();
  return p;
}

function deletePattern(id) {
  const idx = AppState.patterns.findIndex((p) => p.id === id);
  if (idx === -1) return;
  AppState.patterns.splice(idx, 1);
  board.removePattern(id);
  if (AppState.selection.id === id) {
    AppState.selection.id = null;
    statusEl.selected.textContent = "selected: -";
  }
  renderTable();
}

function getTemplatePattern() {
  return AppState.patterns.find((p) => p.role === "template");
}

// Tool switching
function setTool(name) {
  AppState.tool = name;
  document.querySelectorAll(".btn.tool").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tool === name);
  });
  board.cancelDraw();
  if (name === "rect" || name === "rrect") {
    board.enterDrawMode({
      shape: name,
      onFinish: (data) => {
        setTool("select");
        if (!data) { toast("pattern too small (min 4x4)", { error: true }); return; }
        if (getTemplatePattern()) {
          toast("only one template allowed — replace existing", { error: true });
          return;
        }
        addPattern(data, "template");
      },
    });
  }
}

// Event wiring
$("#tool-select").addEventListener("click", () => setTool("select"));
$("#tool-rect").addEventListener("click", () => setTool("rect"));
$("#tool-rrect").addEventListener("click", () => setTool("rrect"));

$("#file-input").addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  try {
    const { filename, dataURL } = await readImageFile(file);
    AppState.image = { filename, dataURL };
    // clear existing patterns when loading a new image
    for (const p of [...AppState.patterns]) deletePattern(p.id);
    board.setImage(dataURL, ({ width, height }) => {
      AppState.image.width = width;
      AppState.image.height = height;
      toast(`loaded ${filename} (${width}x${height})`);
    });
  } catch (err) {
    toast(`failed to load: ${err.message}`, { error: true });
  }
});

$("#clear-all").addEventListener("click", () => {
  for (const p of [...AppState.patterns]) deletePattern(p.id);
});

$("#save-json").addEventListener("click", () => {
  if (!AppState.image) { toast("no image loaded", { error: true }); return; }
  const payload = buildExportPayload(AppState);
  const stem = (AppState.image.filename || "patterns").replace(/\.[^.]+$/, "");
  downloadJson(`${stem}_patterns.json`, payload);
});

$("#quick-mark").addEventListener("click", async () => {
  const tmpl = getTemplatePattern();
  if (!AppState.image) { toast("upload an image first", { error: true }); return; }
  if (!tmpl) { toast("draw a template first", { error: true }); return; }
  if (tmpl.w < 8 || tmpl.h < 8) { toast("template must be >= 8x8", { error: true }); return; }

  const algorithm = $("#algo-select").value || "ccoeff_normed";
  const threshold = parseFloat($("#threshold").value);
  const algoInfo = AppState.algorithms.find((a) => a.id === algorithm);
  const params = {
    ...(algoInfo?.default_params || {}),
    ...(isNaN(threshold) ? {} : { threshold }),
  };

  statusEl.msg.textContent = "matching…";
  const btn = $("#quick-mark");
  btn.disabled = true;
  try {
    const result = await postMatch({
      image: {
        filename: AppState.image.filename,
        data_base64: dataUrlToBase64(AppState.image.dataURL),
      },
      template: {
        shape: tmpl.shape,
        corners: patternToCorners(tmpl),
      },
      algorithm,
      params,
    });
    // remove previous match results, keep template
    for (const p of [...AppState.patterns]) {
      if (p.role === "match") deletePattern(p.id);
    }
    for (const m of result.matches) {
      addPattern({
        shape: "rrect",
        cx: m.cx, cy: m.cy, w: m.w, h: m.h, angle: m.angle,
        score: m.score,
      }, "match");
    }
    statusEl.msg.textContent = `${result.matches.length} matches (${result.elapsed_ms} ms)`;
    toast(`${result.matches.length} matches found`);
  } catch (err) {
    statusEl.msg.textContent = "";
    toast(`match failed: ${err.message}`, { error: true });
  } finally {
    btn.disabled = false;
  }
});

window.addEventListener("keydown", (e) => {
  const tag = e.target?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
  if (e.key === "d" || e.key === "Delete" || e.key === "Backspace") {
    if (AppState.selection.id) {
      e.preventDefault();
      deletePattern(AppState.selection.id);
    }
  } else if (e.key === "Escape") {
    setTool("select");
    board.selectPattern(null);
  }
});

// Expose a minimal debug handle for automated tests / console use.
window.__app = {
  get state() { return AppState; },
  get board() { return board; },
  addPattern, deletePattern, setTool,
};

// When algorithm changes, load its default threshold into the input.
function applyAlgoDefaults(algoId) {
  const a = AppState.algorithms.find((x) => x.id === algoId);
  if (!a) return;
  const t = a.default_params?.threshold;
  if (typeof t === "number") $("#threshold").value = t;
}

$("#algo-select").addEventListener("change", (e) => applyAlgoDefaults(e.target.value));

// Initial load
(async () => {
  try {
    const data = await getAlgorithms();
    AppState.algorithms = data.algorithms;
    const select = $("#algo-select");
    select.innerHTML = "";
    for (const a of data.algorithms) {
      const opt = document.createElement("option");
      opt.value = a.id;
      opt.textContent = a.name;
      select.appendChild(opt);
    }
    applyAlgoDefaults(select.value);
  } catch (err) {
    toast(`failed to load algorithms: ${err.message}`, { error: true });
  }
})();
