# Stock Analysis Web

簡介
-	這是一個使用 Python (Flask) 構建的股票分析展示網站。旨在提供投資者一個直觀的視覺化儀表板，不僅能快速查詢台股與美股的個股資訊，還整合了技術線圖、籌碼動向與基本面數據。此外，系統內建 AI 智能解盤功能，能一鍵為使用者生成綜合分析報告。

核心功能
-   跨市場查詢：支援輸入台股代號（如 2330.TW）

    互動式 K 線圖表：直觀呈現過去一年的開高低收（OHLC）數據，並自動繪製 MA5、MA20、MA60 移動平均線。

    關鍵數據追蹤：

    顯示每股盈餘 (Trailing EPS) 與 EPS 年增率 (YoY)。

    表格化統整近 30 個交易日的「三大法人買賣超」（外資、投信、自營商）。

    AI 智能分析：結合大型語言模型，根據當前股價與各項指標，快速提供個股的綜合分析與趨勢參考。

技術架構
-	前端：HTML / CSS / JavaScript (搭配前端圖表套件)

    後端：Python 3.8+ / Flask

    靜態與動態路由：包含首頁 (index.html)、關於我們 (about.html) 等頁面渲染。

先決條件
-	Python 3.8 或更新

快速上手(local)
1. 建議建立虛擬環境並啟用：

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. 安裝相依套件：

```powershell
pip install -r requirements.txt
```

3. 啟動應用（專案使用 `app.py` 作為啟動點）：

```powershell
python app.py
```

4. 在瀏覽器開啟 http://127.0.0.1:5000

其他打開方式

- 我們的網站:https://gu-piao-fen-xi-wang-zhan.onrender.com From render


專案結構（重點檔案）
-	`app.py`：Flask 應用主程式
-	`requirements.txt`：Python 相依套件列表
-	`index.html`, `about.html`, `contact.html`：站點頁面（根目錄與 `templates/` 中都有樣板）
-	`static/`：靜態資源（CSS、JS、圖片等）