# Deterministic Agent

基於 Flask 的多網站整合平台，提供統一登入、知識庫 AI 聊天助手（含工程計算工具），以及可擴充的子網站架構。

## 功能

- **統一登入** — 透過帳號系統（port 9999）驗證，所有子網站共享登入狀態（SSO）
- **AI 聊天助手** — 串接 Gemini API，結合知識庫問答與工程計算工具
- **子網站管理** — 側邊欄自動載入已註冊的子網站清單，一鍵跳轉
- **權限控制** — 主站白名單控制系統登入，各子站可獨立設定白名單
- **知識庫熱更新** — 修改知識庫文件後，透過 API 即時重載，無需重啟伺服器

## 系統架構

```
帳號系統 (port 9999)
     │
     ▼
主站 (port 9998) ─── AI 聊天助手 + 側邊欄
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
│   │   ├── access_control.csv    # 主站白名單
│   │   └── app_registry.csv      # 子網站註冊表
│   ├── utils/
│   │   └── math_tools.py         # 工程計算工具（Function Calling）
│   ├── data/                     # 知識庫文件 (.md / .txt)
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

AI 助手結合了兩種能力：**知識庫問答（RAG）** 和 **工程計算工具（Function Calling）**。

### 整體流程

```
使用者提問
    │
    ▼
Gemini 收到訊息 + System Instruction（含知識庫全文 + 工具清單）
    │
    ▼
Gemini 判斷問題類型
    │
    ├─ 知識庫能回答 ──→ 直接從知識庫內容引用回答
    │
    ├─ 需要計算 ──→ 呼叫工具函數 ──→ SDK 自動執行 ──→ 回傳結果 ──→ Gemini 組合回答
    │
    └─ 都不適用 ──→ 回覆「不在知識範圍內」
```

### 知識庫問答（RAG）

**原理**：將知識庫全文塞進 Gemini 的 System Instruction，限定 AI 只能根據知識庫內容回答。

**資料流**：

```
伺服器啟動
    │
    ▼
load_knowledge_base()
    │  讀取 backend/data/ 下所有 .md 和 .txt 檔案
    │  依檔名排序後合併為一個字串
    ▼
組合 System Instruction
    │  GEMINI_SYSTEM_INSTRUCTION_TEMPLATE.format(knowledge_base_content=...)
    │  模板內容：
    │    - 限定只能根據知識庫回答
    │    - 無法回答時拒答
    │    - 不可編造資訊
    │    - 有計算工具可用時呼叫工具
    ▼
建立 Chat Session（每位使用者獨立）
```

**相關檔案**：
| 檔案 | 角色 |
|------|------|
| `backend/data/*.md`, `*.txt` | 知識庫文件 |
| `config/config.py` — `KNOWLEDGE_BASE_DIR` | 知識庫目錄路徑 |
| `config/config.py` — `GEMINI_SYSTEM_INSTRUCTION_TEMPLATE` | 包含知識庫的 System Instruction 模板 |
| `server.py` — `load_knowledge_base()` | 讀取並合併知識庫檔案 |
| `server.py` — `POST /api/chat/reload-kb` | 熱更新知識庫（不用重啟伺服器） |

**更新知識庫**：
- 編輯 `backend/data/` 下的檔案
- 呼叫 `POST /api/chat/reload-kb` 即可熱更新
- 這會重新讀取所有檔案，並清除所有使用者的 chat session（讓新知識庫生效）

### 工程計算工具（Function Calling）

**原理**：使用 Gemini 的 Automatic Function Calling (AFC)。將 Python 函數直接傳給 Gemini，Gemini 判斷需要計算時自動呼叫，SDK 在本機執行函數並將結果回傳給 Gemini 組合成自然語言回答。

**資料流**：

```
使用者: 「馬赫數 2.0 的壓力比是多少？」
    │
    ▼
chat.send_message("馬赫數 2.0 的壓力比是多少？")
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
