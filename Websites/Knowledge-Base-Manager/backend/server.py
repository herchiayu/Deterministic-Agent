from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
from flask_session import Session
from functools import wraps
from pathlib import Path
import requests as http_requests
from config import config as cfg

app = Flask(__name__)
CORS(app)

app.secret_key = cfg.SECRET_KEY
app.config['SESSION_TYPE'] = cfg.SESSION_TYPE
app.config['SESSION_FILE_DIR'] = str(cfg.SESSION_FILE_DIR)
app.config['PERMANENT_SESSION_LIFETIME'] = cfg.PERMANENT_SESSION_LIFETIME
Session(app)

# 主站位址
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
    """頁面路由：未登入重導至主站"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(MAIN_SITE_URL)
        return f(*args, **kwargs)
    return decorated


# ============================================================
# 頁面路由
# ============================================================

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(MAIN_SITE_URL)
    return redirect('/home')


@app.route('/home')
@page_login_required
def home():
    return send_from_directory(cfg.FRONTEND_DIR, 'home.html')


# ============================================================
# 認證 API
# ============================================================

@app.route('/api/check-auth')
@login_required
def check_auth():
    return jsonify({
        'authenticated': True,
        'username': session['username'],
        'write_groups': session.get('write_groups', []),
    }), 200


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    session.modified = True
    return jsonify({'message': '登出成功'}), 200


# ============================================================
# 知識庫重建（呼叫主站內部 API）
# ============================================================

def _trigger_rebuild(group):
    """通知主站重建指定群組的向量索引"""
    try:
        resp = http_requests.post(
            f'http://localhost:{cfg.MAIN_SITE_PORT}/api/internal/rebuild-group',
            json={'group': group},
            headers={'X-Internal-Secret': cfg.INTERNAL_SECRET},
            timeout=120,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f'[KB Manager] 重建觸發失敗: {e}')
        return False


# ============================================================
# 知識庫檔案管理 API
# ============================================================

def _get_user_dir(group, username):
    return cfg.KNOWLEDGE_BASE_DIR / group / username


def _validate_write_access(group, write_groups):
    """檢查使用者是否有該群組的寫入權限"""
    return group in write_groups


@app.route('/api/files')
@login_required
def list_files():
    """列出使用者在指定群組中自己的檔案"""
    username = session['username']
    write_groups = session.get('write_groups', [])
    group = request.args.get('group', '').strip()

    if not _validate_write_access(group, write_groups):
        return jsonify({'error': '無權限存取此群組'}), 403

    user_dir = _get_user_dir(group, username)
    files = []
    if user_dir.exists():
        for f in sorted(user_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in cfg.ALLOWED_EXTENSIONS:
                files.append({
                    'name': f.name,
                    'size': f.stat().st_size,
                })

    return jsonify({'files': files}), 200


@app.route('/api/file/content')
@login_required
def get_file_content():
    """讀取檔案內容"""
    username = session['username']
    write_groups = session.get('write_groups', [])
    group = request.args.get('group', '').strip()
    name = request.args.get('name', '').strip()

    if not _validate_write_access(group, write_groups):
        return jsonify({'error': '無權限'}), 403

    filepath = _get_user_dir(group, username) / name

    # 安全檢查
    try:
        filepath.resolve().relative_to(cfg.KNOWLEDGE_BASE_DIR.resolve())
    except ValueError:
        return jsonify({'error': '無效路徑'}), 400

    if not filepath.exists():
        return jsonify({'error': '檔案不存在'}), 404

    content = filepath.read_text(encoding='utf-8')
    return jsonify({'content': content, 'name': name, 'group': group}), 200


@app.route('/api/file', methods=['POST'])
@login_required
def save_file():
    """新增或更新檔案"""
    username = session['username']
    write_groups = session.get('write_groups', [])
    data = request.json or {}

    group = data.get('group', '').strip()
    name = data.get('name', '').strip()
    content = data.get('content', '')

    if not group or not name:
        return jsonify({'error': '缺少群組或檔案名稱'}), 400

    if not _validate_write_access(group, write_groups):
        return jsonify({'error': '無寫入權限'}), 403

    # 驗證副檔名
    ext = Path(name).suffix.lower()
    if ext not in cfg.ALLOWED_EXTENSIONS:
        allowed = ', '.join(cfg.ALLOWED_EXTENSIONS)
        return jsonify({'error': f'僅允許 {allowed} 格式'}), 400

    # 驗證大小
    if len(content.encode('utf-8')) > cfg.MAX_FILE_SIZE:
        return jsonify({'error': f'內容超過 {cfg.MAX_FILE_SIZE // 1024 // 1024}MB 限制'}), 400

    # 安全清理檔名（不可包含路徑分隔符號）
    safe_name = Path(name).name
    if not safe_name or safe_name.startswith('.') or safe_name != name:
        return jsonify({'error': '無效的檔案名稱'}), 400

    # 存檔
    user_dir = _get_user_dir(group, username)
    user_dir.mkdir(parents=True, exist_ok=True)
    filepath = user_dir / safe_name
    filepath.write_text(content, encoding='utf-8')

    # 同步重建索引
    rebuilt = _trigger_rebuild(group)
    msg = f'檔案 {safe_name} 已儲存'
    if rebuilt:
        msg += '，知識庫已更新'
    else:
        msg += '（知識庫更新失敗，主站可能未啟動）'

    return jsonify({'message': msg}), 200


@app.route('/api/file', methods=['DELETE'])
@login_required
def delete_file():
    """刪除檔案"""
    username = session['username']
    write_groups = session.get('write_groups', [])
    data = request.json or {}

    group = data.get('group', '').strip()
    name = data.get('name', '').strip()

    if not group or not name:
        return jsonify({'error': '缺少群組或檔案名稱'}), 400

    if not _validate_write_access(group, write_groups):
        return jsonify({'error': '無寫入權限'}), 403

    filepath = _get_user_dir(group, username) / name

    # 安全檢查
    try:
        filepath.resolve().relative_to(cfg.KNOWLEDGE_BASE_DIR.resolve())
    except ValueError:
        return jsonify({'error': '無效路徑'}), 400

    if not filepath.exists():
        return jsonify({'error': '檔案不存在'}), 404

    filepath.unlink()

    # 同步重建索引
    rebuilt = _trigger_rebuild(group)
    msg = f'檔案 {name} 已刪除'
    if rebuilt:
        msg += '，知識庫已更新'
    else:
        msg += '（知識庫更新失敗，主站可能未啟動）'

    return jsonify({'message': msg}), 200


# ============================================================
# 啟動伺服器
# ============================================================

if __name__ == '__main__':
    print(f"{cfg.PROJECT_ROOT.name}")
    app.run(host=cfg.HOST, port=cfg.PORT, debug=cfg.DEBUG)
