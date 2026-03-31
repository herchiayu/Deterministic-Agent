# 多網站整合指南

本文件說明如何將使用 DEVELOPER_SPEC 架構開發的子網站整合進主站系統。

子網站**不處理登入**，所有認證統一透過主站 `[SERVER_IP]:5000` 進行。

---

## 1. 系統架構概覽

```
Deterministic-Agent/                   ← 主專案根目錄（伺服器上）
├── .env                               ← 共用環境變數（SECRET_KEY 等）
├── .env.example                       ← 環境變數範本（加入版控）
├── run_server.bat                     ← 一鍵啟動所有站點
│
├── backend/                           ← 主站後端 (port 5000)
│   ├── config/                        ← 設定與權限控制
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── access_control.csv         ← 主站白名單
│   │   └── app_registry.csv           ← 網站清單註冊表
│   ├── resources/                     ← 程式靜態資源（唯讀）
│   ├── models/                        ← 大型模型檔案（唯讀）
│   ├── data/                          ← 使用者產生的持久性資料（讀寫）
│   ├── flask_session/                 ← Session 暫存檔
│   ├── server.py
│   └── requirements.txt
│
├── frontend/                          ← 主站前端（含側邊欄）
│
└── Websites/                          ← 子網站集合
    ├── Web-Template/  (port 5001)     ← 子站範例
    │   ├── backend/
    │   │   ├── config/
    │   │   │   ├── __init__.py
    │   │   │   ├── config.py          ← 設定 SERVER_IP 與 PORT
    │   │   │   └── access_control.csv ← 子站白名單
    │   │   ├── server.py              ← 不用改
    │   │   └── requirements.txt
    │   └── frontend/
    │
    ├── Project-B/     (port 5002)     ← 子站 B（未來）
    └── ...
```

### 權限模型

```
第一層：主站 access_control.csv  →  控制「誰能登入整個系統」
第二層：子站 access_control.csv  →  控制「誰能使用這個子站」（空白名單 = 所有已登入使用者皆可進入）
```

### 單一登入原理

- 所有站點共用根目錄的 `.env`（取得相同的 `SECRET_KEY`）
- 子站的 `SESSION_FILE_DIR` 指向主站的 `backend/flask_session/`
- 瀏覽器 Cookie 不區分 port，主站設定的 session cookie 會自動送往子站
- 子站不處理登入，未登入時導回 `http://[SERVER_IP]:5000`

---

## 2. 整合新的子網站（Step by Step）

假設同事交給你一個叫 `My-New-App` 的專案，分配 port `5002`。

### Step 1：放入 Websites 資料夾

將專案資料夾複製到伺服器的 `Websites/` 下。

### Step 2：修改 `config/config.py`（唯一需要改的檔案）

只需確認兩個值：

```python
PORT = 5002                              # ← 確認不與其他站衝突
SERVER_IP = '192.168.x.x'               # ← 改為實際伺服器 IP
```

完整的 `config/config.py` 範例：

```python
from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).parent
BACKEND_DIR = CONFIG_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / 'frontend'
RESOURCE_DIR = BACKEND_DIR / 'resources'
MODEL_DIR = BACKEND_DIR / 'models'
DATA_DIR = BACKEND_DIR / 'data'

# 主專案根目錄（子站位於 Websites/ 下）
MAIN_PROJECT_ROOT = PROJECT_ROOT.parent.parent
load_dotenv(MAIN_PROJECT_ROOT / '.env')

HOST = '0.0.0.0'
PORT = 5002                              # ← 指定 port
DEBUG = True

# 主站伺服器位址（用於未登入時導回主站）
SERVER_IP = '192.168.x.x'               # ← 伺服器 IP
MAIN_SITE_PORT = 5000

SECRET_KEY = os.environ.get('SECRET_KEY')
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = MAIN_PROJECT_ROOT / 'backend' / 'flask_session'
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

ACCESS_CONTROL_CSV = CONFIG_DIR / 'access_control.csv'
ACCOUNT_SYSTEM_URL = 'http://localhost:9999'
```

**`server.py` 完全不用改。**

### Step 3：設定子站白名單

編輯 `Websites/My-New-App/backend/config/access_control.csv`：

```csv
Username
Herch
Dennis
```

留空（只有標題行）或刪除檔案 = 所有已登入使用者皆可進入。

### Step 4：註冊到主站

在主站的 `backend/config/app_registry.csv` 加一行：

```csv
Name,Port,Description
Web-Template,5001,網頁模板範例
My-New-App,5002,我的新應用
```

### Step 5：安裝相依套件

```bash
pip install -r Websites/My-New-App/backend/requirements.txt
```

確保 `requirements.txt` 中包含 `python-dotenv`。

### 完成

重啟 `run_server.bat` 即可，主站側邊欄會自動顯示新網站。

---

## 3. 整合檢查清單

| # | 檢查項目 | ✓ |
|---|---------|---|
| 1 | 子站資料夾已放入 `Websites/` | |
| 2 | `config/config.py`：`SERVER_IP` 已設為伺服器 IP | |
| 3 | `config/config.py`：`PORT` 不與其他站衝突 | |
| 4 | `config/access_control.csv`：已設定子站白名單（或留空允許所有人） | |
| 5 | `backend/config/app_registry.csv`：已註冊到主站 | |
| 6 | `requirements.txt`：已包含 `python-dotenv` 並安裝 | |

---

## 4. Port 分配表

| 站點 | Port | 說明 |
|------|------|------|
| 帳號系統 | 9999 | 統一帳號驗證服務 |
| 主站（AI 聊天助手）| 5000 | 入口站，管理側邊欄與登入 |
| Web-Template | 5001 | 網頁模板範例 |
| （預留）| 5002+ | 未來新增的子站 |
