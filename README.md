# Deterministic Agent

一個基於 Gemini API 的企業內部 AI 問答平台，整合 RAG（向量知識庫）與 AFC（自動函式呼叫），並提供多使用者分群知識庫管理。

---

## 目錄結構

```
Deterministic-Agent/
├── .env                         ← 環境變數（GEMINI_API_KEY、SECRET_KEY、INTERNAL_SECRET）
├── README.md
├── run_server.bat               ← 啟動主站（port 9998）
├── initiate_project.bat         ← 初次建立虛擬環境與安裝套件
├── finalize_project.bat
│
├── backend/                     ← 主站 Flask 後端
│   ├── server.py                ← 主站入口（port 9998）
│   ├── requirements.txt
│   ├── config/
│   │   ├── config.py            ← 主站設定
│   │   ├── access_control.csv   ← 使用者白名單與群組對照
│   │   └── app_registry.csv     ← 子站清單（側欄顯示用）
│   ├── utils/
│   │   ├── knowledge_base.py    ← RAG 核心（ChromaDB + Gemini Embedding）
│   │   └── math_tools.py        ← AFC 工程計算工具（供 Gemini 呼叫）
│   ├── data/                    ← 知識庫根目錄
│   │   ├── chroma_db/           ← ChromaDB 持久化（自動產生，勿手動修改）
│   │   ├── default/
│   │   │   └── system/
│   │   │       └── notice.md    ← 無群組使用者看到的引導訊息
│   │   ├── Developer/
│   │   │   └── {username}/      ← 每位 Developer 成員的知識庫
│   │   │       └── *.md / *.txt
│   │   └── RD_ME/
│   │       └── {username}/
│   │           └── *.md / *.txt
│   ├── flask_session/           ← Server-side Session 檔案（自動產生）
│   ├── models/                  ← 保留目錄
│   └── resources/               ← 保留目錄
│
├── frontend/                    ← 主站前端
│   ├── login.html / login.js / login.css
│   └── home.html / home.js / home.css
│
└── Websites/                    ← 子站群
    ├── Web-Template/            ← 子站模板（參考用）
    └── Knowledge-Base-Manager/  ← 知識庫管理子站（port 9997）
        ├── backend/
        │   ├── server.py
        │   └── config/
        │       ├── config.py    ← 子站設定（含主站路徑與 IP 設定）
        │       └── access_control.csv
        └── frontend/
            ├── home.html / home.js / home.css
            └── images/
```

---

## 快速啟動

### 1. 環境設定

專案根目錄建立 `.env` 檔，填入以下變數：

```env
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_flask_secret_key
INTERNAL_SECRET=deterministic-agent-internal
```

> `INTERNAL_SECRET` 預設值即 `deterministic-agent-internal`，可直接沿用或自訂。
> `SECRET_KEY` 主站與所有子站必須**相同**，否則 Session 無法共用。

### 2. 初次安裝

```bat
initiate_project.bat
```

此 bat 會建立 `.venv/` 虛擬環境並安裝 `backend/requirements.txt`。

### 3. 啟動主站

```bat
run_server.bat
```

主站啟動於 **port 9998**，啟動時會自動建立所有群組的 ChromaDB 向量索引。

### 4. 啟動子站（Knowledge-Base-Manager）

```bat
cd Websites\Knowledge-Base-Manager\backend
python server.py
```

子站啟動於 **port 9997**，需在主站已啟動的情況下使用（儲存／刪除後會呼叫主站重建索引）。

---

## 帳號系統

主站透過外部帳號服務驗證登入（`POST http://localhost:9999/api/verify`），此服務需獨立部署。

### 白名單與群組（`backend/config/access_control.csv`）

```csv
Username,Groups
Herch,Developer;RD_ME
User_All,Developer;RD_ME
User_RD,RD_ME
User_Dev,Developer
User_None,
```

- `Groups` 欄位用 `;` 分隔多個群組。
- 若 `Groups` 為空，使用者被分配至 `default` 群組。
- 若 `access_control.csv` 不存在，則不啟用白名單（所有登入者皆可進入）。

### Session 共用機制（SSO）

所有子站皆使用 **filesystem session**，Session 檔案儲存於主站的 `backend/flask_session/` 目錄。子站的 `config.py` 中 `SESSION_FILE_DIR` 指向此目錄，且 `SECRET_KEY` 必須與主站相同，才能讀取同一個 Session。

---

## 知識庫架構

### 目錄結構（兩層）

```
backend/data/
├── chroma_db/               ← 向量資料庫（per-group collection）
├── {group}/
│   ├── system/              ← 保留，僅供系統管理員手動放置（uploader='system'）
│   │   └── notice.md
│   └── {username}/          ← 每位使用者的個人資料夾
│       └── *.md / *.txt
```

> **`system/` 為保留字**，禁止透過 Knowledge-Base-Manager 建立或刪除此目錄下的檔案。

### 群組隔離規則

| 情境 | 行為 |
|------|------|
| 使用者屬於 `RD_ME` 群組 | 只能看到 `RD_ME/` 下所有成員的知識 |
| 使用者屬於多個群組 | 查詢時合併所有群組的知識庫 |
| 使用者無群組（`default`） | 只能看到 `default/system/notice.md` |
| 知識衝突（不同來源說法不同） | AI 分別列出各方說法與來源，不自行裁定 |

### AI 回應格式

AI 引用知識庫時，每段資料標記為：

```
[來源: 檔名 | 上傳者: 使用者名稱]
```

例如：`[來源: DEVELOPER_SPEC.md | 上傳者: Herch]`

### ChromaDB Collection 命名

每個群組對應一個 collection，名稱即群組名稱（如 `Developer`、`RD_ME`、`default`）。Chunk ID 格式為 `{uploader}/{filename}::chunk_{n}`。

---

## 子站清單（`backend/config/app_registry.csv`）

主站側欄的「應用清單」由此 CSV 驅動：

```csv
Name,Port,Description
Knowledge-Base-Manager,9997,知識庫管理
```

- `Name`：子站顯示名稱
- `Port`：子站 port（使用者點擊後會在同一 IP 的此 port 開啟新分頁）
- `Description`：說明文字

新增子站時，將其加入此 CSV 並在 `Websites/` 下建立對應的 Flask app 即可。

---

## API 總覽

### 主站（port 9998）

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/login` | 登入（呼叫外部帳號服務，寫入 session） |
| `GET` | `/api/check-auth` | 確認是否已登入 |
| `POST` | `/api/logout` | 登出（清除 session 與聊天記錄） |
| `GET` | `/api/apps` | 取得 app_registry.csv 的子站清單 |
| `POST` | `/api/chat` | 傳送訊息（Streaming response，含 RAG + AFC） |
| `GET` | `/api/chat/history` | 取得目前使用者的聊天記錄 |
| `POST` | `/api/chat/clear` | 清除目前使用者的聊天記錄 |
| `POST` | `/api/chat/reload-kb` | 強制重建所有群組的知識庫索引（需登入） |
| `POST` | `/api/internal/rebuild-group` | **內部用**：重建指定群組的索引（需 `X-Internal-Secret` header） |

#### Internal API 說明

子站呼叫主站重建索引：

```http
POST http://localhost:9998/api/internal/rebuild-group
X-Internal-Secret: {INTERNAL_SECRET}
Content-Type: application/json

{"group": "Developer"}
```

### Knowledge-Base-Manager（port 9997）

| 方法 | 路徑 | 說明 |
|------|------|------|
| `GET` | `/api/check-auth` | 確認登入狀態（含 groups） |
| `POST` | `/api/logout` | 登出 |
| `GET` | `/api/files?group={group}` | 列出使用者在指定群組的檔案 |
| `GET` | `/api/file/content?group={group}&name={file}` | 讀取檔案內容 |
| `POST` | `/api/file` | 新增或更新檔案（儲存後自動重建索引） |
| `DELETE` | `/api/file` | 刪除檔案（刪除後自動重建索引） |

---

## 核心模組

### `backend/utils/knowledge_base.py`

```python
from utils.knowledge_base import kb

kb.build_all_indexes()                                    # 啟動時建立所有群組索引
kb.build_all_indexes(force_rebuild=True)                  # 強制重建所有索引
kb.build_group_index('Developer', force_rebuild=True)     # 重建單一群組
results = kb.search("問題", groups=['RD_ME'])              # 向量檢索（回傳格式化字串）
```

**`search()` 回傳格式：**

```
[來源: filename | 上傳者: uploader]
{chunk 內容}

[來源: ...]
...
```

### `backend/utils/math_tools.py`

定義供 Gemini AFC 呼叫的工程計算函式（如爬電距離計算等）。新增工具時，在此模組定義函式並加入 `TOOL_FUNCTIONS` 清單。

---

## 設定檔說明

### 主站 `backend/config/config.py`

| 變數 | 說明 |
|------|------|
| `PORT` | `9998` |
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `ENABLE_KNOWLEDGE_BASE` | `True`；設為 `False` 可跳過 RAG |
| `DEFAULT_GROUP` | `'default'`（無群組使用者的預設群組） |
| `GROUP_SEPARATOR` | `';'`（access_control.csv 中的群組分隔符） |
| `EMBEDDING_MODEL` | `gemini-embedding-001` |
| `CHUNK_SIZE` | `500`（每段最大字元數） |
| `CHUNK_OVERLAP` | `50`（段落重疊字元數） |
| `TOP_K_RESULTS` | `5`（每次檢索回傳段落數） |
| `INTERNAL_SECRET` | 讀自 `.env`，預設 `deterministic-agent-internal` |

### Knowledge-Base-Manager `Websites/Knowledge-Base-Manager/backend/config/config.py`

| 變數 | 說明 |
|------|------|
| `PORT` | `9997` |
| `SERVER_IP` | 部署時改為實際伺服器 IP（目前預設 `192.168.18.6`） |
| `MAIN_SITE_PORT` | `9998` |
| `MAIN_PROJECT_ROOT` | `PROJECT_ROOT.parent.parent`（即 `Deterministic-Agent/`） |
| `KNOWLEDGE_BASE_DIR` | `MAIN_PROJECT_ROOT/backend/data` |
| `SESSION_FILE_DIR` | `MAIN_PROJECT_ROOT/backend/flask_session` |
| `ALLOWED_EXTENSIONS` | `{'.md', '.txt'}` |
| `MAX_FILE_SIZE` | `1MB` |

---

## 新增群組流程

1. 在 `backend/config/access_control.csv` 新增使用者並設定群組名稱。
2. 建立對應的知識庫目錄（Knowledge-Base-Manager 儲存時會自動建立，也可手動建立）：
   ```
   backend/data/{新群組名稱}/{username}/
   ```
3. 若有系統預設知識，手動放置於 `backend/data/{新群組名稱}/system/` 下。
4. 重啟主站，或呼叫 `POST /api/chat/reload-kb` 重建索引。

---

## 新增子站流程

1. 複製 `Websites/Web-Template/` 為新子站目錄。
2. 修改 `backend/config/config.py` 中的 `PORT`、`SERVER_IP`、`MAIN_SITE_PORT`。
3. 確認 `SESSION_FILE_DIR` 指向主站的 `backend/flask_session/`，`SECRET_KEY` 與主站相同。
4. 在主站的 `backend/config/app_registry.csv` 新增一筆記錄。

---

## RAG 運作原理

1. **建立索引**：啟動時掃描 `data/{group}/{username}/*.md|*.txt`，切段後呼叫 Gemini Embedding API 向量化，存入 ChromaDB（per-group collection）。
2. **查詢流程**：使用者提問 → 向量化問題 → 從使用者所屬群組的 collection 檢索前 `TOP_K_RESULTS` 段 → 包裝成 `RAG_QUERY_TEMPLATE` → 傳給 Gemini。
3. **AFC 整合**：Gemini 若判斷需要工程計算，自動呼叫 `math_tools.py` 中定義的函式，取得精確結果後繼續生成回答。

---

## AFC 工程計算工具

`backend/utils/math_tools.py` 中定義的函式會自動成為 Gemini 可呼叫的工具。新增工具方式：

```python
# math_tools.py
def my_tool(param: float) -> float:
    """工具說明（Gemini 依此判斷何時呼叫）"""
    return param * 2

TOOL_FUNCTIONS = [my_tool, ...]  # 加入此清單
```

---

## 注意事項

- **ChromaDB 在 Windows 下有檔案鎖定問題**：主站運行中若強制刪除 `chroma_db/` 目錄下的子目錄會拋出 `PermissionError`，應使用 `force_rebuild=True` 而非手動刪除。
- **啟動時清除所有 Session**：主站每次啟動都會清除 `flask_session/` 下的所有 Session 檔案（`cleanup_all_sessions()`），所有使用者需重新登入。
- **子站不直接 import 主站模組**：子站透過 Internal API（HTTP）觸發主站重建索引，而非直接 import `knowledge_base.py`。
- **`default` 群組特殊處理**：Knowledge-Base-Manager 不允許使用者操作 `default` 群組的檔案（`_validate_group_access` 會拒絕），避免誤改系統引導訊息。
