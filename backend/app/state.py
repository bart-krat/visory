import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime


# Utility mapping by category
CATEGORY_UTILITY = {
    "health": 70.0,
    "work": 80.0,
    "leisure": 85.0,
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
    category: str  # "work", "health", or "leisure"
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


@dataclass
class Constraint:
    """A user-selected optimization constraint."""
    id: str           # Unique identifier
    name: str         # Display name
    description: str  # What this constraint does
    button_label: str  # Short label for UI buttons


# Registry of available constraints - add new options here
CONSTRAINTS: dict[str, Constraint] = {
    "ALL_CATEGORIES": Constraint(
        id="ALL_CATEGORIES",
        name="All Categories",
        description="At least one task from each category (health, work, leisure) must be in the plan",
        button_label="At least one of each category",
    ),
    "NONE": Constraint(
        id="NONE",
        name="No Constraints",
        description="No specific constraints - optimize purely for utility",
        button_label="No constraints",
    ),
}


@dataclass
class PlannerState:
    """Holds the state of the planning workflow."""
    session_id: str = ""
    current_phase: str = "collect_tasks"
    raw_tasks: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    time_window: TimeWindow | None = None
    constraint: Constraint | None = None
    daily_plan: DailyPlan | None = None
    optimizer_type: str | None = None  # Which optimizer was selected
    updated_at: str = ""

    def to_dict(self) -> dict:
        """Convert state to JSON-serializable dict."""
        return {
            "session_id": self.session_id,
            "current_phase": self.current_phase,
            "updated_at": self.updated_at,
            "raw_tasks": self.raw_tasks,
            "tasks": [asdict(t) for t in self.tasks],
            "time_window": asdict(self.time_window) if self.time_window else None,
            "constraint": asdict(self.constraint) if self.constraint else None,
            "optimizer_type": self.optimizer_type,
            "daily_plan": {
                "schedule": [asdict(s) for s in self.daily_plan.schedule],
                "time_window": asdict(self.daily_plan.time_window) if self.daily_plan.time_window else None,
            } if self.daily_plan else None,
        }

    def save(self, directory: str = "state") -> Path:
        """Persist state to JSON file.

        Args:
            directory: Directory to save state files.

        Returns:
            Path to the saved file.
        """
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
            current_phase=data.get("current_phase", "collect_tasks"),
            raw_tasks=data.get("raw_tasks", []),
            optimizer_type=data.get("optimizer_type"),
            updated_at=data.get("updated_at", ""),
        )

        # Reconstruct tasks
        for t in data.get("tasks", []):
            state.tasks.append(Task(**t))

        # Reconstruct time_window
        if data.get("time_window"):
            state.time_window = TimeWindow(**data["time_window"])

        # Reconstruct constraint
        if data.get("constraint"):
            state.constraint = Constraint(**data["constraint"])

        # Reconstruct daily_plan
        if data.get("daily_plan"):
            dp = data["daily_plan"]
            state.daily_plan = DailyPlan(
                schedule=[ScheduledTask(**s) for s in dp.get("schedule", [])],
                time_window=TimeWindow(**dp["time_window"]) if dp.get("time_window") else None,
            )

        return state
