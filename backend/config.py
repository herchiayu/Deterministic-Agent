from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / 'frontend'
DATA_DIR = BACKEND_DIR / 'data'
UPLOAD_DIR = BACKEND_DIR / 'uploads'

HOST = '0.0.0.0'
PORT = 5000
DEBUG = True

SECRET_KEY = os.environ.get('SECRET_KEY', '')
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = BACKEND_DIR / 'flask_session'
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

ACCESS_CONTROL_CSV = DATA_DIR / 'access_control.csv'
ACCOUNT_SYSTEM_URL = 'http://localhost:9999'

# Gemini 設定（在專案根目錄 .env 檔案中設定 GEMINI_API_KEY）
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = 'gemini-2.5-flash'
GEMINI_SYSTEM_INSTRUCTION = '你是一個友善的 AI 助手，請使用繁體中文回答問題。'
