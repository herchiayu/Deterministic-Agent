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
ENABLE_KNOWLEDGE_BASE = True          # 設為 False 可關閉知識庫，測試純 Gemini 回答
KNOWLEDGE_BASE_DIR = DATA_DIR
DEFAULT_GROUP = 'default'             # 無群組使用者的預設群組
GROUP_SEPARATOR = ';'                 # access_control.csv 中群組分隔符號

# 向量資料庫設定
CHROMA_DB_DIR = DATA_DIR / 'chroma_db'
EMBEDDING_MODEL = 'gemini-embedding-001'     # Gemini embedding 模型
CHUNK_SIZE = 500                             # 每個段落最大字元數
CHUNK_OVERLAP = 50                           # 段落之間重疊字元數
TOP_K_RESULTS = 5                            # 每次檢索回傳的段落數

# 內部 API 密鑰（子站呼叫主站重建索引用）
INTERNAL_SECRET = os.environ.get('INTERNAL_SECRET', 'deterministic-agent-internal')

# System Instruction（固定，不含知識庫內容）
GEMINI_SYSTEM_INSTRUCTION_NO_KB = '請使用繁體中文回答。'
GEMINI_SYSTEM_INSTRUCTION = """你是一個知識庫問答助手，請使用繁體中文回答。
你只能根據每次提供給你的「參考資料」回答問題。
如果參考資料中沒有答案，請回答：「很抱歉，此問題不在我的知識範圍內。」
不要編造任何參考資料中沒有的資訊。

每段參考資料都標有「來源」和「上傳者」。回答時請在最後標示你引用了誰的資料，格式為 [來源: 檔名 | 上傳者: 名稱]。
當不同來源的資訊互相矛盾時，請分別列出各方說法並標示各自的來源與上傳者，不要擅自裁定哪方正確。

你也有工程計算工具可以使用。當使用者詢問可用工具能計算的問題時，請呼叫對應的工具取得精確結果，不要自己心算或估算。
回傳計算結果時，請一併列出使用的公式與輸入參數。"""

# 每次使用者提問時，將檢索結果與原始問題包裝成此格式
RAG_QUERY_TEMPLATE = """=== 參考資料 ===
{context}

=== 使用者問題 ===
{question}"""
