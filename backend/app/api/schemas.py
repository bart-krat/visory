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


class Task(BaseModel):
    """A task with all attributes for optimization."""

    name: str
    duration: int  # in minutes
    utility: float
    category: str  # "work", "health", or "leisure"
    time_slot: int | None = None  # optional fixed start time (minutes from midnight)


class TaskConstraintInput(BaseModel):
    """Input for a single task's constraints."""

    name: str
    duration: int  # in minutes (required)
    time_slot: str | None = None  # optional "HH:MM" format


class ConstraintsSubmission(BaseModel):
    """Request to submit task constraints."""

    session_id: str
    tasks: list[TaskConstraintInput]
    time_window_start: str  # "HH:MM"
    time_window_end: str    # "HH:MM"


class ScheduledTask(BaseModel):
    """A task scheduled at a specific time."""

    task: str
    category: str
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    duration_minutes: int


class DailyPlan(BaseModel):
    """The optimized daily plan."""

    schedule: list[ScheduledTask]
    time_window_start: str | None = None
    time_window_end: str | None = None
