# 多網站整合指南

本文件說明如何將使用 DEVELOPER_SPEC 架構開發的子網站整合進主站系統。

---

## 1. 系統架構概覽

```
Deterministic-Agent/                   ← 主專案根目錄
├── .env                               ← 共用環境變數（SECRET_KEY 等）
├── run_server.bat                     ← 一鍵啟動所有站點
│
├── backend/                           ← 主站後端 (port 5000)
│   ├── config.py
│   ├── server.py
│   └── data/
│       ├── access_control.csv         ← 主站白名單（控制誰能登入系統）
│       └── app_registry.csv           ← 網站清單註冊表
│
├── frontend/                          ← 主站前端（含側邊欄）
│
└── Websites/                          ← 子網站集合
    ├── Web-Template/  (port 5001)     ← 子站 A
    │   ├── backend/
    │   │   ├── config.py              ← 已改造：共用 .env 與 session
    │   │   ├── server.py              ← 已改造：白名單權限 + 導回主站
    │   │   └── data/
    │   │       └── access_control.csv ← 子站白名單（控制誰能用此子站）
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
- 子站不處理登入/登出，統一由主站管理

---

## 2. 整合新的子網站（Step by Step）

假設同事交給你一個叫 `My-New-App` 的專案，使用 DEVELOPER_SPEC 架構，分配 port `5002`。

### Step 1：放入 Websites 資料夾

```
將整個專案資料夾複製到 Websites/ 下：

Websites/
└── My-New-App/
    ├── backend/
    │   ├── config.py
    │   ├── server.py
    │   ├── requirements.txt
    │   └── data/
    │       └── access_control.csv
    └── frontend/
        ├── home.html
        ├── login.html
        ├── css/
        └── js/
```

### Step 2：修改子站 `config.py`

將原本的 `config.py` 改為以下內容（注意 3 個關鍵修改）：

```python
from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
MAIN_PROJECT_ROOT = PROJECT_ROOT.parent.parent            # ← 關鍵 1：定位主專案根目錄

# 載入主專案根目錄的 .env（共用 SECRET_KEY 以實現單一登入）
load_dotenv(MAIN_PROJECT_ROOT / '.env')                    # ← 關鍵 2：載入主站 .env

FRONTEND_DIR = PROJECT_ROOT / 'frontend'
DATA_DIR = BACKEND_DIR / 'data'
UPLOAD_DIR = BACKEND_DIR / 'uploads'

HOST = '0.0.0.0'
PORT = 5002                                                # ← 指定此子站的 port
DEBUG = True

SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = MAIN_PROJECT_ROOT / 'backend' / 'flask_session'  # ← 關鍵 3：指向主站 session 目錄
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

ACCESS_CONTROL_CSV = DATA_DIR / 'access_control.csv'
ACCOUNT_SYSTEM_URL = 'http://localhost:9999'
MAIN_SITE_PORT = 5000                                      # ← 主站 port（用於導回登入頁）
```

**與原版 config.py 的差異：**

| 項目 | 原版 | 整合版 |
|------|------|--------|
| `.env` 路徑 | `PROJECT_ROOT / '.env'` | `MAIN_PROJECT_ROOT / '.env'` |
| `SESSION_FILE_DIR` | `BACKEND_DIR / 'flask_session'` | `MAIN_PROJECT_ROOT / 'backend' / 'flask_session'` |
| `MAIN_SITE_PORT` | 無 | `5000` |
| `MAIN_PROJECT_ROOT` | 無 | `PROJECT_ROOT.parent.parent` |

### Step 3：修改子站 `server.py`

需要進行以下修改：

#### 3a. 移除不需要的部分

- 刪除 `cleanup_all_sessions()` 函數及其呼叫（避免清掉主站 session）
- 刪除 `verify_user()` 函數（子站不處理登入驗證）
- 刪除 `/api/login` 路由（登入統一由主站處理）
- 刪除 `/api/logout` 路由（登出統一由主站處理）
- 刪除 `import requests`（不再需要）
- 刪除 `SESSION_FILE_DIR.mkdir(exist_ok=True)`（由主站管理）

#### 3b. 修改白名單函數

```python
def load_whitelist():
    """載入白名單，返回 set 或 None（允許所有人）"""
    if not ACCESS_CONTROL_CSV.exists():
        return None
    whitelist = set()
    with open(ACCESS_CONTROL_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if username := row.get('Username', '').strip():
                whitelist.add(username)
    return whitelist if whitelist else None    # ← 空白名單也返回 None


def check_whitelist(username):
    """檢查使用者是否在白名單中，無白名單則允許所有人"""
    whitelist = load_whitelist()
    if whitelist is None:
        return True
    return username in whitelist
```

#### 3c. 修改裝飾器（加入白名單檢查 + 導回主站）

```python
# 在檔案開頭加入主站位址
MAIN_SITE_URL = f'http://{{}}:{MAIN_SITE_PORT}'

def login_required(f):
    """API路由：未登入返回 401，不在白名單返回 403"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '未登入'}), 401
        if not check_whitelist(session.get('username', '')):
            return jsonify({'error': '您沒有權限使用此應用'}), 403
        return f(*args, **kwargs)
    return decorated


def page_login_required(f):
    """頁面路由：未登入重導至主站，不在白名單顯示 403"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            main_url = MAIN_SITE_URL.format(request.host.split(':')[0])
            return redirect(main_url)
        if not check_whitelist(session.get('username', '')):
            return '''
            <!DOCTYPE html>
            <html lang="zh-TW">
            <head><meta charset="UTF-8"><title>無權限</title>
            <style>
                body { font-family: 'Segoe UI', 'Microsoft JhengHei', sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #f5f5f5; color: #333; }
                .container { text-align: center; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #721c24; margin-bottom: 12px; }
                p { color: #666; margin-bottom: 20px; }
                a { color: #00ACBB; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
            </head>
            <body><div class="container">
                <h1>⛔ 無權限</h1>
                <p>您的帳號沒有權限使用此應用，請聯繫管理員。</p>
                <a href="javascript:history.back()">← 返回上一頁</a>
            </div></body>
            </html>
            ''', 403
        return f(*args, **kwargs)
    return decorated
```

#### 3d. 修改頁面路由

```python
@app.route('/')
def index():
    if 'user_id' not in session:
        main_url = MAIN_SITE_URL.format(request.host.split(':')[0])
        return redirect(main_url)
    if not check_whitelist(session.get('username', '')):
        return redirect('/no-access')
    return redirect('/home')


@app.route('/no-access')
def no_access():
    if 'user_id' not in session:
        main_url = MAIN_SITE_URL.format(request.host.split(':')[0])
        return redirect(main_url)
    return '''（同 page_login_required 中的 403 頁面 HTML）''', 403
```

#### 3e. 修改 check-auth API（加入白名單檢查）

```python
@app.route('/api/check-auth')
@login_required          # ← 這個裝飾器已包含白名單檢查
def check_auth():
    return jsonify({'authenticated': True, 'username': session['username']}), 200
```

### Step 4：設定子站白名單

編輯 `Websites/My-New-App/backend/data/access_control.csv`：

```csv
Username
Herch
Dennis
```

留空（只有標題行）或刪除檔案 = 所有已登入使用者皆可進入。

### Step 5：註冊到主站

在主站的 `backend/data/app_registry.csv` 加一行：

```csv
Name,Port,Description
Web-Template,5001,網頁模板範例
My-New-App,5002,我的新應用
```

### Step 6：安裝相依套件

```bash
pip install -r Websites/My-New-App/backend/requirements.txt
```

確保子站的 `requirements.txt` 中包含 `python-dotenv`。

### 完成

重啟 `run_server.bat` 即可，主站側邊欄會自動顯示新網站。

---

## 3. 整合檢查清單

| # | 檢查項目 | ✓ |
|---|---------|---|
| 1 | 子站資料夾已放入 `Websites/` | |
| 2 | `config.py`：`.env` 路徑指向主專案根目錄 | |
| 3 | `config.py`：`SESSION_FILE_DIR` 指向主站 `backend/flask_session/` | |
| 4 | `config.py`：已設定 `MAIN_SITE_PORT = 5000` | |
| 5 | `config.py`：port 號不與其他站衝突 | |
| 6 | `server.py`：已移除 `cleanup_all_sessions()` | |
| 7 | `server.py`：已移除 `/api/login` 和 `/api/logout` | |
| 8 | `server.py`：裝飾器已加入白名單檢查 | |
| 9 | `server.py`：未登入時導回主站而非顯示登入頁 | |
| 10 | `access_control.csv`：已設定子站白名單 | |
| 11 | `app_registry.csv`：已註冊到主站 | |
| 12 | `requirements.txt`：已包含 `python-dotenv` 並安裝 | |

---

## 4. Port 分配表

| 站點 | Port | 說明 |
|------|------|------|
| 帳號系統 | 9999 | 統一帳號驗證服務 |
| 主站（AI 聊天助手）| 5000 | 入口站，管理側邊欄與登入 |
| Web-Template | 5001 | 網頁模板範例 |
| （預留）| 5002+ | 未來新增的子站 |
