# url4sub

一个基于 FastAPI 的 LLM 聚合服务。当前核心能力是接收一批字符串数据和一个问题，按 OpenAI 兼容协议调用 DeepSeek，并在大数据量场景下自动分片、并发处理、最终汇总答案。

## 项目逻辑

### 1. 接口入口

当前提供两个接口：

- `GET /api/v1/health`
- `POST /api/v1/llm/chat`

其中 `POST /api/v1/llm/chat` 是核心接口，入参为：

```json
{
  "data": [
    "字符串数据1",
    "字符串数据2"
  ],
  "question": "基于这些数据回答的问题"
}
```

返回：

```json
{
  "answer": "LLM 最终生成的答案",
  "model": "deepseek-chat",
  "chunk_count": 1
}
```

### 2. 核心处理流程

`/api/v1/llm/chat` 的执行流程如下：

1. 校验请求参数
   - `data` 必须是字符串数组，且至少有 1 条
   - `question` 不能为空
2. 校验总输入大小
   - 统计 `data` 所有字符串长度与 `question` 长度
   - 超过 `LLM_TOTAL_MAX_CHARS` 时直接返回 `400`
3. 自动分片
   - 按 `LLM_CHUNK_MAX_CHARS` 将 `data` 切成多个 chunk
   - 单条过长数据会单独作为一个 chunk
4. 分片并发调用 LLM
   - 每个 chunk 单独请求 DeepSeek 的 `chat/completions`
   - 并发数由 `LLM_CHUNK_CONCURRENCY` 控制
5. 分片失败重试
   - 每个 LLM 请求失败后会按配置自动重试
   - 重试次数由 `LLM_REQUEST_RETRIES` 控制
   - 重试间隔由 `LLM_RETRY_BACKOFF_SECONDS` 控制
6. 最终汇总
   - 如果只有一个 chunk，直接返回该 chunk 的回答
   - 如果有多个 chunk，再发起一次汇总请求，将所有 chunk 回答合并成最终答案

### 3. 调用的 LLM 协议

服务通过 OpenAI 兼容格式调用 DeepSeek：

- Base URL: `https://api.deepseek.com/v1`
- Endpoint: `/chat/completions`
- Model: `deepseek-chat`

每次请求都会发送：

- `model`
- `messages`
  - `system`
  - `user`

### 4. 错误处理

- 输入过大：返回 `400`
- 上游 LLM 请求失败：返回 `502`

## 配置

项目通过 `.env` 读取配置，示例文件见 [`.env.example`](/E:/url4sub/.env.example)。

当前主要配置项：

```env
APP_NAME=url4sub
APP_VERSION=0.1.0
API_V1_PREFIX=/api/v1

LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=deepseek-chat
LLM_CHUNK_MAX_CHARS=8000
LLM_CHUNK_CONCURRENCY=3
LLM_TOTAL_MAX_CHARS=100000
LLM_REQUEST_RETRIES=2
LLM_RETRY_BACKOFF_SECONDS=1.0
```

说明：

- `LLM_CHUNK_MAX_CHARS`：每个分片最大字符数
- `LLM_CHUNK_CONCURRENCY`：分片并发调用数
- `LLM_TOTAL_MAX_CHARS`：单次请求允许的最大总字符数
- `LLM_REQUEST_RETRIES`：单次调用失败后的重试次数
- `LLM_RETRY_BACKOFF_SECONDS`：重试退避基数

## 启动

```bash
uv sync
uv run python main.py
```

启动后可访问：

- Swagger 文档：`http://127.0.0.1:8000/docs`
- OpenAPI：`http://127.0.0.1:8000/openapi.json`

## 调用示例

### Health Check

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### LLM 接口

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/llm/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "Alice 95分",
      "Bob 88分",
      "Cindy 91分"
    ],
    "question": "谁的分数最高？"
  }'
```

返回示例：

```json
{
  "answer": "Alice 的分数最高，为 95 分。",
  "model": "deepseek-chat",
  "chunk_count": 1
}
```

## 代码结构

```text
.
├── app
│   ├── api
│   │   └── routes
│   │       ├── health.py
│   │       └── llm.py
│   ├── core
│   │   └── config.py
│   ├── schemas
│   │   ├── health.py
│   │   └── llm.py
│   ├── services
│   │   └── llm.py
│   └── main.py
├── .env.example
├── main.py
├── pyproject.toml
└── README.md
```
