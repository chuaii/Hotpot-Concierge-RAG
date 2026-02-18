# 🍲 智能火锅点餐顾问 + RAG 知识问答

基于 **LangChain + Google Gemini + LangGraph + ChromaDB + FastAPI** 实现的 Web 应用。

- **RAG 知识问答**：火锅知识文档录入向量数据库（ChromaDB），用户提问时检索相关内容并由 Gemini 生成答案。
- **智能点餐顾问**：LangGraph 多轮对话引导（辣度、忌口、预算、人数）→ 菜品推荐 → 结构化厨房订单 JSON。
- **前置路由**：API 自动识别「知识问题」与「点餐请求」，分别走 RAG 或 Concierge。
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
  ├─ 知识类问题（"肥牛涮多久？"） → RAG 检索 + Gemini 生成答案
  └─ 点餐请求（"微辣、4人、预算200"） → LangGraph Concierge 多轮对话
                                           └─ 确认 → Pydantic 结构化订单
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

复制 `.env.example` 为 `.env`，填入你的 Google API Key：

```bash
cp .env.example .env
# 编辑 .env，填入 GOOGLE_API_KEY
```

> 获取 API Key：https://aistudio.google.com/app/apikey

### 3. 启动 Web 服务

```bash
python api.py
```

服务启动时会自动将 `sample.txt` 中的火锅知识录入 ChromaDB 向量数据库。

浏览器打开 http://localhost:8080 即可使用。

API 文档：http://localhost:8080/docs

### 4. 手动录入文档（可选）

```bash
python main.py ingest your_file.txt
```

---

## Web API 接口

### `POST /api/chat`

统一对话接口，自动路由知识问答与点餐流程。

**请求：**
```json
{
  "session_id": "可选，首次为空自动生成",
  "message": "番茄锅适合减肥吗？"
}
```

**响应（知识问答 → RAG）：**
```json
{
  "session_id": "uuid",
  "reply": "番茄锅热量相对较低，富含番茄红素，是注重健康的食客首选……",
  "source": "rag",
  "order_json": null
}
```

**响应（点餐流程 → Concierge）：**
```json
{
  "session_id": "uuid",
  "reply": "锅底：番茄锅（¥28）\n  - 肥牛片 × 6份（¥228）\n……",
  "source": "concierge",
  "order_json": null
}
```

确认下单后，`order_json` 包含结构化订单：
```json
{
  "session_id": "uuid",
  "reply": "已按您的要求生成订单 ✅",
  "source": "concierge",
  "order_json": {
    "broth_id": "spicy_sichuan",
    "broth_name_cn": "麻辣锅",
    "items": [...],
    "total_estimate": 186.5,
    "num_guests": 4,
    "dipping_sauce_recipe": ["蒜泥+香油+蚝油+香菜"]
  }
}
```

### `GET /api/health`

健康检查。

---

## 部署到 Google Cloud Run

### 前提条件

1. [Google Cloud 账号](https://cloud.google.com/) + 已创建项目
2. 安装 [gcloud CLI](https://cloud.google.com/sdk/docs/install)
3. 获取 [Google API Key](https://aistudio.google.com/app/apikey)

### 一键部署

```bash
# ① 登录 & 设置项目
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# ② 构建并部署
gcloud run deploy hotpot-concierge \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=你的API密钥

# ③ 完成！控制台会输出 URL
```

### 或手动构建 Docker

```bash
docker build -t hotpot-concierge .
docker run -p 8080:8080 -e GOOGLE_API_KEY=你的key hotpot-concierge
```

---

## 项目结构

```
RAG/
├── api.py                  # FastAPI 后端（前置路由 + RAG + Concierge）
├── rag.py                  # RAG 核心（LangChain 检索链 + ChromaDB + Gemini）
├── llm.py                  # 统一 LLM 工厂（Google Gemini）
├── main.py                 # CLI 入口（ingest / serve）
├── sample.txt              # 火锅知识文档（启动时自动录入 RAG）
├── concierge/              # 智能点餐顾问
│   ├── state.py            # OrderState（LangGraph）
│   ├── graph.py            # Profiler → Inventory → Reviewer
│   ├── schemas.py          # Pydantic：MenuItem, HotpotOrder
│   ├── menu_loader.py      # 菜单与价格加载
│   ├── menu_generator.py   # 结构化订单生成（含蘸料）
│   ├── sauce_pairing.py    # 风味图谱蘸料推荐
│   └── tools.py            # 工具封装
├── static/
│   └── index.html          # 前端聊天界面
├── data/
│   ├── hotpot_menu.json    # 菜单数据
│   └── sauce_pairing_rules.json  # 蘸料规则
├── Dockerfile              # Cloud Run 部署镜像
├── .dockerignore
├── .env.example
├── requirements.txt
└── README.md
```

---

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `GOOGLE_API_KEY` | 是 | - | Google Gemini API 密钥 |
| `GEMINI_MODEL` | 否 | `gemini-2.0-flash` | Gemini 模型名称 |
| `PORT` | 否 | `8080` | Web 服务端口（Cloud Run 自动设置） |
