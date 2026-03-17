# url4sub

基于 FastAPI 的基础项目结构，当前提供健康检查和 LLM 对话接口。

## 启动

```bash
uv sync
uv run python main.py
```

## 接口

`GET /api/v1/health`

```json
{
  "message": "service is running"
}
```

`POST /api/v1/llm/chat`

```json
{
  "data": [
    "Alice 95分",
    "Bob 88分"
  ],
  "question": "谁的分数最高？"
}
```

```json
{
  "answer": "Alice 的分数最高，为 95 分。",
  "model": "deepseek-chat"
}
```
