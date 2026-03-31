import uuid
import time
from fastapi import APIRouter
from dishka.integrations.fastapi import FromDishka, inject

from src.presentation.api.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ChatChoice,
    Usage,
)
from src.application.use_cases.answer_question import AnswerQuestionUseCase
from src.domain.models.search import SearchMode

router = APIRouter(prefix="/v1/chat", tags=["Chat"])


@router.post("/completions", response_model=ChatCompletionResponse)
@inject
async def create_chat_completion(
    request: ChatCompletionRequest, use_case: FromDishka[AnswerQuestionUseCase]
):
    user_message = next(
        (m.content for m in reversed(request.messages) if m.role == "user"), ""
    )
    if not user_message:
        raise ValueError("No user message found")

    mode_str = request.model.split("-")[-1] if "-" in request.model else "hybrid"
    try:
        search_mode = SearchMode(mode_str)
    except ValueError:
        search_mode = SearchMode.HYBRID

    response = await use_case.execute(
        question=user_message, mode=search_mode, top_k=request.top_k or 10
    )

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatChoice(
                index=0, message=ChatMessage(role="assistant", content=response.answer)
            )
        ],
        usage=Usage(),
        sources=[s.model_dump() for s in response.sources],
        context_stats=response.context_stats,
    )
