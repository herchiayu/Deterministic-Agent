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
PORT = 5001
DEBUG = True

# 主站伺服器位址（用於未登入時導回主站）
SERVER_IP = '192.168.18.6'                  # ← 部署時改為實際伺服器 IP
MAIN_SITE_PORT = 9998

SECRET_KEY = os.environ.get('SECRET_KEY')
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = MAIN_PROJECT_ROOT / 'backend' / 'flask_session'
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

ACCESS_CONTROL_CSV = CONFIG_DIR / 'access_control.csv'
ACCOUNT_SYSTEM_URL = f'http://{SERVER_IP}:9999'