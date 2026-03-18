from pydantic import BaseModel, Field


class LlmChatRequest(BaseModel):
    data: list[str] = Field(..., min_length=1, description="A batch of string data passed to the LLM as context.")
    question: str = Field(..., min_length=1, description="The user question for the LLM.")


class LlmChatResponse(BaseModel):
    title: str
    answer: str
    model: str
    chunk_count: int
