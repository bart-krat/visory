"""Orchestrator - runs the planning pipeline workflow."""
from enum import Enum
from app.state import (
    PlannerState,
    ConstraintSet,
    MustIncludeTask,
    FixedTimeSlot,
)
from app.categorize import get_categorize_service
from app.constraints import get_constraints_service, ConstraintClarification, get_constraint_matcher
from app.optimize import get_optimizer_service
from app.results import get_results_service


class WorkflowPhase(str, Enum):
    WELCOME = "welcome"
    QUESTIONNAIRE = "questionnaire"
    EVALUATION = "evaluation"
    COLLECT_TASKS = "collect_tasks"
    CONSTRAINTS = "constraints"
    CONSTRAINT_CLARIFICATION = "constraint_clarification"
    OPTIMIZE = "optimize"
    COMPLETE = "complete"


WELCOME_MESSAGE = """Welcome to Visory! I'll help you plan your perfect day.

Choose how you'd like to get started:
- **Let AI Get to Know You**: Answer a few questions so I can understand your priorities
- **Plan Your Day**: Jump straight into planning your tasks
"""

QUESTIONNAIRE_INTRO = """Great! Let me understand what matters most to you by asking a few questions about your values and priorities.

"""

PLANNING_INTRO = "What tasks do you have on the agenda today?"

TASKS_MESSAGE = "Great! Now, what tasks do you have on the agenda today?"


class Orchestrator:
    """Runs the planning pipeline workflow."""

    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self.state = PlannerState(session_id=session_id)
        self.phase = WorkflowPhase.WELCOME
        self.conversation_history: list[dict] = []
        self.categorize_service = get_categorize_service()
        self.constraints_service = get_constraints_service()
        self.constraint_clarification: ConstraintClarification | None = None
        self.optimizer_service = get_optimizer_service()
        self.results_service = get_results_service()

        # Typed constraints for optimizer
        self.constraint_set = ConstraintSet()

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
        """Start the workflow, return welcome message."""
        self.phase = WorkflowPhase.WELCOME
        self._persist_state()
        return WELCOME_MESSAGE

    def start_planning(self) -> str:
        """Start the planning workflow (task collection phase).

        Uses utility weights from state if available, otherwise defaults.
        """
        if not self.state.utility_weights:
            self.state.utility_weights = {"work": 100, "health": 100, "personal": 100}

        self.phase = WorkflowPhase.COLLECT_TASKS
        self._persist_state()
        return PLANNING_INTRO

    def process_message(self, user_message: str):
        """Process a user message based on current phase."""
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

        self.state.tasks = self.categorize_service.categorize(
            raw_tasks,
            utility_weights=self.state.utility_weights,
        )

        self.phase = WorkflowPhase.CONSTRAINTS
        self._persist_state()

        response = "Great! I've categorized your tasks. Please set the duration for each task and your available time window."
        yield response
        self.conversation_history.append({"role": "assistant", "content": response})

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
            self.state.tasks = tasks
            self.state.time_window = time_window

            self.constraint_clarification = ConstraintClarification(tasks=self.state.tasks)

            self.phase = WorkflowPhase.CONSTRAINT_CLARIFICATION
            self._persist_state()

            full_response = ""
            for chunk in self.constraint_clarification.generate_question():
                full_response += chunk
                yield chunk

            self.conversation_history.append({"role": "assistant", "content": full_response})

    def _handle_constraint_clarification(self, user_message: str):
        """Handle the constraint clarification phase."""
        # Use semantic matcher to parse any user input
        matcher = get_constraint_matcher(self.state.tasks)
        self.constraint_set = matcher.match(user_message)

        if self.constraint_set.is_empty():
            yield "No constraints specified. Optimizing for maximum utility...\n\n"
        else:
            yield f"Understood: {self.constraint_set.describe()}\n\n"

        # Add fixed time slots from task.time_slot
        for task in self.state.tasks:
            if task.time_slot is not None:
                self.constraint_set.add(FixedTimeSlot(
                    task_name=task.name,
                    start_time=task.time_slot,
                ))

        # Save constraints to state
        self.state.constraint_set = self.constraint_set

        # Move to optimize phase
        self.phase = WorkflowPhase.OPTIMIZE
        self._persist_state()

        yield from self._handle_optimize()

    def apply_constraints_from_ids(self, constraint_ids: list[str]) -> None:
        """Apply constraints from button selection IDs.

        Args:
            constraint_ids: List of button IDs like ["TASK_Gym", "TASK_Run"]
        """
        self.constraint_set = self.constraint_clarification.selection_to_constraints(constraint_ids)

        # Add fixed time slots from task.time_slot
        for task in self.state.tasks:
            if task.time_slot is not None:
                self.constraint_set.add(FixedTimeSlot(
                    task_name=task.name,
                    start_time=task.time_slot,
                ))

        # Save to state
        self.state.constraint_set = self.constraint_set

    def apply_constraints_from_text(self, text: str) -> ConstraintSet:
        """Apply constraints from custom text.

        Args:
            text: Natural language constraint description.

        Returns:
            The parsed ConstraintSet.
        """
        matcher = get_constraint_matcher(self.state.tasks)
        self.constraint_set = matcher.match(text)

        # Add fixed time slots from task.time_slot
        for task in self.state.tasks:
            if task.time_slot is not None:
                self.constraint_set.add(FixedTimeSlot(
                    task_name=task.name,
                    start_time=task.time_slot,
                ))

        # Save to state
        self.state.constraint_set = self.constraint_set

        return self.constraint_set

    def run_optimization(self):
        """Run optimization and yield progress/results."""
        self.phase = WorkflowPhase.OPTIMIZE
        yield from self._handle_optimize()

    def return_to_tasks(self) -> str:
        """Return to task collection phase, preserving existing data."""
        self.phase = WorkflowPhase.COLLECT_TASKS
        self._persist_state()

        if self.state.raw_tasks:
            task_list = "\n".join(f"- {t}" for t in self.state.raw_tasks)
            return f"Let's revise your tasks. Current tasks:\n{task_list}\n\nWhat tasks would you like to plan?"
        return PLANNING_INTRO

    def return_to_constraints(self) -> str:
        """Return to constraints phase, preserving existing tasks."""
        if not self.state.tasks:
            return "Please add tasks first."

        self.phase = WorkflowPhase.CONSTRAINTS
        self._persist_state()
        return "Let's revise the durations and time slots for your tasks."

    def return_to_constraint_clarification(self) -> str:
        """Return to custom constraints phase."""
        if not self.state.tasks or not self.state.time_window:
            return "Please complete task collection and constraints first."

        self.constraint_clarification = ConstraintClarification(tasks=self.state.tasks)
        self.phase = WorkflowPhase.CONSTRAINT_CLARIFICATION
        self._persist_state()
        return "Let's revise your optimization constraints."

    def _handle_optimize(self):
        """Handle the optimization phase."""
        yield "Creating your optimized schedule...\n\n"

        # Run optimizer with constraint set
        router = self.optimizer_service.router
        selected_type = router._select_optimizer(
            self.state.tasks,
            self.state.time_window,
            self.constraint_set,
        )
        self.state.optimizer_type = selected_type.value

        daily_plan = router.optimize(
            self.state.tasks,
            self.state.time_window,
            constraints=self.constraint_set,
        )
        self.state.daily_plan = daily_plan

        # If LLM optimizer was used, show its reasoning
        from app.optimize.router import OptimizerType
        if selected_type == OptimizerType.LLM:
            llm_optimizer = router._optimizers.get(OptimizerType.LLM)
            if llm_optimizer and hasattr(llm_optimizer, 'last_reasoning') and llm_optimizer.last_reasoning:
                yield f"💡 **AI Reasoning:** {llm_optimizer.last_reasoning}\n\n"

        self.phase = WorkflowPhase.COMPLETE
        self._persist_state()

        # Generate AI summary of results
        try:
            ai_summary = self.results_service.summarize_results(
                daily_plan=daily_plan,
                all_tasks=self.state.tasks,
                constraint_set=self.constraint_set,
                optimizer_type=self.state.optimizer_type,
            )
            yield f"{ai_summary}\n\n"
        except Exception as e:
            # If AI summary fails, continue without it
            yield f"[Summary generation skipped: {str(e)}]\n\n"

        schedule_text = self._format_schedule(daily_plan)
        yield schedule_text
        self.conversation_history.append({"role": "assistant", "content": schedule_text})

    def _format_schedule(self, daily_plan) -> str:
        """Format the daily plan as readable text."""
        if not daily_plan.schedule:
            return "Could not create a schedule that satisfies all constraints.\n"

        lines = [
            f"Here's your optimized schedule for {daily_plan.time_window.start_time} - {daily_plan.time_window.end_time}:\n"
        ]

        for task in daily_plan.schedule:
            category_emoji = {"health": "💪", "work": "💼", "personal": "🎮"}.get(task.category, "📌")
            lines.append(
                f"{category_emoji} {task.start_time} - {task.end_time}: {task.task} ({task.duration_minutes} min)"
            )

        # Show constraints
        lines.append(f"\nConstraints: {self.constraint_set.describe()}")
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


# Session storage
_sessions: dict[str, Orchestrator] = {}


def get_or_create_orchestrator(session_id: str) -> Orchestrator:
    """Get existing orchestrator or create new one for session."""
    if session_id not in _sessions:
        _sessions[session_id] = Orchestrator(session_id=session_id)
    return _sessions[session_id]


def get_orchestrator(session_id: str) -> Orchestrator | None:
    """Get orchestrator for session if it exists."""
    return _sessions.get(session_id)
