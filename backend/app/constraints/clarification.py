"""Constraint clarification for the planning workflow.

Handles user selection of optimization constraints.
"""
from app.state import Constraint, CONSTRAINTS, Task


class ConstraintClarification:
    """Handles constraint selection in the workflow.

    Generates dynamic options based on tasks:
    - Static: ALL_CATEGORIES, NONE
    - Dynamic per category: CATEGORY_<category>
    - Dynamic per task: TASK_<task_name>

    Usage:
        clarification = ConstraintClarification(tasks=state.tasks)

        # Get options for UI
        options = clarification.get_options_for_ui()

        # Parse user response
        constraint = clarification.parse_response(user_input)
    """

    def __init__(self, tasks: list[Task] | None = None):
        """Initialize with tasks to generate dynamic options.

        Args:
            tasks: List of tasks to generate category/task-specific options.
        """
        self.tasks = tasks or []
        self.options = self._build_options()

    def _build_options(self) -> list[Constraint]:
        """Build the full list of constraint options."""
        options = []

        # Static options first
        options.append(CONSTRAINTS["ALL_CATEGORIES"])
        options.append(CONSTRAINTS["NONE"])

        # Dynamic category options (only for categories present in tasks)
        categories = sorted(set(t.category for t in self.tasks))
        for category in categories:
            options.append(Constraint(
                id=f"CATEGORY_{category.upper()}",
                name=f"Include {category.title()}",
                description=f"Must include at least one {category} task",
                button_label=f"Must include {category}",
            ))

        # Dynamic task options
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
        yield "\nHow would you like me to optimize your schedule?"

    def get_options_for_ui(self) -> list[dict]:
        """Get options formatted for UI button rendering.

        Returns:
            List of dicts with 'id', 'label', 'description' for each option.
        """
        return [
            {
                "id": opt.id,
                "label": opt.button_label,
                "description": opt.description,
            }
            for opt in self.options
        ]

    def parse_response(self, user_input: str) -> Constraint | None:
        """Parse user's constraint selection.

        Accepts:
        - Option ID (e.g., "ALL_CATEGORIES", "CATEGORY_WORK", "TASK_Go to gym")
        - Option number (e.g., "1")
        - Partial match on button label

        Args:
            user_input: The user's response text.

        Returns:
            Selected Constraint or None if not recognized.
        """
        user_input = user_input.strip()

        # Try exact ID match (case-insensitive for static, case-sensitive for dynamic)
        for opt in self.options:
            if user_input == opt.id or user_input.upper() == opt.id:
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

        return None

    def get_default(self) -> Constraint:
        """Get the default constraint (first option)."""
        return self.options[0]
