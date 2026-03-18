import asyncio

import httpx

from app.core.config import settings


CHUNK_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the question based on the provided batch data chunk. "
    "Use only the supplied content. If the chunk is insufficient, say so clearly."
)
FINAL_SYSTEM_PROMPT = (
    "You are a helpful assistant. Combine the chunk-level answers into one final answer. "
    "Remove duplication, keep the answer concise, and say clearly if the source chunks are insufficient."
)
TITLE_SYSTEM_PROMPT = (
    "You are a helpful assistant. Generate a short Chinese title primarily based on the provided source data. "
    "The title must reflect the main theme of the data itself, not just restate the question or answer. "
    "Keep it within 8 to 16 Chinese characters when possible, avoid punctuation, and return only the title."
)


class LlmInputTooLargeError(ValueError):
    """Raised when the total input size exceeds the configured limit."""


def _build_chunked_data(data: list[str], max_chars: int) -> list[list[str]]:
    chunks: list[list[str]] = []
    current_chunk: list[str] = []
    current_size = 0

    for item in data:
        item_size = len(item)
        if item_size >= max_chars:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0
            chunks.append([item])
            continue

        if current_chunk and current_size + item_size > max_chars:
            chunks.append(current_chunk)
            current_chunk = [item]
            current_size = item_size
            continue

        current_chunk.append(item)
        current_size += item_size

    if current_chunk:
        chunks.append(current_chunk)

    return chunks or [[]]


def _validate_total_input_size(data: list[str], question: str) -> None:
    total_chars = sum(len(item) for item in data) + len(question)
    if total_chars > settings.llm_total_max_chars:
        raise LlmInputTooLargeError(
            f"Total input chars {total_chars} exceed limit {settings.llm_total_max_chars}"
        )


async def _call_chat_completion(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_content: str,
) -> tuple[str, str]:
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    retries = max(settings.llm_request_retries, 0)
    last_error: httpx.HTTPError | None = None

    for attempt in range(retries + 1):
        try:
            response = await client.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            response_data = response.json()
            message = response_data["choices"][0]["message"]["content"]
            model = response_data.get("model", settings.llm_model)
            return message, model
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt >= retries:
                break
            await asyncio.sleep(settings.llm_retry_backoff_seconds * (attempt + 1))

    assert last_error is not None
    raise last_error


async def _generate_title(
    client: httpx.AsyncClient,
    data: list[str],
    question: str,
    answer: str,
) -> tuple[str, str]:
    source_data = "\n".join(f"{index}. {item}" for index, item in enumerate(data, start=1))
    user_content = f"Source data:\n{source_data}\n\nQuestion:\n{question}\n\nAnswer:\n{answer}"
    return await _call_chat_completion(client, TITLE_SYSTEM_PROMPT, user_content)


async def generate_llm_reply(data: list[str], question: str) -> tuple[str, str, str, int]:
    _validate_total_input_size(data, question)
    chunks = _build_chunked_data(data, settings.llm_chunk_max_chars)
    model = settings.llm_model
    semaphore = asyncio.Semaphore(max(settings.llm_chunk_concurrency, 1))

    async def run_chunk(
        client: httpx.AsyncClient,
        index: int,
        chunk: list[str],
    ) -> tuple[int, str, str]:
        batch_data = "\n".join(f"{item_index}. {item}" for item_index, item in enumerate(chunk, start=1))
        user_content = (
            f"Chunk {index}/{len(chunks)}\n"
            f"Batch data:\n{batch_data}\n\n"
            f"Question:\n{question}"
        )
        async with semaphore:
            chunk_answer, chunk_model = await _call_chat_completion(client, CHUNK_SYSTEM_PROMPT, user_content)
        return index, chunk_answer, chunk_model

    async with httpx.AsyncClient(timeout=60.0) as client:
        chunk_results = await asyncio.gather(
            *(run_chunk(client, index, chunk) for index, chunk in enumerate(chunks, start=1))
        )

        chunk_results.sort(key=lambda item: item[0])
        chunk_answers = []
        for index, chunk_answer, chunk_model in chunk_results:
            model = chunk_model
            chunk_answers.append(f"Chunk {index} answer:\n{chunk_answer}")

        if len(chunk_answers) == 1:
            final_answer = chunk_answers[0].split("\n", 1)[1]
        else:
            summary_content = (
                "The following are answers generated from multiple data chunks.\n\n"
                f"{'\n\n'.join(chunk_answers)}\n\n"
                f"Final question:\n{question}"
            )
            final_answer, model = await _call_chat_completion(client, FINAL_SYSTEM_PROMPT, summary_content)

        title, title_model = await _generate_title(client, data, question, final_answer)
        model = title_model

    return title.strip(), final_answer, model, len(chunks)
