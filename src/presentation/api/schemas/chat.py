from pydantic import BaseModel

from domain.models.search import SearchMode


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "graphrag-hybrid"
    search_mode: SearchMode | None = None
    messages: list[ChatMessage]
    temperature: float | None = 0.7
    top_k: int | None = 10


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: Usage
    sources: list[dict] = []
    context_stats: dict = {}
