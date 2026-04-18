# Pattern Matching Web App — 產品規劃書 (v0.1)

本文件為 `specs/1st.md` 的完整化規格，將原始需求擴充為可直接進入實作階段的產品規劃書。

---

## 1. 產品定位

### 1.1 目標
提供一個輕量、可在瀏覽器操作的 Pattern Matching 輔助工具，讓使用者能夠：
- 上傳圖片
- 以「矩形 / 旋轉矩形」標記感興趣的 Template Pattern
- 一鍵送至後端進行 Template Matching，將找到的相似區域回傳至前端視覺化
- 對偵測結果進行人工增刪修改，最後匯出標註結果 (JSON)

### 1.2 使用者情境
- **品質檢測工程師**：在產線照片中找出重複出現的標記
- **資料標註人員**：批次產生訓練資料的 bounding box
- **研究/教學用途**：快速驗證 OpenCV Template Matching 演算法效果

### 1.3 非目標 (Out of Scope, v0.1)
- 多使用者帳號 / 權限管理
- 專案保存與雲端同步
- 深度學習 (CNN/Transformer) 類型的偵測演算法
- 批次處理多張圖片 (單張圖片為主)
- 手機 / 觸控裝置原生操作 (以桌面滑鼠為主)

---

## 2. 系統架構

### 2.1 總覽
```
┌──────────────────────────┐        HTTP/JSON        ┌────────────────────────────┐
│      Frontend (SPA)      │ ───────────────────────▶│  Backend (FastAPI, 3.11)   │
│  HTML + Vanilla JS + CSS │                         │  OpenCV + Algorithm Layer  │
│   Canvas/SVG 標記層      │ ◀────────────────────── │   File I/O, Job Manager    │
└──────────────────────────┘      matches (JSON)     └────────────────────────────┘
```

### 2.2 技術選型
| 層級 | 技術 | 說明 |
|------|------|------|
| 前端 | HTML5 / CSS3 / Vanilla JS (ES2020+) | 不使用 build pipeline；允許以 CDN 引入少量第三方庫 |
| 前端第三方 (可選) | Fabric.js 或原生 Canvas API | 用於處理可拖曳/縮放/旋轉的矩形。若以 Canvas 手刻，維持 0-build 原則 |
| 後端 | Python 3.11 + FastAPI + Uvicorn | REST API |
| 影像處理 | OpenCV (cv2) ≥ 4.8 | 核心 matching |
| 輔助套件 | numpy, pydantic, python-multipart | pydantic 用於 request/response schema |
| 封包 | 本機開發：`uvicorn main:app --reload` | 可在單一 port 同時 serve 前端 static 檔 |

### 2.3 目錄結構 (建議)
```
pattern_mattching/
├── backend/
│   ├── main.py                 # FastAPI 進入點
│   ├── api/
│   │   └── match.py            # /api/match endpoint
│   ├── core/
│   │   ├── algorithms/
│   │   │   ├── base.py         # AbstractMatcher (詳見 §5.1)
│   │   │   ├── ccoeff.py       # OpenCV cv2.matchTemplate
│   │   │   └── registry.py     # 演算法註冊/查表
│   │   ├── geometry.py         # 旋轉矩形、仿射變換工具
│   │   └── image_io.py         # base64 ↔ ndarray
│   ├── schemas.py              # Pydantic models
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── main.css
│   │   └── components.css
│   └── js/
│       ├── app.js              # 入口、狀態管理
│       ├── canvas.js           # 繪圖層、互動
│       ├── pattern.js          # Pattern 物件模型 (含旋轉)
│       ├── table.js            # 結果列表 UI
│       ├── api.js              # fetch wrapper
│       └── io.js               # 上傳 / 下載 JSON
├── specs/
│   ├── 1st.md
│   └── 001_spec.md             # (本文件)
└── test_image/
    ├── image_01.png
    ├── image_02.png
    └── image_03.png
```

---

## 3. 前端規劃

### 3.1 畫面配置 (Layout)
```
┌──────────────────────────────────────────────────────────────┐
│  Toolbar: [Upload] [Draw Rect] [Draw Rotated Rect] [Quick   │
│           Mark] [Save JSON] [Clear All]                     │
├────────────────────────────────────────────┬─────────────────┤
│                                            │  Pattern Table  │
│                                            │ ┌─────────────┐ │
│            Canvas / 影像顯示區             │ │ Type  XYWH  │ │
│            (含可互動 Pattern 圖層)         │ │ Tmpl  ...   │ │
│                                            │ │ Match ...   │ │
│                                            │ └─────────────┘ │
├────────────────────────────────────────────┴─────────────────┤
│  Status Bar: cursor(x,y) / zoom / selected pattern id        │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 前端狀態 (Single Source of Truth)
以 `AppState` 單一物件持有：
```js
AppState = {
  image: { filename, width, height, dataURL },
  patterns: [
    {
      id: 'p-uuid',
      role: 'template' | 'match',            // template 為使用者標記；match 為後端回傳
      shape: 'rect' | 'rrect',                // 矩形 / 旋轉矩形
      cx, cy, w, h, angle,                    // 中心點 + 寬高 + 旋轉角 (deg)
      score: number|null,                     // match 才有
      createdAt, updatedAt,
    }
  ],
  selection: { id: 'p-uuid' | null },
  tool: 'select' | 'rect' | 'rrect',
  viewport: { scale, offsetX, offsetY },
}
```

### 3.3 Pattern 幾何模型
- 所有 Pattern 內部一律以 (cx, cy, w, h, angle) 保存。
- 四個角點 (x1,y1)~(x4,y4) 以順序「左上、右上、右下、左下」依角度旋轉後計算。
- 與後端交換時使用四點座標 (符合 `1st.md` 第 4.b 點)，並附上 (cx, cy, w, h, angle) 作輔助欄位以便除錯。

### 3.4 互動規格
| 操作 | 行為 |
|------|------|
| 左鍵拖曳 pattern 本體 | 平移 |
| 左鍵拖曳角落 handle | 等比/非等比縮放 (按 Shift 等比) |
| 左鍵拖曳旋轉 handle | 以中心點旋轉；按 Shift 鎖定 15° 吸附 |
| 點擊 pattern | 設為 selected；Table 對應列 highlight |
| 鍵盤 `d` | 刪除 selected pattern (對應 `1st.md` 第 7 點) |
| 鍵盤 `Esc` | 取消選取 / 取消繪製 |
| 滑鼠滾輪 | 以游標為中心縮放整個畫布 |
| 空白鍵 + 拖曳 | 平移畫布 |

### 3.5 Pattern Table 欄位
| 欄位 | 說明 |
|------|------|
| # | 序號 |
| ID | Pattern UUID 前 8 碼 |
| Role | Template / Match |
| Shape | Rect / RRect |
| cx, cy | 中心座標 (整數像素) |
| w × h | 寬高 |
| angle | 旋轉角 (度) |
| score | Match 分數 (0–1)，Template 留白 |
| actions | 聚焦、刪除 |

### 3.6 檔案 I/O
- **上傳**：`<input type="file" accept="image/*">`；前端以 `FileReader` 轉為 `dataURL`，顯示於 Canvas；同時保留 filename。
- **Save JSON** (對應 `1st.md` 第 8 點)：
  ```json
  {
    "version": "0.1",
    "image": { "filename": "image_01.png", "width": 1920, "height": 1080 },
    "patterns": [
      {
        "id": "p-...", "role": "template", "shape": "rrect",
        "cx": 512, "cy": 384, "w": 120, "h": 80, "angle": 15.0,
        "corners": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]],
        "score": null
      }
    ],
    "exportedAt": "2026-04-18T12:34:56+08:00"
  }
  ```

---

## 4. 後端 API

所有 endpoint 前綴 `/api`，回傳 `application/json`，錯誤使用標準 HTTP 狀態碼 + `{ "detail": "..." }`.

### 4.1 `POST /api/match`
將圖片 + template pattern 送入指定演算法進行 matching。

**Request**
```json
{
  "image": {
    "filename": "image_01.png",
    "data_base64": "iVBORw0KGgoAAAA..."
  },
  "template": {
    "shape": "rrect",
    "corners": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
  },
  "algorithm": "ccoeff_normed",
  "params": {
    "threshold": 0.85,
    "max_results": 50,
    "nms_iou": 0.3,
    "multi_scale": false,
    "scales": [1.0],
    "multi_angle": false,
    "angle_range": [-15, 15],
    "angle_step": 5
  }
}
```

**Response (200)**
```json
{
  "algorithm": "ccoeff_normed",
  "elapsed_ms": 312,
  "matches": [
    {
      "corners": [[...],[...],[...],[...]],
      "cx": 620, "cy": 410, "w": 120, "h": 80, "angle": 15.0,
      "score": 0.93
    }
  ]
}
```

**錯誤碼**
| Code | 原因 |
|------|------|
| 400 | base64 解碼失敗 / pattern 超出影像範圍 / 參數非法 |
| 413 | 圖片大小超過上限 (預設 20 MB) |
| 422 | pydantic 驗證錯誤 |
| 500 | 演算法內部錯誤 |

### 4.2 `GET /api/algorithms`
回傳目前註冊可用的演算法清單與預設參數 schema，供前端動態產生設定 UI。
```json
{
  "algorithms": [
    {
      "id": "ccoeff_normed",
      "name": "OpenCV CCOEFF Normed",
      "supports_rotation": false,
      "default_params": { "threshold": 0.85, "max_results": 50, "nms_iou": 0.3 }
    }
  ]
}
```

### 4.3 `GET /api/healthz`
Liveness probe，回 `{ "status": "ok", "version": "0.1.0" }`.

---

## 5. 演算法抽象層 (核心)

對應 `1st.md` 第 5.a 點 — 可替換之演算法介面。

### 5.1 介面定義
```python
# backend/core/algorithms/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import numpy as np

@dataclass(frozen=True)
class PatternSpec:
    """輸入的 template pattern。四個角點為順時針排列。"""
    corners: list[tuple[float, float]]  # [(x1,y1)...(x4,y4)]
    shape: str                           # 'rect' | 'rrect'

    @property
    def cx(self) -> float: ...
    @property
    def cy(self) -> float: ...
    @property
    def w(self) -> float: ...
    @property
    def h(self) -> float: ...
    @property
    def angle(self) -> float: ...        # deg, 0 = 水平

@dataclass(frozen=True)
class MatchResult:
    corners: list[tuple[float, float]]
    cx: float; cy: float
    w: float; h: float; angle: float
    score: float                         # 0.0 – 1.0 (愈大愈相似)

class AbstractMatcher(ABC):
    id: str                              # 唯一識別，例 'ccoeff_normed'
    name: str
    supports_rotation: bool = False

    @abstractmethod
    def match(
        self,
        image: np.ndarray,               # BGR, uint8
        pattern: PatternSpec,
        params: dict[str, Any],
    ) -> list[MatchResult]:
        """回傳所有超過 threshold 的候選，已做 NMS。"""
```

### 5.2 預設實作：`CCoeffNormedMatcher`
1. 由 `PatternSpec.corners` 計算最小外接矩形並以仿射變換把 template 取出 (支援 `rrect`)。
2. 若 `params.multi_angle = True`，在 `angle_range` 內以 `angle_step` 掃描，取局部最大。
3. 若 `params.multi_scale = True`，對 image 或 template 縮放掃描。
4. 呼叫 `cv2.matchTemplate(..., cv2.TM_CCOEFF_NORMED)`。
5. 以 `threshold` 過濾 → NMS (IoU ≥ `nms_iou`) → 取前 `max_results`。
6. 將 match 中心點反算回原圖座標，組出 `MatchResult`。

### 5.3 註冊機制
```python
# backend/core/algorithms/registry.py
_REGISTRY: dict[str, AbstractMatcher] = {}

def register(matcher: AbstractMatcher) -> None: ...
def get(algorithm_id: str) -> AbstractMatcher: ...
def list_all() -> list[AbstractMatcher]: ...
```
新增演算法時僅需：
1. 繼承 `AbstractMatcher` 並實作 `match()`
2. 在 `backend/core/algorithms/__init__.py` 呼叫 `register(...)`
3. 前端透過 `/api/algorithms` 自動取得選項

---

## 6. 資料流 (Happy Path)

1. 使用者點「Upload」選擇圖片 → 前端載入 → 顯示於 Canvas。
2. 使用者選擇「Draw Rect」或「Draw Rotated Rect」→ 在影像上拖拉出 template → Pattern Table 新增一列 (role=template)。
3. 使用者拖曳 / 縮放 / 旋轉 template 調整至所需區域。
4. 按「Quick Mark」→ 前端將 `{ filename, data_base64, template(4 corners), algorithm, params }` POST `/api/match`。
5. 後端：
   a. 以 `image_io.decode_base64` 還原為 `np.ndarray`。
   b. 查 `registry.get(algorithm)` → 呼叫 `matcher.match(...)`。
   c. 回傳 `matches[]`。
6. 前端將 matches 以 role=match 加入 `AppState.patterns` → Canvas 繪製 + Table 更新。
7. 使用者以滑鼠 + `d` 鍵刪除不需要的 match。
8. 按「Save JSON」→ 前端以 `Blob` 建立檔案並觸發下載。

---

## 7. 非功能需求 (NFR)

| 類別 | 目標 |
|------|------|
| 效能 | 1920×1080 影像 + 120×80 template + 單一尺度單一角度 → 後端 matching ≤ 500 ms (一般筆電 CPU) |
| 傳輸 | base64 圖片上限 20 MB；超過回 413 |
| 相容性 | Chrome/Edge/Firefox 最新版；不支援 IE |
| 可維護性 | 演算法新增 ≤ 1 個檔案 + 1 行註冊 |
| 記錄 | 後端以 `logging` INFO 記錄 request id、演算法、耗時；ERROR 記錄 stack trace |
| 安全 | 僅接受 `image/png`、`image/jpeg`；後端對 base64 長度與 magic bytes 做驗證 |
| 國際化 | UI 以英文為主，欄位標籤預留 i18n 字典 |

---

## 8. 錯誤處理 & 邊界情境

- **Template 超出影像範圍**：前端繪製時 clamp；後端再驗一次，超界回 400。
- **Template 過小 (<8×8 px)**：前端禁用 Quick Mark，顯示提示。
- **Match 為 0**：回傳空陣列，UI 顯示「No matches found」。
- **角度為負 / 大於 360**：正規化至 `[-180, 180)`。
- **重複 pattern**：同中心 ± 1 px 且角度差 < 1° 視為重複，前端 dedupe。
- **圖片 EXIF 旋轉**：上傳時先以前端 canvas 正規化方向，避免後端座標錯位。

---

## 9. 驗收條件 (Acceptance Criteria)

對應 `1st.md` 八項功能，需皆可以下列情境驗證：

1. ✅ 能透過 Upload 按鈕載入 `test_image/image_01.png`，影像正確呈現。
2. ✅ 以「Draw Rotated Rect」繪製 30° 傾斜矩形，可拖曳、8 向縮放、繞中心旋轉。
3. ✅ Pattern Table 出現 1 列 template，欄位數值隨互動即時更新。
4. ✅ 按「Quick Mark」送出；DevTools 可見 POST `/api/match` payload 包含 base64 與四點座標。
5. ✅ 後端正確回傳至少 1 個 match；切換演算法 (mock 第二個 matcher) 僅需改 dropdown。
6. ✅ Canvas 上出現綠色 match 框，Table 新增 match 列並顯示 score。
7. ✅ 點擊某個 match → 按 `d` → 該框與列同時消失。
8. ✅ 按「Save JSON」下載檔案，內容符合 §3.6 的 schema 並可被重新載入還原 pattern。

---

## 10. 後續擴充路線 (Roadmap, 非 v0.1 範圍)

- **v0.2**：支援多邊形 / 橢圓 pattern；加入 SIFT/ORB 特徵比對 matcher。
- **v0.3**：Project 概念 — 多張圖片批次 matching、結果匯出為 COCO / YOLO 格式。
- **v0.4**：後端切換為 worker queue (RQ/Celery)，支援長時任務與進度條。
- **v0.5**：WebSocket 即時進度推送；支援拖曳 JSON 匯入還原標註。
- **v1.0**：使用者帳號、雲端儲存、審核流程。

---

## 11. 開發里程碑建議 (v0.1)

| 週次 | 任務 |
|------|------|
| W1 | 後端骨架 (FastAPI、/healthz、AbstractMatcher、CCoeffNormedMatcher)；單元測試 |
| W2 | 前端骨架 (Layout、Canvas 繪製矩形、Pattern Table)；前後端 join |
| W3 | 旋轉矩形互動 (縮放 handle、旋轉 handle、鍵盤刪除)；Quick Mark 串接 |
| W4 | Save/Load JSON、錯誤處理、NFR 優化、驗收測試、README |

---

_本文件為 v0.1 規劃草案，後續若有需求變更，請於 `specs/` 目錄新增 `002_*.md` 追加修訂版本，不直接覆寫本檔。_
