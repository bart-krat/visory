"""Constraint clarification for the planning workflow.

Handles user selection of optimization constraints.
Supports both button-based task selection and custom text input.
"""
from app.state import Constraint, Task, CustomConstraint


class ConstraintClarification:
    """Handles constraint selection in the workflow.

    Generates dynamic task-based options:
    - TASK_<task_name> buttons for each task

    Also supports custom text input which will be processed
    via semantic matching.

    Usage:
        clarification = ConstraintClarification(tasks=state.tasks)

        # Get options for UI
        options = clarification.get_options_for_ui()

        # Parse user response (button click or custom text)
        result = clarification.parse_response(user_input)
        # Returns Constraint for button clicks, CustomConstraint for text
    """

    def __init__(self, tasks: list[Task] | None = None):
        """Initialize with tasks to generate dynamic options.

        Args:
            tasks: List of tasks to generate task-specific options.
        """
        self.tasks = tasks or []
        self.options = self._build_options()

    def _build_options(self) -> list[Constraint]:
        """Build the list of task constraint options (buttons only)."""
        options = []

        # Dynamic task options - one button per task
        for task in self.tasks:
            options.append(Constraint(
                id=f"TASK_{task.name}",
                name=f"Include {task.name}",
                description=f"Must include the task: {task.name}",
                button_label=f"Must do: {task.name}",
            ))

        return options

    def generate_question(self):
        """Generate the constraint selection question.

        Yields:
            String chunks for streaming to chat interface.
        """
        yield "\nHow would you like me to optimize your schedule?\n"
        yield "You can select specific tasks that must be included, "
        yield "or describe your requirements in your own words."

    def get_options_for_ui(self) -> list[dict]:
        """Get options formatted for UI button rendering.

        Returns:
            List of dicts with 'id', 'label', 'description' for each task option.
        """
        return [
            {
                "id": opt.id,
                "label": opt.button_label,
                "description": opt.description,
            }
            for opt in self.options
        ]

    def parse_response(self, user_input: str) -> Constraint | CustomConstraint | None:
        """Parse user's constraint selection.

        Accepts:
        - Task constraint ID (e.g., "TASK_Go to gym")
        - Option number (e.g., "1")
        - Custom text describing constraints

        Args:
            user_input: The user's response text.

        Returns:
            Constraint for button selections,
            CustomConstraint for custom text input,
            None if input is empty.
        """
        user_input = user_input.strip()
        if not user_input:
            return None

        # Try exact ID match for task constraints
        for opt in self.options:
            if user_input == opt.id or user_input.upper() == opt.id.upper():
                return opt

        # Try number selection
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(self.options):
                return self.options[idx]

        # Try partial match on button label
        user_lower = user_input.lower()
        for opt in self.options:
            if user_lower in opt.button_label.lower():
                return opt

        # Not a button selection - treat as custom text constraint
        return CustomConstraint(raw_text=user_input)

    def get_task_names(self) -> list[str]:
        """Get list of available task names for matching."""
        return [task.name for task in self.tasks]

    def get_categories(self) -> list[str]:
        """Get list of available categories for matching."""
        return list(set(task.category for task in self.tasks))
