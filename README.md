# 🍲 智能火锅点餐顾问 + RAG 知识问答

基于 **LangChain + Google Gemini + LangGraph + ChromaDB + FastAPI** 的 Web 应用。

- **RAG 知识问答**：将火锅知识文档（`data/*.txt`）录入 ChromaDB，用户提问时检索并由 Gemini 生成答案。
- **智能点餐顾问**：LangGraph 多轮对话（辣度、忌口、人数）→ 菜品推荐 → 结构化订单 JSON。自助餐固定每人价格，无需询问预算。
- **前置路由**：API 自动区分「知识问题」与「点餐请求」，分别走 RAG 或 Concierge。
- **一键部署**：Docker + Google Cloud Run。

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| LLM | **Google Gemini** (gemini-2.0-flash) | 通过 `langchain-google-genai` 调用 |
| RAG | **ChromaDB** + **HuggingFace Embeddings** | 向量存储与语义检索 |
| 编排 | **LangGraph** | 多轮对话状态机：Profiler → Inventory → Reviewer |
| 结构化输出 | **Pydantic** | `MenuItem` / `HotpotOrder` 保证订单可校验 |
| Web 服务 | **FastAPI** + **Uvicorn** | REST API + 静态前端 |
| 部署 | **Docker** + **Google Cloud Run** | 一键部署到云端 |

---

## 系统架构

```
用户消息 → API 前置路由
  ├─ 知识类问题（「肥牛涮多久？」）→ RAG 检索 + Gemini 生成答案
  └─ 点餐请求（「微辣、4人」）→ LangGraph Concierge 多轮对话
                                           └─ 确认 → Pydantic 结构化订单
```

---

## 项目结构（四层）

```
RAG/
├── api.py                 # Web 入口（uvicorn api:app）
├── main.py                # CLI：ingest / serve
├── core/                  # 核心：LLM + RAG
│   ├── __init__.py
│   ├── llm.py             # Gemini 工厂（get_llm）
│   └── rag.py             # 向量检索与问答（RAG 类）
├── concierge/             # 点餐顾问
│   ├── __init__.py
│   ├── state.py           # OrderState（LangGraph）
│   ├── graph.py           # Profiler → Inventory → Reviewer
│   ├── schemas.py         # Pydantic：MenuItem, HotpotOrder
│   ├── menu_loader.py     # 菜单与价格加载
│   ├── menu_generator.py  # 结构化订单生成（含蘸料）
│   ├── sauce_pairing.py   # 风味图谱蘸料推荐
│   └── tools.py           # 工具封装
├── data/                  # 数据
│   ├── sample.txt         # 火锅知识文档（启动时自动录入 RAG）
│   ├── hotpot_menu.json   # 菜单数据
│   ├── sauce_pairing_rules.json  # 蘸料规则
│   └── chroma_data/       # 向量库（自动生成，已 gitignore）
├── web/                   # 前后端
│   ├── __init__.py
│   ├── app.py             # FastAPI 应用（路由、Session、RAG 单例）
│   ├── schemas.py         # 请求/响应模型
│   ├── recommendation.py  # 食材推荐与购物车解析
│   └── static/            # 前端
│       ├── index.html
│       ├── css/style.css
│       └── js/app.js
├── Dockerfile
├── .dockerignore
├── .env.example
├── requirements.txt
└── README.md
```

---

## 快速开始（本地开发）

### 1. 环境准备

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入 Google API Key：

```bash
cp .env.example .env
# 编辑 .env，填入 GOOGLE_API_KEY
```

> 获取 API Key：https://aistudio.google.com/app/apikey

### 3. 启动 Web 服务

```bash
python api.py
# 或：python main.py serve
```

启动时会自动将 **data/*.txt** 中的火锅知识录入 ChromaDB。

- 页面：http://localhost:8080  
- API 文档：http://localhost:8080/docs  

### 4. 手动录入文档（可选）

```bash
python main.py ingest data/your_file.txt
# 指定向量库路径：python main.py ingest data/your_file.txt --persist data/chroma_data
```

---

## Web API

### `POST /api/chat`

统一对话接口，自动路由知识问答与点餐流程。

**请求：**
```json
{
  "session_id": "可选，首次为空自动生成",
  "message": "番茄锅适合减肥吗？",
  "num_guests": 2,
  "allergies": ["海鲜"],
  "broths": [{"name_cn": "番茄火锅汤底", "quantity": 1}]
}
```

**响应（知识问答 → RAG）：**
```json
{
  "session_id": "uuid",
  "reply": "番茄锅热量相对较低……",
  "source": "rag",
  "order_json": null
}
```

**响应（点餐流程 → Concierge）：**
```json
{
  "session_id": "uuid",
  "reply": "锅底：番茄锅……",
  "source": "concierge",
  "order_json": null
}
```

确认下单后返回结构化订单：
```json
{
  "session_id": "uuid",
  "reply": "已按您的要求生成订单 ✅",
  "source": "concierge",
  "order_json": {
    "broth_id": "tomato",
    "broth_name_cn": "番茄火锅汤底",
    "broths": [...],
    "items": [...],
    "num_guests": 4,
    "dipping_sauce_recipe": ["蒜泥+香油+蚝油+香菜"]
  }
}
```

### `POST /api/recommend`

按人数与过敏项生成预选食材列表，并创建/更新 session。

**请求：**
```json
{
  "num_guests": 2,
  "allergies": ["海鲜"],
  "session_id": "可选"
}
```

**响应：** `items`、`all_items`（可勾选）、`total`、`message`、`session_id`。规定：1人8样、2人10样、3人12样、4人14样、5人16样、6人17样。

### `POST /api/cart/update`

根据前端勾选更新购物车。

**请求：**
```json
{
  "session_id": "uuid",
  "cart": ["bean_sprouts", "beef_sliced", ...]
}
```

### `GET /api/health`

健康检查。

### `GET /`

前端页面（web/static/index.html）。

---

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `GOOGLE_API_KEY` | 是 | - | Google Gemini API 密钥 |
| `GEMINI_MODEL` | 否 | `gemini-2.0-flash` | Gemini 模型名称 |
| `PORT` | 否 | `8080` | Web 服务端口（Cloud Run 自动设置） |

---

## 部署到 Google Cloud Run

### 前提条件

1. [Google Cloud 账号](https://cloud.google.com/) + 已创建项目  
2. 安装 [gcloud CLI](https://cloud.google.com/sdk/docs/install)  
3. 获取 [Google API Key](https://aistudio.google.com/app/apikey)  

### 一键部署

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

gcloud run deploy hotpot-concierge \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=你的API密钥
```

### 或手动构建 Docker

```bash
docker build -t hotpot-concierge .
docker run -p 8080:8080 -e GOOGLE_API_KEY=你的key hotpot-concierge
```

Docker 启动时自动将 **data/*.txt** 录入 RAG 向量库。
