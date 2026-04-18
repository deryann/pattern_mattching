# pattern_mattching

在瀏覽器中標記 template pattern 並對影像執行 OpenCV Template Matching 的前後端工具。

## 目錄結構

```
backend/     Python 3.11 + FastAPI + OpenCV；演算法抽象層
frontend/    Vanilla HTML/CSS/JS + Fabric.js (CDN)
specs/       需求規格與規劃文件
test_image/  範例圖片 (停車場平面圖)
```

## 啟動

建議使用 [uv](https://docs.astral.sh/uv/)（會依 `.python-version` 自動下載 Python 3.11）：

```bash
uv sync                                         # 建 venv + 安裝依賴
uv run uvicorn backend.main:app --reload --port 8000
```

或使用傳統 pip：

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

瀏覽器開 `http://localhost:8000/`。

## 使用流程

1. **Upload**：選擇 PNG/JPEG 影像（≤ 20 MB）。
2. **Draw Rect / Draw Rotated Rect**：於影像上拖曳出 template；可拖移、縮放、以中心旋轉。
3. 調整 Algorithm / Threshold，按 **Quick Mark** → 後端執行 `cv2.matchTemplate` + NMS，回傳匹配結果。
4. Canvas 顯示綠色匹配框；Pattern Table 列出每筆的 `cx, cy, w, h, angle, score`。
5. 點選任一 pattern → 按 `d` / `Delete` 刪除。
6. **Save JSON**：下載目前所有 pattern（含 template 與 match）。

## 鍵盤快捷鍵

| 鍵 | 行為 |
|----|------|
| `d` / `Delete` / `Backspace` | 刪除選取的 pattern |
| `Esc` | 取消目前工具 / 取消選取 |
| `Space` + 拖曳 | 平移畫布 |
| 滾輪 | 以游標為中心縮放畫布 |

## API

- `GET /api/healthz` — liveness
- `GET /api/algorithms` — 列出註冊的演算法
- `POST /api/match` — 送出圖片 + template，取得匹配結果

完整 schema 見 `specs/001_spec.md` §4。

## 新增演算法

1. 在 `backend/core/algorithms/` 新增檔案，繼承 `AbstractMatcher` 並實作 `match()`。
2. 於 `backend/core/algorithms/__init__.py` 加一行 `register(MyMatcher())`。
3. 前端 `Algorithm` 下拉選單會自動出現。

## 測試

```bash
uv run pytest -v
```

## 驗收 (對應 specs/001_spec.md §9)

- [x] 1. Upload `test_image/image_01.png` 正確顯示
- [x] 2. Draw Rect / Draw Rotated Rect 可拖曳、縮放、旋轉
- [x] 3. Pattern Table 即時反映 template 狀態
- [x] 4. Quick Mark POST `/api/match` 含 base64 + 4 corners
- [x] 5. 後端回傳匹配結果；切換演算法只需改 dropdown
- [x] 6. Canvas 綠色匹配框 + Table 顯示 score
- [x] 7. 點 pattern + 按 `d` 同步從 Canvas 與 Table 刪除
- [x] 8. Save JSON 下載符合 §3.6 schema 的檔案

## 版本

v0.1.0 — 單張圖片、單一演算法 (`ccoeff_normed`)、單一尺度單一角度。Roadmap 見 `specs/001_spec.md` §10。
