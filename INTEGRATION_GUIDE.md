# 子網站整合操作手冊（AI 指令版）

本文件用途：指導 AI 將開發者依 `DEVELOPER_SPEC.md` 建立的獨立專案，轉換為可掛載至主站（port 9998）的子網站。

---

## 前置知識

### 主專案目錄結構

```
Deterministic-Agent/                     ← 主專案根目錄
├── .env                                 ← 共用環境變數（SECRET_KEY 等）
├── run_server.bat                       ← 一鍵啟動所有站點
├── backend/                             ← 主站後端 (port 9998)
│   └── config/
│       ├── config.py
│       ├── access_control.csv           ← 主站白名單
│       └── app_registry.csv             ← 子網站註冊表
├── frontend/                            ← 主站前端
└── Websites/                            ← 所有子網站放這裡
    ├── Web-Template/  (port 5001)
    ├── Web-Template-2/ (port 5002)
    └── ...
```

### 開發者交付的原始專案結構（依 DEVELOPER_SPEC 建立）

```
Developer-Project/
├── .env                                 ← 開發者自己的環境變數
├── .env.example
├── backend/
│   ├── config/
│   │   ├── __init__.py                  ← 空檔案
│   │   ├── config.py                    ← ★ 需要改
│   │   └── access_control.csv
│   ├── resources/
│   ├── models/
│   ├── data/
│   ├── flask_session/                   ← 可刪除（整合後用主站的）
│   ├── server.py                        ← ★ 需要改
│   └── requirements.txt                 ← ★ 需要確認
├── frontend/
│   ├── login.html                       ← ★ 需要刪除
│   ├── home.html                        ← ★ 需要改
│   ├── css/
│   │   ├── login.css                    ← ★ 需要刪除
│   │   └── home.css
│   ├── js/
│   │   ├── login.js                     ← ★ 需要刪除
│   │   └── home.js                      ← ★ 需要改
│   └── images/
├── run_server.bat                       ← 不需要帶入
├── initiate_project.bat                 ← 不需要帶入
└── finalize_project.bat                 ← 不需要帶入
```

### 單一登入原理

- 所有站點共用根目錄 `.env` 中的 `SECRET_KEY`
- 子站的 `SESSION_FILE_DIR` 指向主站的 `backend/flask_session/`
- 瀏覽器 Cookie 不區分 port，主站設的 session cookie 會自動送往子站
- 子站不處理登入，未登入時導回主站 `http://[SERVER_IP]:9998`

### 權限模型

```
第一層：主站 access_control.csv → 控制「誰能登入整個系統」
第二層：子站 access_control.csv → 控制「誰能使用這個子站」（空白名單 = 所有已登入使用者皆可進入）
```

---

## 整合步驟

以下假設：
- 開發者交付的專案資料夾名稱為 `{APP_NAME}`
- 分配的 port 為 `{PORT}`

### 步驟 1：複製專案到 Websites 資料夾

將 `{APP_NAME}` 資料夾複製到 `Websites/` 下。

結果路徑：`Deterministic-Agent/Websites/{APP_NAME}/`

### 步驟 2：刪除不需要的檔案

刪除以下檔案（子站不處理登入，這些由主站負責）：

```
刪除：frontend/login.html
刪除：frontend/css/login.css
刪除：frontend/js/login.js
刪除：backend/flask_session/（整個資料夾，如存在）
刪除：.env（如存在；子站使用主專案根目錄的 .env）
刪除：.env.example（如存在）
刪除：run_server.bat（如存在）
刪除：initiate_project.bat（如存在）
刪除：finalize_project.bat（如存在）
刪除：.venv/（如存在）
刪除：.git/（如存在）
刪除：.gitignore（如存在）
```

### 步驟 3：改寫 `backend/config/config.py`

**整份替換**為以下內容（保留開發者自訂的變數）：

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
PORT = {PORT}                                    # ← 替換為實際 port
DEBUG = True

# 主站伺服器位址（用於未登入時導回主站）
SERVER_IP = 'localhost'                           # ← 部署時改為實際伺服器 IP
MAIN_SITE_PORT = 9998

SECRET_KEY = os.environ.get('SECRET_KEY')
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = MAIN_PROJECT_ROOT / 'backend' / 'flask_session'
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

ACCESS_CONTROL_CSV = CONFIG_DIR / 'access_control.csv'
ACCOUNT_SYSTEM_URL = f'http://{SERVER_IP}:9999'

# ── 以下保留開發者自訂的變數 ──
# 例如：
# GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
# CUSTOM_SETTING = 'value'
```

#### 改動對照表（與開發者原始版本比較）

| 項目 | 開發者原始值 | 整合後的值 | 說明 |
|------|-------------|-----------|------|
| `load_dotenv()` 路徑 | `PROJECT_ROOT / '.env'` | `MAIN_PROJECT_ROOT / '.env'` | 改讀主專案根目錄的 .env |
| `PORT` | `5000`（或其他） | `{PORT}` | 不與其他站衝突 |
| 新增 `MAIN_PROJECT_ROOT` | 不存在 | `PROJECT_ROOT.parent.parent` | 指向 `Deterministic-Agent/` |
| 新增 `SERVER_IP` | 不存在 | `'localhost'` | 主站 IP |
| 新增 `MAIN_SITE_PORT` | 不存在 | `9998` | 主站 port |
| `SESSION_FILE_DIR` | `BACKEND_DIR / 'flask_session'` | `MAIN_PROJECT_ROOT / 'backend' / 'flask_session'` | 指向主站的 session 目錄以實現 SSO |
| `ACCOUNT_SYSTEM_URL` | `'http://localhost:9999'` | `f'http://{SERVER_IP}:9999'` | 使用實際 IP，跨機器可存取 |
| 刪除 `APP_REGISTRY_CSV` | 可能存在 | 刪除 | 子站不需要管理網站清單 |

#### 開發者自訂變數處理規則

若開發者的 `config.py` 中有上表以外的額外變數（例如 API Key、模型設定等），**必須保留**並附加在檔案末尾。如果這些變數使用 `os.environ.get()`，確保對應的環境變數名稱已新增到主專案根目錄的 `.env` 中。

### 步驟 4：改寫 `backend/server.py`

需要進行以下修改：

#### 4a. 移除登入相關程式碼

**刪除**以下函數與路由（子站不處理登入，認證由主站負責）：

```
刪除：verify_user() 函數
刪除：@app.route('/api/login', ...) 路由
刪除：import requests（如果只被 verify_user 使用）
```

#### 4b. 移除 session 清理程式碼

**刪除**以下區塊（session 由主站管理）：

```python
# 刪除這段：
cfg.SESSION_FILE_DIR.mkdir(exist_ok=True)

# 刪除這段：
def cleanup_all_sessions():
    if cfg.SESSION_FILE_DIR.exists():
        for f in cfg.SESSION_FILE_DIR.glob('*'):
            if f.is_file():
                f.unlink()

cleanup_all_sessions()
```

#### 4c. 新增主站導回 URL

在 `Session(app)` 之後加入：

```python
# 主站位址（未登入時導回主站登入）
MAIN_SITE_URL = f'http://{cfg.SERVER_IP}:{cfg.MAIN_SITE_PORT}'
```

#### 4d. 新增白名單檢查函數

保留原本的 `load_whitelist()`，並新增 `check_whitelist()`：

```python
def load_whitelist():
    """載入白名單，返回 set 或 None（允許所有人）"""
    if not cfg.ACCESS_CONTROL_CSV.exists():
        return None
    whitelist = set()
    with open(cfg.ACCESS_CONTROL_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if username := row.get('Username', '').strip():
                whitelist.add(username)
    return whitelist if whitelist else None


def check_whitelist(username):
    """檢查使用者是否在白名單中，無白名單則允許所有人"""
    whitelist = load_whitelist()
    if whitelist is None:
        return True
    return username in whitelist
```

#### 4e. 新增無權限頁面渲染函數

```python
def _render_no_access():
    """渲染無權限頁面"""
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
```

#### 4f. 改寫裝飾器

將原本的裝飾器替換為子站版本（加入白名單檢查 + 未登入導回主站）：

```python
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
            return redirect(MAIN_SITE_URL)
        if not check_whitelist(session.get('username', '')):
            return _render_no_access()
        return f(*args, **kwargs)
    return decorated
```

#### 4g. 改寫根路由 `/`

```python
# 原本（開發者版本）：
@app.route('/')
def index():
    return redirect('/home') if 'user_id' in session else send_from_directory(cfg.FRONTEND_DIR, 'login.html')

# 改為（子站版本）：
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(MAIN_SITE_URL)
    if not check_whitelist(session.get('username', '')):
        return _render_no_access()
    return redirect('/home')
```

#### 4h. 修改 logout 路由

確保 logout 路由存在且不包含主站特有的邏輯（例如清除 Gemini chat session）：

```python
@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    session.modified = True
    return jsonify({'message': '登出成功'}), 200
```

#### server.py 完整範本（供參考）

以下是整合後的 server.py 基本骨架，開發者的業務 API 路由應保留在對應區塊中：

```python
from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
from flask_session import Session
from functools import wraps
import csv
from config import config as cfg
# ← 保留開發者的其他 import（但移除 requests 如果只被 verify_user 使用）

app = Flask(__name__)
CORS(app)

app.secret_key = cfg.SECRET_KEY
app.config['SESSION_TYPE'] = cfg.SESSION_TYPE
app.config['SESSION_FILE_DIR'] = str(cfg.SESSION_FILE_DIR)
app.config['PERMANENT_SESSION_LIFETIME'] = cfg.PERMANENT_SESSION_LIFETIME
Session(app)

cfg.RESOURCE_DIR.mkdir(exist_ok=True)
cfg.MODEL_DIR.mkdir(exist_ok=True)
cfg.DATA_DIR.mkdir(exist_ok=True)
# 注意：不要 mkdir SESSION_FILE_DIR，也不要 cleanup_all_sessions()

# 主站位址（未登入時導回主站登入）
MAIN_SITE_URL = f'http://{cfg.SERVER_IP}:{cfg.MAIN_SITE_PORT}'

# ← 保留開發者的初始化程式碼（例如 Gemini client、資料庫連線等）


# ============================================================
# 白名單
# ============================================================

def load_whitelist():
    """載入白名單，返回 set 或 None（允許所有人）"""
    if not cfg.ACCESS_CONTROL_CSV.exists():
        return None
    whitelist = set()
    with open(cfg.ACCESS_CONTROL_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if username := row.get('Username', '').strip():
                whitelist.add(username)
    return whitelist if whitelist else None


def check_whitelist(username):
    """檢查使用者是否在白名單中，無白名單則允許所有人"""
    whitelist = load_whitelist()
    if whitelist is None:
        return True
    return username in whitelist


# ============================================================
# 裝飾器
# ============================================================

def _render_no_access():
    """渲染無權限頁面"""
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
            return redirect(MAIN_SITE_URL)
        if not check_whitelist(session.get('username', '')):
            return _render_no_access()
        return f(*args, **kwargs)
    return decorated


# ============================================================
# 靜態資源路由
# ============================================================

@app.route('/static/css/<path:filename>')
def css_files(filename):
    return send_from_directory(cfg.FRONTEND_DIR / 'css', filename)


@app.route('/static/js/<path:filename>')
def js_files(filename):
    return send_from_directory(cfg.FRONTEND_DIR / 'js', filename)


@app.route('/static/images/<path:filename>')
def image_files(filename):
    return send_from_directory(cfg.FRONTEND_DIR / 'images', filename)


# ============================================================
# 頁面路由
# ============================================================

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(MAIN_SITE_URL)
    if not check_whitelist(session.get('username', '')):
        return _render_no_access()
    return redirect('/home')


@app.route('/home')
@page_login_required
def home():
    return send_from_directory(cfg.FRONTEND_DIR, 'home.html')

# ← 保留開發者的其他頁面路由（全部加上 @page_login_required）


# ============================================================
# API 路由
# ============================================================

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    session.modified = True
    return jsonify({'message': '登出成功'}), 200


@app.route('/api/check-auth')
@login_required
def check_auth():
    return jsonify({'authenticated': True, 'username': session['username']}), 200

# ← 保留開發者的其他 API 路由（全部加上 @login_required）
# ← 注意：刪除 /api/login 路由（子站不處理登入）


# ============================================================
# 啟動伺服器
# ============================================================

if __name__ == '__main__':
    print(f"{cfg.PROJECT_ROOT.name}")
    app.run(host=cfg.HOST, port=cfg.PORT, debug=cfg.DEBUG)
```

### 步驟 5：修改前端檔案

#### 5a. 刪除登入相關檔案

已在步驟 2 刪除。

#### 5b. 修改所有頁面 JS 中的 `window.location.replace('/')`

將前端 JS 中登出後的跳轉從 `/` 改為主站 URL，以便跳回主站首頁而非子站根路由（子站根路由會再導回主站，但直接跳主站更直覺）：

**搜尋規則**：在所有 `frontend/js/*.js` 檔案中，找到 `logout()` 函數中的 `window.location.replace('/')` 並保持不動（因為子站 `/` 路由已設定導回主站，所以不改也可以正常運作）。

> 此步驟為可選。不修改也能正常運作，因為子站的 `/` 路由已會導回主站。

#### 5c. 修改 home.html 及其他頁面的 HTML

移除任何引用 `login.css` 或 `login.js` 的標籤（通常不會出現在 home.html 中，但仍需確認）。

### 步驟 6：處理 requirements.txt

確認 `backend/requirements.txt` 包含 `python-dotenv`。

**檢查方式**：在檔案中搜尋 `python-dotenv`，若不存在則新增一行 `python-dotenv`。

另外，如果開發者的 `requirements.txt` 中包含 `requests` 套件，且該套件在 `server.py` 中已因移除 `verify_user()` 而不再被使用，**不需要主動移除**（留著無害）。

### 步驟 7：設定子站白名單

編輯 `Websites/{APP_NAME}/backend/config/access_control.csv`：

```csv
Username
Herch
Dennis
```

- 只保留標題行 `Username`（無資料行）= 所有已登入使用者皆可進入
- 新增使用者名稱 = 僅白名單中的使用者可進入

### 步驟 8：在主站 app_registry.csv 註冊

在 `backend/config/app_registry.csv` 新增一行：

```csv
{APP_NAME},{PORT},{DESCRIPTION}
```

**注意**：不要覆蓋既有的行，僅在末尾新增。

### 步驟 9：處理開發者自訂的環境變數

如果開發者的 `.env` 或 `.env.example` 中有自訂的環境變數（例如 `GEMINI_API_KEY`、`OPENAI_API_KEY` 等），需要將這些變數的值新增到主專案根目錄的 `.env` 檔案中。

### 步驟 10：安裝相依套件

執行：
```bash
pip install -r Websites/{APP_NAME}/backend/requirements.txt
```

---

## 快速檢查清單

| # | 項目 | 確認 |
|---|------|------|
| 1 | 子站資料夾已放入 `Websites/` | |
| 2 | `frontend/login.html`、`login.css`、`login.js` 已刪除 | |
| 3 | `backend/flask_session/` 已刪除 | |
| 4 | `.env`、`.env.example`、`run_server.bat` 等根目錄檔案已刪除 | |
| 5 | `config/config.py`：`MAIN_PROJECT_ROOT` 已加入 | |
| 6 | `config/config.py`：`load_dotenv` 指向 `MAIN_PROJECT_ROOT / '.env'` | |
| 7 | `config/config.py`：`PORT` 設為不衝突的值 | |
| 8 | `config/config.py`：`SERVER_IP` 設為 `localhost` | |
| 9 | `config/config.py`：`MAIN_SITE_PORT` 設為 `9998` | |
| 10 | `config/config.py`：`SESSION_FILE_DIR` 指向主站的 `flask_session` | |
| 11 | `config/config.py`：`ACCOUNT_SYSTEM_URL` 使用 `SERVER_IP` | |
| 12 | `config/config.py`：開發者自訂變數已保留 | |
| 13 | `server.py`：`verify_user()` 已刪除 | |
| 14 | `server.py`：`/api/login` 路由已刪除 | |
| 15 | `server.py`：`cleanup_all_sessions()` 已刪除 | |
| 16 | `server.py`：`SESSION_FILE_DIR.mkdir` 已刪除 | |
| 17 | `server.py`：`MAIN_SITE_URL` 已加入 | |
| 18 | `server.py`：`check_whitelist()` 已加入 | |
| 19 | `server.py`：`_render_no_access()` 已加入 | |
| 20 | `server.py`：裝飾器已改為子站版本（含白名單檢查） | |
| 21 | `server.py`：根路由 `/` 已改為導回主站 | |
| 22 | `server.py`：開發者的業務 API 路由已保留且加上 `@login_required` | |
| 23 | `server.py`：開發者的頁面路由已保留且加上 `@page_login_required` | |
| 24 | `requirements.txt`：包含 `python-dotenv` | |
| 25 | `access_control.csv`：已設定子站白名單 | |
| 26 | 主站 `app_registry.csv`：已註冊新子站 | |
| 27 | 主專案 `.env`：已加入開發者需要的環境變數 | |
| 28 | 相依套件已安裝 | |

---

## Port 分配表（目前已使用）

| 站點 | Port | 說明 |
|------|------|------|
| 帳號系統 | 9999 | 統一帳號驗證服務 |
| 主站 | 9998 | 入口站，管理側邊欄與登入 |
| Web-Template | 5001 | 網頁模板範例 |
| Web-Template-2 | 5002 | 網頁模板範例 2 |
| Web-Template-3 | 5003 | 網頁模板範例 3 |

新增子站時，從下一個可用的 port 開始分配。

---

## 常見邊界情況

### 開發者有多個頁面（不只 home.html）

- 所有額外頁面路由都必須加上 `@page_login_required` 裝飾器
- 對應的 JS 檔案中 `pageshow` 事件的 `check-auth` 失敗時，應執行 `window.location.replace('/')`（與 home.js 相同邏輯）

### 開發者使用了 `requests` 套件做其他用途

- 僅刪除 `verify_user()` 函數，**不要移除** `import requests`
- 判斷方式：搜尋整個 `server.py`，如果 `requests` 只在 `verify_user()` 中使用，才移除 import

### 開發者有自訂的 logout 邏輯

- 保留開發者在 logout 中的額外清理邏輯（例如清除記憶體中的使用者資料）
- 只需確保最後有 `session.clear()` 和 `session.modified = True`

### 開發者的 server.py 使用 `use_reloader=False`

- 保持開發者的設定不變，不強制更改
