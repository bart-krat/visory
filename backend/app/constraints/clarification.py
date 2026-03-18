"""Constraint clarification for the planning workflow.

Handles user selection of optimization constraints.
"""
from app.state import Constraint, CONSTRAINTS


class ConstraintClarification:
    """Handles constraint selection in the workflow.

    Usage:
        clarification = ConstraintClarification()

        # Stream the question to user
        for chunk in clarification.generate_question():
            yield chunk

        # Parse user response
        constraint = clarification.parse_response(user_input)
    """

    def __init__(self, constraint_ids: list[str] | None = None):
        """Initialize with specific constraints to offer.

        Args:
            constraint_ids: List of constraint IDs to offer.
                           Defaults to all available constraints.
        """
        if constraint_ids:
            self.options = [CONSTRAINTS[cid] for cid in constraint_ids if cid in CONSTRAINTS]
        else:
            self.options = list(CONSTRAINTS.values())

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
        - Option ID (e.g., "ALL_CATEGORIES")
        - Option number (e.g., "1")
        - Partial match on button label

        Args:
            user_input: The user's response text.

        Returns:
            Selected Constraint or None if not recognized.
        """
        user_input = user_input.strip()

        # Try exact ID match
        for opt in self.options:
            if user_input.upper() == opt.id:
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
