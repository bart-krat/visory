from enum import Enum
from app.state import PlannerState, CONSTRAINTS
from app.categorize import get_categorize_service
from app.constraints import get_constraints_service, ConstraintClarification
from app.optimize import get_optimizer_service


class WorkflowPhase(str, Enum):
    COLLECT_TASKS = "collect_tasks"
    CONSTRAINTS = "constraints"
    CONSTRAINT_CLARIFICATION = "constraint_clarification"
    OPTIMIZE = "optimize"
    COMPLETE = "complete"


INITIAL_MESSAGE = "What tasks do you have on the agenda today?"


class Orchestrator:
    """Runs the planning pipeline workflow."""

    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self.state = PlannerState(session_id=session_id)
        self.phase = WorkflowPhase.COLLECT_TASKS
        self.conversation_history: list[dict] = []
        self.categorize_service = get_categorize_service()
        self.constraints_service = get_constraints_service()
        self.constraint_clarification = ConstraintClarification()
        self.optimizer_service = get_optimizer_service()

    def _persist_state(self):
        """Save current state to disk."""
        self.state.current_phase = self.phase.value
        self.state.save()

    def get_state(self) -> PlannerState:
        """Get the current state."""
        return self.state

    def get_phase(self) -> WorkflowPhase:
        """Get the current workflow phase."""
        return self.phase

    def start(self) -> str:
        """Start the workflow, return initial message."""
        self.phase = WorkflowPhase.COLLECT_TASKS
        self._persist_state()
        return INITIAL_MESSAGE

    def process_message(self, user_message: str):
        """Process a user message based on current phase.

        Args:
            user_message: The user's input.

        Yields:
            Response chunks (for streaming) or returns response string.
        """
        self.conversation_history.append({"role": "user", "content": user_message})

        if self.phase == WorkflowPhase.COLLECT_TASKS:
            yield from self._handle_collect_tasks(user_message)

        elif self.phase == WorkflowPhase.CONSTRAINTS:
            yield from self._handle_constraints(user_message)

        elif self.phase == WorkflowPhase.CONSTRAINT_CLARIFICATION:
            yield from self._handle_constraint_clarification(user_message)

        elif self.phase == WorkflowPhase.OPTIMIZE:
            yield from self._handle_optimize()

    def _handle_collect_tasks(self, user_message: str):
        """Handle the task collection phase."""
        raw_tasks = self._parse_tasks_from_message(user_message)
        self.state.raw_tasks = raw_tasks

        # Categorize tasks (returns Task objects with name, category, utility)
        self.state.tasks = self.categorize_service.categorize(raw_tasks)

        # Move to constraints phase
        self.phase = WorkflowPhase.CONSTRAINTS
        self._persist_state()

        # Stream the constraints question
        full_response = ""
        for chunk in self.constraints_service.generate_constraints_question(
            self.state.tasks
        ):
            full_response += chunk
            yield chunk

        self.conversation_history.append({"role": "assistant", "content": full_response})

    def _handle_constraints(self, user_message: str):
        """Handle the constraints gathering phase."""
        result = self.constraints_service.parse_constraints_response(
            self.state.tasks,
            user_message,
            self.conversation_history,
        )

        if result is None:
            response = "I didn't catch all the details. Could you tell me the duration for each task and your available time window (e.g., 9am to 5pm)?"
            self.conversation_history.append({"role": "assistant", "content": response})
            yield response
        else:
            tasks, time_window = result
            self.state.tasks = tasks  # Tasks now have duration filled
            self.state.time_window = time_window

            # Move to constraint clarification phase
            self.phase = WorkflowPhase.CONSTRAINT_CLARIFICATION
            self._persist_state()

            # Stream the constraint clarification question
            full_response = ""
            for chunk in self.constraint_clarification.generate_question():
                full_response += chunk
                yield chunk

            self.conversation_history.append({"role": "assistant", "content": full_response})

    def _handle_constraint_clarification(self, user_message: str):
        """Handle the constraint clarification phase."""
        constraint = self.constraint_clarification.parse_response(user_message)

        if constraint is None:
            # Default to ALL_CATEGORIES if not recognized
            constraint = CONSTRAINTS["ALL_CATEGORIES"]
            yield f"I'll use the default: **{constraint.button_label}**\n\n"

        self.state.constraint = constraint

        # Configure optimizer based on constraint
        if constraint.id == "ALL_CATEGORIES":
            self.optimizer_service.router.require_all_categories = True
        else:
            self.optimizer_service.router.require_all_categories = False

        # Move to optimize phase
        self.phase = WorkflowPhase.OPTIMIZE
        self._persist_state()

        yield from self._handle_optimize()

    def _handle_optimize(self):
        """Handle the optimization phase."""
        yield "Creating your optimized schedule...\n\n"

        # Get the optimizer type that will be selected
        router = self.optimizer_service.router
        selected_type = router._select_optimizer(self.state.tasks, self.state.time_window)
        self.state.optimizer_type = selected_type.value

        # Run the optimizer
        daily_plan = self.optimizer_service.run_optimizer(
            self.state.tasks,
            self.state.time_window,
        )
        self.state.daily_plan = daily_plan

        # Move to complete phase and persist
        self.phase = WorkflowPhase.COMPLETE
        self._persist_state()

        # Format the schedule for display
        schedule_text = self._format_schedule(daily_plan)
        yield schedule_text

        self.conversation_history.append({"role": "assistant", "content": schedule_text})

    def _format_schedule(self, daily_plan) -> str:
        """Format the daily plan as readable text."""
        lines = [
            f"Here's your optimized schedule for {daily_plan.time_window.start_time} - {daily_plan.time_window.end_time}:\n"
        ]

        for task in daily_plan.schedule:
            category_emoji = {"health": "💪", "work": "💼", "leisure": "🎮"}.get(task.category, "📌")
            lines.append(
                f"{category_emoji} {task.start_time} - {task.end_time}: {task.task} ({task.duration_minutes} min)"
            )

        lines.append(f"\nConstraint: {self.state.constraint.button_label}")
        lines.append(f"Optimizer: {self.state.optimizer_type}")
        lines.append("\nYour day is planned!")

        return "\n".join(lines)

    def _parse_tasks_from_message(self, message: str) -> list[str]:
        """Extract task list from user message."""
        lines = message.strip().split("\n")
        tasks = []
        for line in lines:
            line = line.strip()
            if line.startswith(("-", "*", "•")):
                line = line[1:].strip()
            elif len(line) > 2 and line[0].isdigit() and line[1] in ".)":
                line = line[2:].strip()
            if line:
                tasks.append(line)

        if len(tasks) == 1 and "," in tasks[0]:
            tasks = [t.strip() for t in tasks[0].split(",") if t.strip()]

        return tasks


# Session storage for orchestrators (in production, use Redis or similar)
_sessions: dict[str, Orchestrator] = {}


def get_or_create_orchestrator(session_id: str) -> Orchestrator:
    """Get existing orchestrator or create new one for session."""
    if session_id not in _sessions:
        _sessions[session_id] = Orchestrator(session_id=session_id)
    return _sessions[session_id]


def get_orchestrator(session_id: str) -> Orchestrator | None:
    """Get orchestrator for session if it exists."""
    return _sessions.get(session_id)
