import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime


# Default utility mapping by category (used if questionnaire skipped)
DEFAULT_UTILITY_WEIGHTS = {
    "health": 100.0,
    "work": 100.0,
    "personal": 100.0,
}


@dataclass
class Task:
    """A task flowing through the planning pipeline.

    Lifecycle:
    1. Categorizer: sets name, category, utility (duration=0)
    2. Constraints: fills in duration and optional time_slot
    3. Optimizer: uses complete task for scheduling
    """
    name: str
    category: str  # "work", "health", or "personal"
    utility: float = 0.0
    duration: int = 0  # in minutes, filled by constraints phase
    time_slot: int | None = None  # optional fixed start time (minutes from midnight)


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


# =============================================================================
# Typed Constraint Model
# =============================================================================
# These represent the actual constraint semantics that optimizers understand.

@dataclass
class MustIncludeTask:
    """Specific task must be included in the plan."""
    task_name: str

    def __str__(self) -> str:
        return f"Must include '{self.task_name}'"


@dataclass
class MustIncludeCategory:
    """At least one task from this category must be included."""
    category: str  # "health", "work", or "personal"

    def __str__(self) -> str:
        return f"Must include a {self.category} task"


@dataclass
class FixedTimeSlot:
    """Task must be scheduled at a specific time."""
    task_name: str
    start_time: int  # minutes from midnight (e.g., 840 = 14:00)

    def __str__(self) -> str:
        h, m = divmod(self.start_time, 60)
        return f"'{self.task_name}' at {h:02d}:{m:02d}"


@dataclass
class OrderedAfter:
    """Task must be scheduled after another task."""
    task_name: str
    after_task: str  # The task that must come before

    def __str__(self) -> str:
        return f"'{self.task_name}' after '{self.after_task}'"


# Union of all constraint types
ConstraintType = MustIncludeTask | MustIncludeCategory | FixedTimeSlot | OrderedAfter


@dataclass
class ConstraintSet:
    """A collection of typed constraints with helper methods."""
    constraints: list[ConstraintType] = field(default_factory=list)

    def add(self, constraint: ConstraintType) -> None:
        """Add a constraint to the set."""
        self.constraints.append(constraint)

    @property
    def mandatory_tasks(self) -> set[str]:
        """Extract mandatory task names."""
        return {c.task_name for c in self.constraints if isinstance(c, MustIncludeTask)}

    @property
    def mandatory_categories(self) -> set[str]:
        """Extract mandatory categories."""
        return {c.category for c in self.constraints if isinstance(c, MustIncludeCategory)}

    @property
    def fixed_slots(self) -> dict[str, int]:
        """Extract fixed time slots as {task_name: start_time}."""
        return {c.task_name: c.start_time for c in self.constraints if isinstance(c, FixedTimeSlot)}

    @property
    def ordering_constraints(self) -> list[tuple[str, str]]:
        """Extract ordering as [(before, after), ...]."""
        return [(c.after_task, c.task_name) for c in self.constraints if isinstance(c, OrderedAfter)]

    def has_complex_constraints(self) -> bool:
        """Check if constraints require EnumerationOptimizer."""
        return bool(self.fixed_slots or self.ordering_constraints)

    def is_empty(self) -> bool:
        """Check if there are no constraints."""
        return len(self.constraints) == 0

    def describe(self) -> str:
        """Human-readable description of all constraints."""
        if not self.constraints:
            return "No constraints"
        return "; ".join(str(c) for c in self.constraints)

    def to_dict(self) -> list[dict]:
        """Serialize constraints to JSON-compatible format."""
        result = []
        for c in self.constraints:
            if isinstance(c, MustIncludeTask):
                result.append({"type": "must_include_task", "task_name": c.task_name})
            elif isinstance(c, MustIncludeCategory):
                result.append({"type": "must_include_category", "category": c.category})
            elif isinstance(c, FixedTimeSlot):
                result.append({"type": "fixed_time_slot", "task_name": c.task_name, "start_time": c.start_time})
            elif isinstance(c, OrderedAfter):
                result.append({"type": "ordered_after", "task_name": c.task_name, "after_task": c.after_task})
        return result

    @classmethod
    def from_dict(cls, data: list[dict]) -> "ConstraintSet":
        """Deserialize constraints from JSON format."""
        cs = cls()
        for item in data:
            ctype = item.get("type")
            if ctype == "must_include_task":
                cs.add(MustIncludeTask(task_name=item["task_name"]))
            elif ctype == "must_include_category":
                cs.add(MustIncludeCategory(category=item["category"]))
            elif ctype == "fixed_time_slot":
                cs.add(FixedTimeSlot(task_name=item["task_name"], start_time=item["start_time"]))
            elif ctype == "ordered_after":
                cs.add(OrderedAfter(task_name=item["task_name"], after_task=item["after_task"]))
        return cs


# =============================================================================
# Legacy UI Constraint (for backward compatibility)
# =============================================================================

@dataclass
class UIConstraint:
    """A UI button representation of a constraint (legacy)."""
    id: str           # Unique identifier
    name: str         # Display name
    description: str  # What this constraint does
    button_label: str  # Short label for UI buttons


@dataclass
class PlannerState:
    """Holds the state of the planning workflow."""
    session_id: str = ""
    current_phase: str = "questionnaire"
    utility_weights: dict[str, float] = field(default_factory=lambda: DEFAULT_UTILITY_WEIGHTS.copy())
    questionnaire_answers: list[dict] = field(default_factory=list)
    raw_tasks: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    time_window: TimeWindow | None = None
    daily_plan: DailyPlan | None = None
    optimizer_type: str | None = None
    updated_at: str = ""

    def to_dict(self) -> dict:
        """Convert state to JSON-serializable dict."""
        return {
            "session_id": self.session_id,
            "current_phase": self.current_phase,
            "updated_at": self.updated_at,
            "utility_weights": self.utility_weights,
            "questionnaire_answers": self.questionnaire_answers,
            "raw_tasks": self.raw_tasks,
            "tasks": [asdict(t) for t in self.tasks],
            "time_window": asdict(self.time_window) if self.time_window else None,
            "optimizer_type": self.optimizer_type,
            "daily_plan": {
                "schedule": [asdict(s) for s in self.daily_plan.schedule],
                "time_window": asdict(self.daily_plan.time_window) if self.daily_plan.time_window else None,
            } if self.daily_plan else None,
        }

    def save(self, directory: str = "state") -> Path:
        """Persist state to JSON file."""
        self.updated_at = datetime.now().isoformat()

        dir_path = Path(directory)
        dir_path.mkdir(exist_ok=True)

        filename = f"{self.session_id}.json" if self.session_id else "state.json"
        file_path = dir_path / filename

        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return file_path

    @classmethod
    def load(cls, filepath: str) -> "PlannerState":
        """Load state from JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        state = cls(
            session_id=data.get("session_id", ""),
            current_phase=data.get("current_phase", "questionnaire"),
            utility_weights=data.get("utility_weights", DEFAULT_UTILITY_WEIGHTS.copy()),
            questionnaire_answers=data.get("questionnaire_answers", []),
            raw_tasks=data.get("raw_tasks", []),
            optimizer_type=data.get("optimizer_type"),
            updated_at=data.get("updated_at", ""),
        )

        for t in data.get("tasks", []):
            state.tasks.append(Task(**t))

        if data.get("time_window"):
            state.time_window = TimeWindow(**data["time_window"])

        if data.get("daily_plan"):
            dp = data["daily_plan"]
            state.daily_plan = DailyPlan(
                schedule=[ScheduledTask(**s) for s in dp.get("schedule", [])],
                time_window=TimeWindow(**dp["time_window"]) if dp.get("time_window") else None,
            )

        return state
