from flask import Flask, request, jsonify, send_from_directory, session, redirect, Response, stream_with_context
from flask_cors import CORS
from flask_session import Session
from functools import wraps
import csv
import requests
from google import genai
from google.genai import types
from config import config as cfg
from utils.math_tools import TOOL_FUNCTIONS
from utils.knowledge_base import kb

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

# ─── Gemini 設定 ───
gemini_client = genai.Client(api_key=cfg.GEMINI_API_KEY)

# 儲存每個使用者的 Gemini Chat Session
user_chats = {}


# 啟動時建立知識庫向量索引
if cfg.ENABLE_KNOWLEDGE_BASE:
    kb.build_all_indexes()


def get_or_create_chat(username):
    """取得或建立使用者的聊天 session"""
    if username not in user_chats:
        if cfg.ENABLE_KNOWLEDGE_BASE:
            instruction = cfg.GEMINI_SYSTEM_INSTRUCTION
        else:
            instruction = cfg.GEMINI_SYSTEM_INSTRUCTION_NO_KB
        user_chats[username] = gemini_client.chats.create(
            model=cfg.GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                tools=TOOL_FUNCTIONS,
            )
        )
    return user_chats[username]


# ─── 帳號系統整合 ───

def verify_user(username: str, password: str) -> dict | None:
    try:
        response = requests.post(f'{cfg.ACCOUNT_SYSTEM_URL}/api/verify',
                                 json={'username': username, 'password': password}, timeout=5)
        data = response.json()
        return data if data.get('success') else None
    except:
        return None


def load_whitelist():
    """載入白名單與群組對照，回傳 (whitelist_set, groups_dict) 或 (None, {})"""
    if not cfg.ACCESS_CONTROL_CSV.exists():
        return None, {}
    whitelist = set()
    groups_map = {}  # {username: [group1, group2, ...]}
    with open(cfg.ACCESS_CONTROL_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if username := row.get('Username', '').strip():
                whitelist.add(username)
                raw_groups = row.get('Groups', '').strip()
                if raw_groups:
                    groups_map[username] = [
                        g.strip() for g in raw_groups.split(cfg.GROUP_SEPARATOR) if g.strip()
                    ]
                else:
                    groups_map[username] = [cfg.DEFAULT_GROUP]
    return whitelist, groups_map


# ─── 裝飾器 ───

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


# ─── 靜態資源路由 ───

@app.route('/static/css/<path:filename>')
def css_files(filename):
    return send_from_directory(cfg.FRONTEND_DIR / 'css', filename)


@app.route('/static/js/<path:filename>')
def js_files(filename):
    return send_from_directory(cfg.FRONTEND_DIR / 'js', filename)


@app.route('/static/images/<path:filename>')
def image_files(filename):
    return send_from_directory(cfg.FRONTEND_DIR / 'images', filename)


# ─── 頁面路由 ───

@app.route('/')
def index():
    return redirect('/home') if 'user_id' in session else send_from_directory(cfg.FRONTEND_DIR, 'login.html')


@app.route('/home')
@page_login_required
def home():
    return send_from_directory(cfg.FRONTEND_DIR, 'home.html')


# ─── 認證 API ───

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
    whitelist, groups_map = load_whitelist()
    if whitelist is not None and username not in whitelist:
        return jsonify({'error': '您沒有權限進入此系統'}), 403

    # 設定 session
    session['user_id'] = result['user_id']
    session['username'] = result['username']
    session['groups'] = groups_map.get(username, [cfg.DEFAULT_GROUP])
    return jsonify({'message': '登入成功'}), 200


@app.route('/api/check-auth')
@login_required
def check_auth():
    return jsonify({'authenticated': True, 'username': session['username']}), 200


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    username = session.get('username')
    # 登出時清除該使用者的聊天記錄
    if username and username in user_chats:
        del user_chats[username]
    session.clear()
    session.modified = True
    return jsonify({'message': '登出成功'}), 200


# ─── 網站清單 API ───

@app.route('/api/apps')
@login_required
def get_apps():
    """取得已註冊的網站清單"""
    apps = []
    if cfg.APP_REGISTRY_CSV.exists():
        with open(cfg.APP_REGISTRY_CSV, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                name = row.get('Name', '').strip()
                port = row.get('Port', '').strip()
                description = row.get('Description', '').strip()
                if name and port:
                    apps.append({'name': name, 'port': port, 'description': description})
    return jsonify({'apps': apps}), 200


# ─── 聊天 API ───

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """傳送訊息給 Gemini，處理 function calling 後回傳回應"""
    data = request.json
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': '訊息不可為空'}), 400

    if not cfg.GEMINI_API_KEY:
        return jsonify({'error': 'Gemini API Key 未設定，請在 config.py 或環境變數中設定 GEMINI_API_KEY'}), 500

    username = session['username']
    chat_session = get_or_create_chat(username)

    # 若啟用知識庫，先檢索相關段落並包裝訊息
    if cfg.ENABLE_KNOWLEDGE_BASE:
        user_groups = session.get('groups', [cfg.DEFAULT_GROUP])
        context = kb.search(message, groups=user_groups)
        wrapped_message = cfg.RAG_QUERY_TEMPLATE.format(
            context=context if context else '（無相關參考資料）',
            question=message,
        )
    else:
        wrapped_message = message

    def generate():
        try:
            # AFC (Automatic Function Calling) 會自動執行函數並回傳最終結果
            response = chat_session.send_message(wrapped_message)

            if response.text:
                yield response.text

        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower():
                yield '\n\n[錯誤] API 額度已用完，請檢查 Google AI Studio 的方案與帳單設定。'
            else:
                yield f'\n\n[錯誤] {error_msg}'

    return Response(stream_with_context(generate()), mimetype='text/plain')


@app.route('/api/chat/history', methods=['GET'])
@login_required
def chat_history():
    """取得目前使用者的聊天記錄"""
    username = session['username']
    chat_session = user_chats.get(username)

    history = chat_session.get_history() if chat_session else []
    if not history:
        return jsonify({'messages': []}), 200

    messages = []
    for msg in history:
        role = 'assistant' if msg.role == 'model' else 'user'
        content = ''.join(part.text for part in msg.parts if hasattr(part, 'text'))
        messages.append({'role': role, 'content': content})

    return jsonify({'messages': messages}), 200


@app.route('/api/chat/clear', methods=['POST'])
@login_required
def chat_clear():
    """清除目前使用者的聊天記錄"""
    username = session['username']
    if username in user_chats:
        del user_chats[username]
    return jsonify({'message': '聊天記錄已清除'}), 200


@app.route('/api/chat/reload-kb', methods=['POST'])
@login_required
def reload_knowledge_base_api():
    """重建知識庫向量索引，並清除所有使用者的聊天 session"""
    kb.build_all_indexes(force_rebuild=True)
    user_chats.clear()
    return jsonify({'message': '知識庫已重新載入'}), 200


@app.route('/api/internal/rebuild-group', methods=['POST'])
def internal_rebuild_group():
    """子站呼叫：重建特定群組的知識庫索引"""
    secret = request.headers.get('X-Internal-Secret', '')
    if secret != cfg.INTERNAL_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json or {}
    group = data.get('group', '').strip()
    if not group:
        return jsonify({'error': 'Missing group'}), 400
    kb.build_group_index(group, force_rebuild=True)
    return jsonify({'message': f'{group} index rebuilt'}), 200



if __name__ == '__main__':
    print(f"{cfg.PROJECT_ROOT.name}")
    app.run(host=cfg.HOST, port=cfg.PORT, debug=cfg.DEBUG, use_reloader=False)
