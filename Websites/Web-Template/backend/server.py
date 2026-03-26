from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
from flask_session import Session
from functools import wraps
import csv
import requests
from config import *

app = Flask(__name__)
CORS(app)

app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = SESSION_TYPE
app.config['SESSION_FILE_DIR'] = str(SESSION_FILE_DIR)
app.config['PERMANENT_SESSION_LIFETIME'] = PERMANENT_SESSION_LIFETIME
Session(app)

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================
# 靜態資源路由
# ============================================================

@app.route('/static/css/<path:filename>')
def css_files(filename):
    return send_from_directory(FRONTEND_DIR / 'css', filename)


@app.route('/static/js/<path:filename>')
def js_files(filename):
    return send_from_directory(FRONTEND_DIR / 'js', filename)


@app.route('/static/images/<path:filename>')
def image_files(filename):
    return send_from_directory(FRONTEND_DIR / 'images', filename)


# ============================================================
# 帳號系統整合
# ============================================================

def verify_user(username: str, password: str) -> dict | None:
    """向帳號系統驗證使用者"""
    try:
        response = requests.post(f'{ACCOUNT_SYSTEM_URL}/api/verify',
                                 json={'username': username, 'password': password}, timeout=5)
        data = response.json()
        return data if data.get('success') else None
    except:
        return None


def load_whitelist():
    """載入白名單，返回 set 或 None（允許所有人）"""
    if not ACCESS_CONTROL_CSV.exists():
        return None
    whitelist = set()
    with open(ACCESS_CONTROL_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if username := row.get('Username', '').strip():
                whitelist.add(username)
    return whitelist


# ============================================================
# 裝飾器
# ============================================================

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


# ============================================================
# 頁面路由
# ============================================================

@app.route('/')
def index():
    return redirect('/home') if 'user_id' in session else send_from_directory(FRONTEND_DIR, 'login.html')


@app.route('/home')
@page_login_required
def home():
    return send_from_directory(FRONTEND_DIR, 'home.html')


# ============================================================
# API 路由
# ============================================================

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


# ============================================================
# 啟動伺服器
# ============================================================

if __name__ == '__main__':
    import os
    print(f"{Path(__file__).parent.parent.name}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
