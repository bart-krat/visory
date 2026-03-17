from pydantic import BaseModel


class ConversationMessage(BaseModel):
    """A single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str


class ChatMessage(BaseModel):
    """Request payload for chat endpoint."""

    content: str
    conversation_history: list[ConversationMessage] = []
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    message: str
    done: bool


class CategorizeRequest(BaseModel):
    """Request payload for categorize endpoint."""

    tasks: list[str]


class CategorizedTask(BaseModel):
    """A single categorized task."""

    task: str
    category: str  # "work", "health", or "leisure"


class CategorizeResponse(BaseModel):
    """Response from categorize endpoint."""

    categorized_tasks: list[CategorizedTask]


class WorkflowStartResponse(BaseModel):
    """Response when starting a new workflow."""

    session_id: str
    message: str
    phase: str


class WorkflowMessageRequest(BaseModel):
    """Request to send a message to the workflow."""

    session_id: str
    message: str
