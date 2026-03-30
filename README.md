# helloagents_trip_langgraph

基于 `helloagents-trip-planner` 重构的全新项目：**LangGraph 驱动的个性化旅行推荐 Agent 系统**。

核心目标：
- 用 LangGraph 的 stateful workflow 替代教程式单次调用
- 区分短期记忆（会话态）与长期记忆（用户画像）
- 支持多轮澄清、预算校验/调整、个性化重排
- 可作为面试展示项目（工程结构清晰，可运行、可扩展）

---

## 1. 为什么从原项目升级到 LangGraph

原项目（`helloagents-trip-planner`）已经具备基础的“景点/天气/酒店/规划”能力，但主要是串行调用模式。
本项目升级点：

1. 将流程抽象为图：节点职责边界更清晰，分支可控。
2. 引入状态：同一线程可累积上下文，支持多轮澄清。
3. 预算、个性化、记忆写回都进入明确节点，不再散落在单个大函数里。
4. 方便扩展到多模型、多工具、多策略路由。

---

## 2. 架构图（文字版）

```text
User Message
  |
  v
POST /api/chat/message
  |
  v
PlannerService -> LangGraph Workflow

START
  -> load_user_memory
  -> parse_user_request
  -> check_missing_info
      |--[missing]--> ask_clarification -> END
      |--[enough]--> retrieve_candidates
                     -> build_candidate_plan
                     -> personalize_rerank
                     -> budget_check
                         |--[over budget]--> budget_revise -> budget_check
                         |--[ok]----------> generate_output
                                           -> write_memory
                                           -> END
```

---

## 3. 长短期记忆设计

### 短期记忆（Short-term）
- 载体：LangGraph `PlannerState` + SessionStore（session/thread 映射）
- 粒度：`session_id / thread_id`
- 保存：当前消息、解析结果、缺失字段、候选集、计划中间态、预算状态、最终输出
- Checkpointer：默认 `memory` 模式（稳定、开箱即用），可切换 `sqlite` 模式

### 长期记忆（Long-term）
- 载体：SQLite（`profiles.sqlite` + `trips.sqlite`）
- 核心：只保存“稳定偏好画像”，不直接存整段聊天全文
- 字段示例：
  - `travel_style`
  - `hotel_budget_min/max`
  - `food_preference`
  - `attraction_preference`
  - `transport_preference`
  - `pace_preference`
  - `avoid_tags`
- 来源：
  - 用户显式输入
  - 对话偏好提炼（summarizer）
  - 反馈回写（`/api/user/feedback`）

---

## 4. 功能亮点

1. 多轮澄清：缺少城市/日期/天数/预算时不瞎猜。
2. 个性化重排：候选方案先生成，再按画像做 rerank。
3. 预算闭环：预算检查 -> 超预算自动压缩（酒店/餐饮/收费景点优先）。
4. 结构化输出：返回 `structured_plan` + `assistant_message` + `need_clarification`。
5. 长期偏好写回：每轮规划可沉淀稳定偏好，并可被后续会话复用。

---

## 5. 项目结构

```text
helloagents_trip_langgraph/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   ├── router.py
│   │   │   ├── workflow.py
│   │   │   └── nodes/
│   │   ├── memory/
│   │   ├── tools/
│   │   ├── services/
│   │   ├── schemas/
│   │   └── main.py
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   ├── run.py
│   └── README.md
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── src/main.js
└── README.md
```

---

## 6. 快速运行

### 后端

```bash
cd helloagents_trip_langgraph/backend
python -m pip install -r requirements.txt
cp .env.example .env
python run.py
```

默认接口：`http://localhost:8001`

### 前端（最小可运行版本）

```bash
cd helloagents_trip_langgraph/frontend
python -m http.server 5173
```

浏览器打开：`http://localhost:5173`

---

## 7. .env 关键配置

参考 `backend/.env.example`：
- `MOCK_MODE=true`：无外部 Key 时可本地跑通
- `CHECKPOINTER_MODE=memory`：默认稳定模式
- `LLM_API_KEY`：可选，不填时走确定性 fallback
- `AMAP_API_KEY`：mock 模式下可不填

---

## 8. API 示例

### 8.1 创建会话

`POST /api/chat/session`

```json
{
  "user_id": "user_001"
}
```

### 8.2 发送消息

`POST /api/chat/message`

```json
{
  "session_id": "...",
  "user_id": "user_001",
  "message": "我想去杭州玩3天，2026-05-01出发，预算3000元，偏好美食，地铁出行。"
}
```

返回（示意）：

```json
{
  "assistant_message": "已生成杭州3天个性化行程...",
  "structured_plan": {
    "city": "杭州",
    "days": [...],
    "budget": {...},
    "personalization_explanation": [...]
  },
  "need_clarification": false,
  "session_id": "...",
  "thread_id": "..."
}
```

### 8.3 用户画像
- `GET /api/user/profile/{user_id}`

### 8.4 用户反馈
- `POST /api/user/feedback`

### 8.5 历史行程
- `GET /api/trips/history/{user_id}`

---

## 9. 迁移说明（复用与重构）

### 复用思路
- 复用了原项目“地图/天气/酒店/餐饮/预算”能力边界
- 复用了原项目结构化行程输出思路（TripPlan/DayPlan 等）
- 保留 FastAPI 前后端交互模式

### 重构点
- 由单体串行编排重构为 LangGraph 节点图
- 新增长期记忆与画像提炼
- 新增澄清分支与预算修正分支
- 新增会话/线程模型

> 重要：原项目 `helloagents-trip-planner` 未被修改，本项目在同级目录独立实现。

---

## 10. 面试讲解亮点

1. 为什么要从“链式调用”升级到“图式编排”。
2. Stateful workflow 如何支持多轮澄清和恢复上下文。
3. 长期记忆只存“稳定偏好”而不是全量对话。
4. 个性化策略与预算策略如何解耦成独立节点。
5. 如何在无外部 API Key 下仍保证 demo 可运行（mock/fallback）。

