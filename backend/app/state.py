from dataclasses import dataclass, field


@dataclass
class CategorizedTask:
    """A task with its assigned category."""
    task: str
    category: str  # "work", "health", or "leisure"


@dataclass
class TaskWithDuration:
    """A categorized task with estimated duration."""
    task: str
    category: str
    duration_minutes: int


@dataclass
class TimeWindow:
    """Available time window for the day."""
    start_time: str  # e.g. "09:00"
    end_time: str    # e.g. "18:00"


@dataclass
class ScheduledTask:
    """A task scheduled at a specific time."""
    task: str
    category: str
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    duration_minutes: int


@dataclass
class DailyPlan:
    """The optimized daily plan."""
    schedule: list[ScheduledTask] = field(default_factory=list)
    time_window: TimeWindow | None = None


@dataclass
class PlannerState:
    """Holds the state of the planning workflow."""
    raw_tasks: list[str] = field(default_factory=list)
    categorized_tasks: list[CategorizedTask] = field(default_factory=list)
    tasks_with_duration: list[TaskWithDuration] = field(default_factory=list)
    time_window: TimeWindow | None = None
    daily_plan: DailyPlan | None = None
