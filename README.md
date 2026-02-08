# 🍲 智能火锅点餐顾问 + RAG 系统

基于 **LangChain + Google Gemini + LangGraph + FastAPI** 实现。

- **RAG 问答**：读取文本存入向量数据库，检索并回答问题。
- **火锅点餐顾问**：多轮对话引导（辣度、忌口、预算、人数）→ 生成推荐方案 → 输出标准化厨房订单 JSON。
- **Web 界面**：前后端一体，可直接部署到 **Google Cloud Run**，客人通过浏览器/谷歌地图链接使用。

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| LLM | **Google Gemini** (gemini-2.0-flash) | 通过 `langchain-google-genai` 调用 |
| 编排 | **LangGraph** | 多轮对话状态机：Profiler → Inventory → Reviewer |
| 结构化输出 | **Pydantic** | `MenuItem` / `HotpotOrder` 保证订单可校验 |
| 向量检索 | **ChromaDB** + **HuggingFace Embeddings** | RAG 文本检索 |
| 蘸料推荐 | 风味图谱规则 | 锅底标签 + 食材标签 → 蘸料配方 |
| Web 服务 | **FastAPI** + **Uvicorn** | REST API + 静态前端 |
| 部署 | **Docker** + **Google Cloud Run** | 一键部署到云端 |

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

浏览器打开 http://localhost:8080 即可使用聊天界面。

API 文档：http://localhost:8080/docs

### 4. 命令行使用（可选）

```bash
# RAG：录入文本
python main.py ingest sample.txt

# RAG：提问
python main.py ask "RAG 是什么？"

# 火锅顾问（简单问答）
python main.py hotpot "哪个锅底最受欢迎？"
python main.py hotpot "How much beef for 4 people?" --guests 4

# 火锅顾问（多轮对话 - 终端版）
python run_concierge.py
```

---

## Web API 接口

### `POST /api/chat`

多轮对话接口，支持 session。

**请求：**
```json
{
  "session_id": "可选，首次为空自动生成",
  "message": "微辣、不吃羊肉、预算200元、4个人"
}
```

**响应：**
```json
{
  "session_id": "uuid",
  "reply": "顾问回复文本",
  "order_json": null
}
```

当用户发送"确认"后，`order_json` 中会包含结构化订单：

```json
{
  "session_id": "uuid",
  "reply": "已按您的要求生成订单 ✅",
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

### 一键部署（3 步）

```bash
# ① 登录 & 设置项目
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# ② 构建并部署（Cloud Run 会自动构建 Docker 镜像）
gcloud run deploy hotpot-concierge \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=你的API密钥

# ③ 完成！控制台会输出 URL，如：
# https://hotpot-concierge-xxxxx-de.a.run.app
```

> **注意**：`--source .` 会自动使用项目中的 `Dockerfile` 构建镜像并推送到 Container Registry，无需手动 `docker build`。

### 或者手动构建 Docker

```bash
# 本地构建
docker build -t hotpot-concierge .

# 本地测试
docker run -p 8080:8080 -e GOOGLE_API_KEY=你的key hotpot-concierge

# 推送到 Google Container Registry
docker tag hotpot-concierge gcr.io/YOUR_PROJECT_ID/hotpot-concierge
docker push gcr.io/YOUR_PROJECT_ID/hotpot-concierge

# 部署到 Cloud Run
gcloud run deploy hotpot-concierge \
  --image gcr.io/YOUR_PROJECT_ID/hotpot-concierge \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=你的API密钥
```

### 绑定自定义域名（可选）

```bash
gcloud run domain-mappings create \
  --service hotpot-concierge \
  --domain hotpot.yourdomain.com \
  --region asia-east1
```

### 放到谷歌地图

1. 登录 [Google 商家资料](https://business.google.com/)
2. 编辑你的火锅店信息 → 「网站」字段填入 Cloud Run 生成的 URL
3. 客人在谷歌地图搜到你的店后，点击链接即可直接使用点餐顾问

---

## 项目结构

```
RAG/
├── api.py                  # FastAPI Web 后端（/api/chat + session 管理）
├── llm.py                  # 统一 LLM 工厂（Google Gemini）
├── rag.py                  # RAG 核心（LangChain 检索链 + Gemini）
├── hotpot_advisor.py       # 火锅顾问（简单问答）
├── main.py                 # 命令行入口
├── run_concierge.py        # 终端多轮对话入口
├── concierge/              # Agentic Hotpot Concierge
│   ├── state.py            # OrderState（LangGraph）
│   ├── graph.py            # Profiler → Inventory → Reviewer（Gemini）
│   ├── schemas.py          # Pydantic：MenuItem, HotpotOrder
│   ├── menu_loader.py      # 菜单与价格加载
│   ├── menu_generator.py   # 生成 HotpotOrder（含蘸料）
│   ├── sauce_pairing.py    # 风味图谱蘸料推荐
│   └── tools.py            # ADK 工具封装
├── static/
│   └── index.html          # 前端聊天界面
├── data/
│   ├── hotpot_menu.json
│   └── sauce_pairing_rules.json
├── Dockerfile              # Cloud Run 部署镜像
├── .dockerignore
├── .env.example            # 环境变量模板
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
