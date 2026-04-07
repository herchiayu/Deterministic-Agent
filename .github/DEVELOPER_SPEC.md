# IT&CE ME 前後端專案開發規範

IT&CE ME 部門前後端開發規範，包含架構、帳號系統整合、固定格式及網頁風格。

**帳號系統位址**: `http://localhost:9999`

---

## 1. 目錄結構

### 1.1 標準專案架構

```
project-root/
├── frontend/             # 前端資源
│   ├── css/              # 樣式檔案
│   ├── js/               # JavaScript 檔案
│   ├── images/           # 圖片資源
│   ├── login.html        # 登入頁面
│   └── home.html         # 首頁
│
├── backend/              # 後端服務
│   ├── config/           # 設定與權限控制
│   │   ├── __init__.py   # 套件識別檔（空檔案）
│   │   ├── config.py     # 設定檔
│   │   └── access_control.csv  # 白名單設定
│   ├── resources/        # 程式靜態資源（唯讀）
│   ├── models/           # 大型模型檔案（唯讀）
│   ├── data/             # 使用者產生的持久性資料（讀寫）
│   ├── utils/            # 工具函數
│   ├── flask_session/    # Session 暫存檔
│   ├── server.py         # 主伺服器程式
│   └── requirements.txt  # Python 相依性
│
├── .venv/                # 虛擬環境
├── .env                  # 環境變數（機敏資訊，不版控）
├── .env.example          # 環境變數範本（加入版控）
├── .gitignore            # Git 忽略清單
└── run_server.bat        # 啟動腳本
```

### 1.2 設定檔說明

**config/config.py** - 集中管理所有設定
**config/access_control.csv** - 使用者白名單（控制誰能登入）
**requirements.txt** - Python 套件清單

**環境變數規則**:

| 檔案 | 用途 | 版控 |
|------|------|------|
| `.env` | 存放實際的機敏值（SECRET_KEY、API Key） | X |
| `.env.example` | 列出所有需要的變數名稱，值留空或填範例 | O |

> **強制規定**：機敏資訊（金鑰、密碼、API Key）**禁止寫死在程式碼中**，必須透過 `.env` + `os.environ.get()` 讀取。

**.env.example 範本**:
```env
# Flask session 加密金鑰（必填）
SECRET_KEY=

# 其他 API Key（依專案需求新增）
# LLM_API_KEY=
```

**資料目錄規則**:

| 目錄 | 用途 | 版控 | 備份 |
|------|------|------|------|
| `backend/config/` | 設定檔與權限控制 | O | - |
| `backend/resources/` | 程式靜態資源（CSV 參考資料、範本、規則檔） | O | - |
| `backend/models/` | 大型模型檔案（.pt、.onnx、.pkl） | X | 需要 |
| `backend/data/` | 使用者產生的持久性資料（上傳檔案、知識庫文件） | X | 需要 |
| `backend/flask_session/` | Session 暫存（啟動時自動清除） | X | 不需要 |

---

## 2. 設計準則

### 2.1 前後端設計原則

**前端原則**:
- API 呼叫使用相對路徑 `/api/*`，不硬編碼 IP
- 邏輯封裝於類別或模組
- 處理載入狀態、錯誤訊息、使用者回饋

**後端原則**:
- 路徑使用 `pathlib.Path` 計算絕對路徑
- 設定集中於 `config.py`
- 伺服器綁定 `0.0.0.0` 支援區網存取
- 啟用 CORS

**config.py 範例**:
```python
from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).parent
BACKEND_DIR = CONFIG_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / '.env')

FRONTEND_DIR = PROJECT_ROOT / 'frontend'
RESOURCE_DIR = BACKEND_DIR / 'resources'
MODEL_DIR = BACKEND_DIR / 'models'
DATA_DIR = BACKEND_DIR / 'data'

HOST = '0.0.0.0'
PORT = 5000
DEBUG = True

SECRET_KEY = os.environ.get('SECRET_KEY')
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = BACKEND_DIR / 'flask_session'
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

ACCESS_CONTROL_CSV = CONFIG_DIR / 'access_control.csv'
ACCOUNT_SYSTEM_URL = 'http://localhost:9999'
```

**server.py 基本架構**:
```python
from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
from flask_session import Session
from functools import wraps
import csv
import requests
from config import config as cfg

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
cfg.SESSION_FILE_DIR.mkdir(exist_ok=True)

# 啟動時清除所有 session 檔案（必須在 Session(app) 之後執行）
def cleanup_all_sessions():
    if cfg.SESSION_FILE_DIR.exists():
        for f in cfg.SESSION_FILE_DIR.glob('*'):
            if f.is_file():
                f.unlink()

cleanup_all_sessions()

# 靜態資源路由
@app.route('/static/css/<path:filename>')
def css_files(filename):
    return send_from_directory(cfg.FRONTEND_DIR / 'css', filename)

@app.route('/static/js/<path:filename>')
def js_files(filename):
    return send_from_directory(cfg.FRONTEND_DIR / 'js', filename)

@app.route('/static/images/<path:filename>')
def image_files(filename):
    return send_from_directory(cfg.FRONTEND_DIR / 'images', filename)

# 裝飾器與路由（見下方章節）

if __name__ == '__main__':
    print(f"{cfg.PROJECT_ROOT.name}")
    app.run(host=cfg.HOST, port=cfg.PORT, debug=cfg.DEBUG)
```

### 2.2 帳號系統整合

**檢查服務**: `http://localhost:9999/api/status`

**API - POST /api/verify**

請求:
```json
{"username": "alice", "password": "pass123"}
```

回應:
```json
// 成功 200
{"success": true, "user_id": 1, "username": "alice"}
// 失敗 401
{"success": false, "error": "使用者名稱或密碼錯誤"}
```

**驗證函數**:
```python
def verify_user(username: str, password: str) -> dict | None:
    try:
        response = requests.post(f'{cfg.ACCOUNT_SYSTEM_URL}/api/verify',
                                json={'username': username, 'password': password}, timeout=5)
        data = response.json()
        return data if data.get('success') else None
    except:
        return None
```

### 2.3 權限控制

**白名單檔案**: `backend/config/access_control.csv`

```csv
Username
User01
User02
```

**載入函數**:
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
    return whitelist
```

**登入 API（整合驗證+白名單）**:
```python
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # 驗證帳密
    result = verify_user(username, password)
    if not result:
        return jsonify({'error': '帳號或密碼錯誤'}), 401
    
    # 檢查白名單
    whitelist = load_whitelist()
    if whitelist is not None and username not in whitelist:
        return jsonify({'error': '您沒有權限進入此系統'}), 403
    
    # 設定 session
    session['user_id'] = result['user_id']
    session['username'] = result['username']
    return jsonify({'message': '登入成功'}), 200
```

### 2.4 登入狀態管理

> `cleanup_all_sessions()` 已內嵌於 2.1 的 `server.py` 架構模板，**不可省略**。

**前後端雙重保護規則（必須同時實作）**:

| 情境 | 後端 | 前端 |
|------|------|------|
| 已登入訪問 `/`（登入頁）| `index()` redirect → `/home` | `login.js` 頁面載入時呼叫 `check-auth`，成功則跳 `/home` |
| 未登入訪問任何非登入頁面 | `@page_login_required` redirect → `/` | 每個頁面 JS 頁面載入時呼叫 `check-auth`，失敗則跳 `/` |

**前端驗證模板（每個非登入頁面 JS 必須包含）**:
```javascript
// 非登入頁面（如 home.js）：未登入則跳回 /
// 使用 pageshow 而非 DOMContentLoaded，以確保 bfcache 還原時也會執行
window.addEventListener('pageshow', async () => {
    const response = await fetch('/api/check-auth', {credentials: 'same-origin'});
    if (!response.ok) window.location.replace('/');
});

// 登入頁面（login.js）：已登入則跳回 /home
window.addEventListener('pageshow', async () => {
    const response = await fetch('/api/check-auth', {credentials: 'same-origin'});
    if (response.ok) window.location.replace('/home');
});
```

**裝飾器**:
```python
def login_required(f):
    """API路由：未登入返回 401"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '未登入'}), 401
        return f(*args, **kwargs)
    return decorated

def page_login_required(f):
    """頁面路由：未登入重導至 /"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated
```

**路由範例**:
```python
@app.route('/')
def index():
    return redirect('/home') if 'user_id' in session else send_from_directory(cfg.FRONTEND_DIR, 'login.html')

@app.route('/home')
@page_login_required
def home():
    return send_from_directory(cfg.FRONTEND_DIR, 'home.html')

@app.route('/api/check-auth')
@login_required
def check_auth():
    return jsonify({'authenticated': True, 'username': session['username']}), 200

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    session.modified = True  # 確保 cookie 被正確清除
    return jsonify({'message': '登出成功'}), 200
```

### 2.5 完整前端範例

**login.html**:
```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>登入</title>
    <link rel="stylesheet" href="/static/css/login.css">
</head>
<body>
    <div class="container">
        <h2>系統登入</h2>
        <input type="text" id="username" placeholder="使用者名稱">
        <input type="password" id="password" placeholder="密碼">
        <button class="primary-btn" onclick="login()">登入</button>
        <div id="message" class="message"></div>
    </div>
    <script src="/static/js/login.js"></script>
</body>
</html>
```

**login.js**:
```javascript
// 已登入則直接跳回 home
window.addEventListener('pageshow', async () => {
    const response = await fetch('/api/check-auth', {credentials: 'same-origin'});
    if (response.ok) window.location.replace('/home');
});

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        showMessage('請輸入使用者名稱和密碼', true);
        return;
    }
    
    const response = await fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    });
    
    const data = await response.json();
    if (response.ok) {
        window.location.replace('/home');
    } else {
        showMessage(data.error || '登入失敗', true);
    }
}

function showMessage(text, isError) {
    const msg = document.getElementById('message');
    msg.textContent = text;
    msg.className = 'message ' + (isError ? 'error' : 'success');
}
```

**home.html**:
```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>首頁</title>
    <link rel="stylesheet" href="/static/css/home.css">
</head>
<body>
    <div class="header">
        <h1>歡迎 <span id="username-display"></span></h1>
        <button onclick="logout()">登出</button>
    </div>
    <div class="container">
        <!-- 你的頁面內容 -->
    </div>
    <script src="/static/js/home.js"></script>
</body>
</html>
```

**home.js**:
```javascript
window.addEventListener('pageshow', async () => {
    const response = await fetch('/api/check-auth', {credentials: 'same-origin'});
    if (!response.ok) {
        window.location.replace('/');
    } else {
        const data = await response.json();
        document.getElementById('username-display').textContent = data.username;
    }
});

async function logout() {
    await fetch('/api/logout', {method: 'POST'});
    window.location.replace('/');
}
```

---

## 3. 固定格式

### 3.1 .gitignore

```gitignore
__pycache__/
.github/
venv/
.venv/
env/
ENV/
backend/models/
backend/data/
backend/flask_session/
.env
initiate_project.bat
finalize_project.bat
INSTRUCTIONS.md
INSTRUCTIONS.pdf
```

### 3.2 網頁風格

**色彩系統**:
- 主色: `#00ACBB`  |  輔助: `#2196F3`  |  成功: `#4CAF50`  |  錯誤: `#721c24`
- 背景: `#ffffff`  |  文字: `#333` / `#666`

**字體**:
```css
font-family: 'Segoe UI', 'Microsoft JhengHei', sans-serif;
```
大小: 標題 `1.7rem`, 正文 `1rem`, 小字 `0.875rem`

**容器**:
```css
.container {
    max-width: 400px;
    margin: 50px auto;
    padding: 30px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}
```

**按鈕**:
```css
button {
    width: 100%;
    padding: 12px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: opacity 0.3s;
}
.primary-btn { background: #00ACBB; color: white; }
button:hover { opacity: 0.9; }
```

**輸入框**:
```css
input {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
}
input:focus { border-color: #00ACBB; outline: none; }
```

**訊息提示**:
```css
.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
```

**間距/圓角**: 間距 `4px 8px 12px 24px 32px` | 圓角 按鈕`4px` 卡片`8px`

**響應式**:
```css
@media (max-width: 768px) {
    .container { padding: 0 16px; margin: 30px auto; }
}
```

## 常見問題

**帳號系統連線**
- 確認帳號系統是否啟動: `http://localhost:9999/api/status`
- 在自己電腦開發、帳號系統在別台機器: 修改 `config.py` 中的 `ACCOUNT_SYSTEM_URL = 'http://伺服器IP:9999'`
- 修改埠號: `config.py` 中修改 `PORT`

**登入 / 權限問題**
- 登入成功但被擋在頁面外（403）: 檢查 `backend/config/access_control.csv`，確認使用者名稱已加入白名單；只保留標題行 `Username`（無任何資料行）代表允許所有已登入使用者進入
- 帳號密碼正確但登入失敗: 先確認帳號系統可連線（見上方），再確認 `ACCOUNT_SYSTEM_URL` 指向正確的 IP

**Session 問題**
- 每次重啟 server 後必須重新登入: 這是設計行為，`cleanup_all_sessions()` 在啟動時會清除所有 session
- 登出後按返回鍵還能回到頁面: 前端必須使用 `pageshow` 事件執行 `check-auth`（見 2.4 節），而非 `DOMContentLoaded`
- Session 異常 / 無法保持登入: 確認 `.env` 中 `SECRET_KEY` 已設定且不為空

**靜態資源**
- CSS / JS / 圖片 404: 前端路徑需使用規定前綴 `/static/css/`、`/static/js/`、`/static/images/`

