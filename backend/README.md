# Backend - helloagents_trip_langgraph

## 技术栈
- Python + FastAPI
- LangGraph（主流程编排）
- Pydantic / Pydantic Settings
- SQLite（用户画像 + 行程历史）

## 核心目录

- `app/main.py`：FastAPI 应用入口
- `app/api/routes/`：HTTP 路由
- `app/graph/workflow.py`：LangGraph 主流程组装
- `app/graph/nodes/`：每个节点一个文件，职责单一
- `app/memory/`：短期会话存储、长期画像与历史存储
- `app/tools/`：地图/天气/酒店/餐饮/预算/记忆工具
- `app/services/`：会话与规划调度、依赖容器

## LangGraph 节点职责

1. `load_user_memory`
- 读取长期用户画像

2. `parse_user_request`
- 解析用户输入，合并多轮上下文

3. `check_missing_info`
- 判断是否缺关键字段

4. `ask_clarification`
- 生成追问语句并终止当前轮

5. `retrieve_candidates`
- 调用工具拿候选数据（景点、天气、酒店、餐饮）

6. `build_candidate_plan`
- 组装初稿行程

7. `personalize_rerank`
- 按偏好进行个性化重排

8. `budget_check`
- 预算汇总与超预算判定

9. `budget_revise`
- 超预算时自动降本

10. `generate_output`
- 生成 assistant_message + structured_plan

11. `write_memory`
- 偏好写回 + 历史写入

## 运行

```bash
pip install -r requirements.txt
cp .env.example .env
python run.py
```

## 测试

```bash
pytest -q
```

当前用例：
- 完整规划链路（无澄清）
- 澄清分支
- 反馈更新长期画像

## Demo

```bash
python tests/demo_run.py
```

## 可扩展方向

- 将 `checkpointer_mode` 切换到 `sqlite` 做跨进程状态恢复
- 将 `PreferenceSummarizer` 升级为 LLM + 规则混合提炼
- 将长期存储从 SQLite 迁移到 PostgreSQL
- 为工具层增加真实供应商 API 适配器（地图/酒店/餐饮）
