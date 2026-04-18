# 建立一個 Web 前後端

## 前端 (static)
### 基本的 html js css 架構，可以使用第三方js 但不要大量使用需要 build 的套件
### 切分 .html .js .css 讓整體架構好管理


## 後端 (backend)
Python 3.11 FastAPI + FILES + opencv 


## 基本功能系列
1. 可以在前端上傳一張圖片處理
2. 使用者可以先標記一個想要找尋的 pattern  (先支援矩形的 與斜的矩形，未來再支援其他的方式) ，標記後必須可以拖曳放大縮小，也要可以再中心點旋轉
3. 畫面上需有一個 table 可以詳細說明現在 template pattern 的位置，並且也留下將來 偵測的 pattern 的位置資訊
4. 按下 "快速標記" 按鈕後，前端會把圖片與 pattern 的位置資訊傳給後端
     a. 圖片的資訊包含 filename 與 base64 編碼的圖片資料
     b. pattern 的位置資訊包含 pattern x1,y1,x2,y2,x3,y3,x4,y4的矩形座標
5. 後端會使用 opencv 的 template matching 功能找尋圖片中符合 pattern 的位置，並回傳給前端
    a. 演算法封裝必須符合隨是可以替換相關的演算法(請幫我詳細的封裝介面 圖形filename 與 / pattern x1,y1,x2,y2,x3,y3,x4,y4的矩形)
6. 前端會在圖片上標記出找到的 pattern 位置
7. 使用者可以點選想刪除的 pattern 的位置,按下 d 鍵刪除該 pattern 的位置
8. 按下 save 按鈕可以 download 一個 json 檔案，裡面包含圖片的 filename 與 pattern 的位置資訊


