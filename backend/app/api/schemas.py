from pydantic import BaseModel


class WorkflowStartResponse(BaseModel):
    """Response when starting a new workflow."""

    session_id: str
    message: str
    phase: str


class WorkflowMessageRequest(BaseModel):
    """Request to send a message to the workflow."""

    session_id: str
    message: str


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


class ConstraintSelectionRequest(BaseModel):
    """Request to submit selected constraints and run optimization."""

    session_id: str
    constraint_ids: list[str] = []  # List of constraint IDs (e.g., ["TASK_Go to gym"])
    custom_constraint: str | None = None  # Optional custom text constraint


class UtilityMessageRequest(BaseModel):
    """Request to send a message to the utility questionnaire."""

    session_id: str
    message: str
