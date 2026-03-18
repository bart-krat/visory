"""Constraint clarification for the planning workflow.

Handles user selection of optimization constraints via buttons.
Converts selections to typed constraints for the optimizer.
"""
from app.state import (
    Task,
    UIConstraint,
    ConstraintSet,
    MustIncludeTask,
)


class ConstraintClarification:
    """Handles constraint selection in the workflow.

    Generates task-based button options and converts selections
    to typed ConstraintSet for the optimizer.

    Usage:
        clarification = ConstraintClarification(tasks=state.tasks)

        # Get options for UI buttons
        options = clarification.get_options_for_ui()

        # Convert button selections to typed constraints
        constraints = clarification.selection_to_constraints(["TASK_Gym", "TASK_Run"])
    """

    def __init__(self, tasks: list[Task] | None = None):
        """Initialize with tasks to generate options.

        Args:
            tasks: List of tasks to generate task-specific options.
        """
        self.tasks = tasks or []
        self.options = self._build_options()

    def _build_options(self) -> list[UIConstraint]:
        """Build the list of task constraint options (buttons)."""
        options = []

        for task in self.tasks:
            options.append(UIConstraint(
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

    def selection_to_constraints(self, selected_ids: list[str]) -> ConstraintSet:
        """Convert button selections to typed constraints.

        Args:
            selected_ids: List of button IDs (e.g., ["TASK_Gym", "TASK_Run"])

        Returns:
            ConstraintSet with typed constraints.
        """
        cs = ConstraintSet()

        for id in selected_ids:
            if id.startswith("TASK_"):
                task_name = id.replace("TASK_", "")
                # Verify task exists
                if any(t.name == task_name for t in self.tasks):
                    cs.add(MustIncludeTask(task_name=task_name))

        return cs

    def get_task_names(self) -> list[str]:
        """Get list of available task names."""
        return [task.name for task in self.tasks]

    def get_categories(self) -> list[str]:
        """Get list of available categories."""
        return list(set(task.category for task in self.tasks))
