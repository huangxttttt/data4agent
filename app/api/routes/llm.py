from fastapi import APIRouter, HTTPException
from httpx import HTTPError

from app.schemas.llm import LlmChatRequest, LlmChatResponse
from app.services.llm import LlmInputTooLargeError, generate_llm_reply

router = APIRouter()


@router.post("/chat", response_model=LlmChatResponse, summary="Ask LLM with batch data")
async def llm_chat(request: LlmChatRequest) -> LlmChatResponse:
    try:
        answer, model, chunk_count = await generate_llm_reply(request.data, request.question)
    except LlmInputTooLargeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    return LlmChatResponse(answer=answer, model=model, chunk_count=chunk_count)
