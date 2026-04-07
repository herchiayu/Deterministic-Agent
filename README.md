# Deterministic Agent

基於 Flask 的多網站整合平台，提供統一登入、知識庫 AI 聊天助手（含工程計算工具），以及可擴充的子網站架構。

## 功能

- **統一登入** — 透過帳號系統（port 9999）驗證，所有子網站共享登入狀態（SSO）
- **AI 聊天助手** — 串接 Gemini API，結合向量知識庫問答（RAG）與工程計算工具（AFC）
- **多群組知識庫** — 依使用者群組分配不同的知識庫，各群組資料完全隔離
- **子網站管理** — 側邊欄自動載入已註冊的子網站清單，一鍵跳轉
- **權限控制** — 主站白名單控制系統登入，各子站可獨立設定白名單
- **知識庫熱更新** — 修改知識庫文件後，透過 API 即時重建向量索引，無需重啟伺服器

## 系統架構

```
帳號系統 (port 9999)
     │
     ▼
主站 (port 9998) ─── AI 聊天助手（RAG + AFC）+ 側邊欄
     │
     ├── 子站 A (port 5001)
     ├── 子站 B (port 5002)
     └── ...
```

## 快速開始

### 1. 建立環境

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
```

### 2. 設定環境變數

複製 `.env.example` 為 `.env`，填入實際值：

```env
SECRET_KEY=你的隨機金鑰
GEMINI_API_KEY=你的_Google_AI_Studio_API_Key
```

### 3. 啟動

```bash
run_server.bat
```

此腳本會自動啟動主站與所有子網站。

## 目錄結構

```
Deterministic-Agent/
├── .env                          # 環境變數（不版控）
├── .env.example                  # 環境變數範本
├── run_server.bat                # 一鍵啟動
├── backend/                      # 主站後端 (port 9998)
│   ├── server.py
│   ├── requirements.txt
│   ├── config/
│   │   ├── config.py             # 主站設定
│   │   ├── access_control.csv    # 主站白名單（含群組欄位）
│   │   └── app_registry.csv      # 子網站註冊表
│   ├── utils/
│   │   ├── math_tools.py         # 工程計算工具（AFC）
│   │   └── knowledge_base.py     # 向量知識庫模組（ChromaDB）
│   ├── data/                     # 知識庫文件（依群組分資料夾）
│   │   ├── Developer/            # Developer 群組知識庫
│   │   ├── RD_ME/                # RD_ME 群組知識庫
│   │   ├── default/              # 無群組使用者的預設訊息
│   │   └── chroma_db/            # ChromaDB 向量索引（自動生成）
│   ├── resources/                # 程式靜態資源（唯讀）
│   └── models/                   # 大型模型檔案（唯讀）
├── frontend/                     # 主站前端
│   ├── login.html
│   ├── home.html
│   ├── css/
│   ├── js/
│   └── images/
└── Websites/                     # 子網站集合
    ├── Web-Template/  (port 5001)
    ├── Web-Template-2/ (port 5002)
    └── Web-Template-3/ (port 5003)
```

---

## AI 聊天助手運作原理

AI 助手結合了兩種能力：**知識庫向量搜尋（RAG）** 和 **工程計算工具（Function Calling）**。

### 整體流程

```
使用者提問
    │
    ▼
依使用者群組，對各群組的 ChromaDB Collection 進行向量搜尋
    │
    ▼
取得最相關的 TOP_K 段落，組合成「參考資料」注入當前訊息
    │
    ▼
Gemini 收到「參考資料 + 使用者問題」+ 固定的 System Instruction
    │
    ▼
Gemini 判斷問題類型
    │
    ├─ 參考資料能回答 ──→ 直接引用回答
    │
    ├─ 需要計算 ──→ 呼叫工具函數 ──→ SDK 自動執行 ──→ 回傳結果 ──→ Gemini 組合回答
    │
    └─ 都不適用 ──→ 回覆「不在知識範圍內」
```

---

### 知識庫向量搜尋（Vector RAG）

**原理**：使用 ChromaDB 本地向量資料庫 + Gemini Embedding API。每次使用者提問時，先把問題轉成向量，搜尋最相近的知識庫段落，再將搜尋結果注入當前訊息傳給 Gemini。

**資料流（啟動時）**：

```
伺服器啟動
    │
    ▼
kb.build_all_indexes()
    │  掃描 data/ 下所有子目錄（Developer/, RD_ME/, default/, ...）
    │  每個子目錄 = 一個群組
    │
    ▼
對每個群組，讀取所有 .md / .txt 文件
    │  按 Markdown 標題切割段落（chunk_size=500 字元）
    │
    ▼
呼叫 gemini-embedding-001 將每個段落轉成向量
    │
    ▼
存入 ChromaDB（data/chroma_db/）—— 每個群組對應一個獨立 Collection
```

**資料流（每次對話）**：

```
使用者提問（如「爬電距離是什麼？」）
    │
    ▼
讀取 session['groups']（如 ['Developer', 'RD_ME']）
    │
    ▼
對每個群組的 Collection 做向量搜尋，取 TOP_K 段落
    │  多群組結果依餘弦相似度合併、排序
    │
    ▼
RAG_QUERY_TEMPLATE.format(context=段落內容, question=原始問題)
    │
    ▼
包裝後的訊息傳送給 Gemini Chat Session
```

**多群組知識庫配置**（`config/access_control.csv`）：

```csv
Username,Groups
Herch,Developer;RD_ME
User_RD,RD_ME
User_Dev,Developer
User_None,
```

- 群組用 `;` 分隔，可指定多個
- 空白群組欄位 → 分配到 `default` 群組
- `default` 群組的 `data/default/` 目錄通常放引導使用者聯絡管理員的訊息

**新增知識庫群組**：
1. 在 `data/` 下建立新子目錄（如 `data/HR/`）
2. 放入 `.md` 或 `.txt` 知識庫文件
3. 在 `access_control.csv` 將使用者指定到新群組
4. 呼叫 `POST /api/chat/reload-kb` 重建索引（或重啟伺服器）

**更新現有知識庫**：
- 編輯 `data/{群組}/` 下的文件
- 呼叫 `POST /api/chat/reload-kb` 熱更新（會清除所有使用者的 chat session）

**相關檔案**：

| 檔案 | 角色 |
|------|------|
| `backend/data/{群組}/*.md` | 各群組知識庫文件 |
| `backend/utils/knowledge_base.py` | 向量索引建立、搜尋、ChromaDB 操作 |
| `config/config.py` — `CHROMA_DB_DIR` | ChromaDB 儲存路徑 |
| `config/config.py` — `EMBEDDING_MODEL` | Gemini 嵌入模型（`gemini-embedding-001`） |
| `config/config.py` — `CHUNK_SIZE` / `TOP_K_RESULTS` | 分段大小 / 每次搜尋回傳段落數 |
| `config/config.py` — `RAG_QUERY_TEMPLATE` | 包裝問題與參考資料的模板 |
| `config/access_control.csv` | 使用者 ↔ 群組對照表 |
| `server.py` — `POST /api/chat/reload-kb` | 熱更新知識庫索引 |

---

### 工程計算工具（Function Calling）

**原理**：使用 Gemini 的 Automatic Function Calling (AFC)。將 Python 函數直接傳給 Gemini，Gemini 判斷需要計算時自動呼叫，SDK 在本機執行函數並將結果回傳給 Gemini 組合成自然語言回答。

**資料流**：

```
使用者: 「馬赫數 2.0 的壓力比是多少？」
    │
    ▼
chat.send_message(...)
    │
    ▼
Gemini 分析 → 決定呼叫 isentropic_pressure_ratio(mach=2.0)
    │
    ▼
SDK 自動在本機執行該函數 → 回傳 {'pressure_ratio': 7.824608, ...}
    │
    ▼
SDK 自動將結果送回 Gemini
    │
    ▼
Gemini 組合最終回答:
    「在馬赫數 2.0、γ=1.4 的條件下，
     等熵流壓力比 PR = 7.824608
     使用公式：PR = (1 + (γ-1)/2 × M²) ^ (γ/(γ-1))」
```

**關鍵機制**：
- AFC 靠函數的 **名稱**、**type hints**、**docstring** 讓 Gemini 理解函數用途
- 計算完全在本機執行，公式由你掌控，100% 確定性
- Gemini 只負責「判斷要呼叫什麼」和「將結果組合成自然語言」

**目前已實作工具**：

| 函數 | 說明 |
|------|------|
| `isentropic_pressure_ratio(mach, gamma=1.4)` | 等熵流壓力比 PR = (1 + (γ-1)/2 × M²)^(γ/(γ-1)) |
| `isentropic_temperature_ratio(mach, gamma=1.4)` | 等熵流溫度比 TR = 1 + (γ-1)/2 × M² |

**相關檔案**：

| 檔案 | 角色 |
|------|------|
| `backend/utils/math_tools.py` | 計算函數定義 + `TOOL_FUNCTIONS` 註冊表 |
| `server.py` — `get_or_create_chat()` | 將 `TOOL_FUNCTIONS` 傳入 `tools` 參數 |

### 新增計算工具（開發指南）

只需編輯 `backend/utils/math_tools.py`，三步完成：

**第一步：寫計算函數**

```python
def my_new_calculator(param_a: float, param_b: float = 1.0) -> dict:
    """
    函數說明（Gemini 讀這段來理解功能）
    寫清楚這個函數算什麼、公式是什麼
    """
    result = param_a * param_b  # 你的計算邏輯
    return {
        'param_a': param_a,
        'param_b': param_b,
        'result': round(result, 6),
        'formula': 'Result = A × B'
    }
```

**必要條件**（AFC 依賴這些資訊）：
- ✅ 參數必須有 **type hints**（`float`, `str`, `int` 等）
- ✅ 必須有 **docstring** 描述功能
- ✅ 回傳 `dict`
- 選用預設值的參數，使用者可省略

**第二步：加入 TOOL_FUNCTIONS**

```python
TOOL_FUNCTIONS = [
    isentropic_pressure_ratio,
    isentropic_temperature_ratio,
    my_new_calculator,           # ← 加在這裡
]
```

**第三步：重啟伺服器**

不需要改 `server.py` 或 `config.py`。

---

## 新增子網站

詳見 [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)。

## 開發規範

詳見 `.github/DEVELOPER_SPEC.md`。