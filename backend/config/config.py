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
PORT = 9998
DEBUG = True

SECRET_KEY = os.environ.get('SECRET_KEY')
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = BACKEND_DIR / 'flask_session'
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

ACCESS_CONTROL_CSV = CONFIG_DIR / 'access_control.csv'
APP_REGISTRY_CSV = CONFIG_DIR / 'app_registry.csv'
ACCOUNT_SYSTEM_URL = 'http://localhost:9999'

# Gemini 設定（在專案根目錄 .env 檔案中設定 GEMINI_API_KEY）
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = 'gemini-2.5-flash'

# 知識庫設定
KNOWLEDGE_BASE_DIR = DATA_DIR
GEMINI_SYSTEM_INSTRUCTION_TEMPLATE = """你是一個知識庫問答助手，請使用繁體中文回答。
你只能根據下方「知識庫」中的內容回答問題。
如果問題的答案不在知識庫中，請回答：「很抱歉，此問題不在我的知識範圍內。」
不要編造任何知識庫中沒有的資訊。

=== 知識庫 ===
{knowledge_base_content}
"""
