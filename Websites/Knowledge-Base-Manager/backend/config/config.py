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
PORT = 9997
DEBUG = True

# 主站伺服器位址（用於未登入時導回主站）
SERVER_IP = '192.168.18.6'                  # ← 部署時改為實際伺服器 IP
MAIN_SITE_PORT = 9998

SECRET_KEY = os.environ.get('SECRET_KEY')
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = MAIN_PROJECT_ROOT / 'backend' / 'flask_session'
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

# 知識庫設定（指向主專案的 data 目錄）
KNOWLEDGE_BASE_DIR = MAIN_PROJECT_ROOT / 'backend' / 'data'
PUBLIC_GROUP = 'Public'
SYSTEM_UPLOADER = 'system'
ALLOWED_EXTENSIONS = {'.md', '.txt'}
MAX_FILE_SIZE = 1 * 1024 * 1024              # 最大檔案大小（1MB）

# 內部 API 密鑰（與主站共用，用於觸發知識庫重建）
INTERNAL_SECRET = os.environ.get('INTERNAL_SECRET', 'deterministic-agent-internal')
