from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
from flask_session import Session
from functools import wraps
import csv
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

# 主站位址（未登入時導回主站登入）
MAIN_SITE_URL = f'http://{cfg.SERVER_IP}:{cfg.MAIN_SITE_PORT}'


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


# ============================================================
# 啟動伺服器
# ============================================================

if __name__ == '__main__':
    print(f"{cfg.PROJECT_ROOT.name}")
    app.run(host=cfg.HOST, port=cfg.PORT, debug=cfg.DEBUG)
