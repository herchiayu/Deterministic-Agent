from flask import Flask, request, jsonify, send_from_directory, session, redirect, Response, stream_with_context
from flask_cors import CORS
from flask_session import Session
from functools import wraps
import csv
import requests
from google import genai
from google.genai import types
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
SESSION_FILE_DIR.mkdir(exist_ok=True)


# 啟動時清除所有 session 檔案（必須在 Session(app) 之後執行）
def cleanup_all_sessions():
    if SESSION_FILE_DIR.exists():
        for f in SESSION_FILE_DIR.glob('*'):
            if f.is_file():
                f.unlink()


cleanup_all_sessions()

# ─── Gemini 設定 ───
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# 儲存每個使用者的 Gemini Chat Session
user_chats = {}


def get_or_create_chat(username):
    """取得或建立使用者的聊天 session"""
    if username not in user_chats:
        user_chats[username] = gemini_client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=GEMINI_SYSTEM_INSTRUCTION
            )
        )
    return user_chats[username]


# ─── 帳號系統整合 ───

def verify_user(username: str, password: str) -> dict | None:
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
    return send_from_directory(FRONTEND_DIR / 'css', filename)


@app.route('/static/js/<path:filename>')
def js_files(filename):
    return send_from_directory(FRONTEND_DIR / 'js', filename)


@app.route('/static/images/<path:filename>')
def image_files(filename):
    return send_from_directory(FRONTEND_DIR / 'images', filename)


# ─── 頁面路由 ───

@app.route('/')
def index():
    return redirect('/home') if 'user_id' in session else send_from_directory(FRONTEND_DIR, 'login.html')


@app.route('/home')
@page_login_required
def home():
    return send_from_directory(FRONTEND_DIR, 'home.html')


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
    username = session.get('username')
    # 登出時清除該使用者的聊天記錄
    if username and username in user_chats:
        del user_chats[username]
    session.clear()
    session.modified = True
    return jsonify({'message': '登出成功'}), 200


# ─── 聊天 API ───

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """傳送訊息給 Gemini，以串流方式回傳回應"""
    data = request.json
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': '訊息不可為空'}), 400

    if not GEMINI_API_KEY:
        return jsonify({'error': 'Gemini API Key 未設定，請在 config.py 或環境變數中設定 GEMINI_API_KEY'}), 500

    username = session['username']
    chat_session = get_or_create_chat(username)

    def generate():
        try:
            for chunk in chat_session.send_message_stream(message):
                if chunk.text:
                    yield chunk.text
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


if __name__ == '__main__':
    print(f"{Path(__file__).parent.parent.name}")
    app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)
