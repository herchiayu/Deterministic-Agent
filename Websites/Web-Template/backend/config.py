from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
MAIN_PROJECT_ROOT = PROJECT_ROOT.parent.parent

# 載入主專案根目錄的 .env（共用 SECRET_KEY 以實現單一登入）
load_dotenv(MAIN_PROJECT_ROOT / '.env')

FRONTEND_DIR = PROJECT_ROOT / 'frontend'
DATA_DIR = BACKEND_DIR / 'data'
UPLOAD_DIR = BACKEND_DIR / 'uploads'

HOST = '0.0.0.0'
PORT = 5001
DEBUG = True

SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = MAIN_PROJECT_ROOT / 'backend' / 'flask_session'
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

ACCESS_CONTROL_CSV = DATA_DIR / 'access_control.csv'
ACCOUNT_SYSTEM_URL = 'http://localhost:9999'
