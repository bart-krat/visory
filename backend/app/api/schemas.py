import re
from pydantic import BaseModel, field_validator, model_validator


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

    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v):
        if v <= 0:
            raise ValueError('Duration must be positive')
        if v > 1440:  # 24 hours
            raise ValueError('Duration cannot exceed 1440 minutes (24 hours)')
        return v

    @field_validator('time_slot')
    @classmethod
    def validate_time_slot(cls, v):
        if v is None:
            return v
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('time_slot must be in HH:MM format (24-hour)')
        return v


class ConstraintsSubmission(BaseModel):
    """Request to submit task constraints."""

    session_id: str
    tasks: list[TaskConstraintInput]
    time_window_start: str  # "HH:MM"
    time_window_end: str    # "HH:MM"

    @field_validator('time_window_start', 'time_window_end')
    @classmethod
    def validate_time_format(cls, v):
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('Time must be in HH:MM format (24-hour)')
        return v

    @model_validator(mode='after')
    def validate_time_window(self):
        """Ensure end time is after start time."""
        start_h, start_m = map(int, self.time_window_start.split(':'))
        end_h, end_m = map(int, self.time_window_end.split(':'))
        start_mins = start_h * 60 + start_m
        end_mins = end_h * 60 + end_m

        if end_mins <= start_mins:
            raise ValueError(
                'time_window_end must be after time_window_start. '
                'Overnight windows are not supported.'
            )

        window_duration = end_mins - start_mins
        if window_duration < 30:
            raise ValueError('Time window must be at least 30 minutes')

        return self


class ConstraintSelectionRequest(BaseModel):
    """Request to submit selected constraints and run optimization."""

    session_id: str
    constraint_ids: list[str] = []  # List of constraint IDs (e.g., ["TASK_Go to gym"])
    custom_constraint: str | None = None  # Optional custom text constraint


class UtilityMessageRequest(BaseModel):
    """Request to send a message to the utility questionnaire."""

    session_id: str
    message: str
