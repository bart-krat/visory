"""Semantic matching for custom constraints.

Parses natural language constraint descriptions into typed
ConstraintSet objects that optimizers can understand.
"""
import re

from app.state import (
    Task,
    ConstraintSet,
    MustIncludeTask,
    MustIncludeCategory,
    FixedTimeSlot,
    OrderedAfter,
)


class ConstraintMatcher:
    """Matches natural language to typed constraints.

    Recognizes patterns like:
    - "must do gym" → MustIncludeTask("Gym")
    - "need a workout" → MustIncludeCategory("health")
    - "meeting at 2pm" → FixedTimeSlot("Meeting", 840)
    - "beach after run" → OrderedAfter("Beach", "Run")

    Usage:
        matcher = ConstraintMatcher(tasks)
        constraints = matcher.match("I need to do gym and beach after my run")
    """

    # Category keywords for semantic matching
    CATEGORY_KEYWORDS = {
        "health": [
            "health", "healthy", "fitness", "exercise", "workout", "gym",
            "run", "running", "walk", "walking", "yoga", "meditation",
            "physical", "body", "wellness", "active", "sport",
        ],
        "work": [
            "work", "working", "job", "meeting", "meetings", "office",
            "project", "deadline", "email", "professional", "business",
            "productivity", "task", "report", "presentation",
        ],
        "personal": [
            "personal", "hobby", "fun", "relax", "relaxing", "leisure",
            "entertainment", "social", "friends", "family", "creative",
            "reading", "gaming", "music",
        ],
    }

    # Patterns for constraint detection
    MUST_PATTERNS = [
        r"must\s+(?:do|include|have)\s+(.+)",
        r"need\s+to\s+(?:do|include)\s+(.+)",
        r"have\s+to\s+(?:do|include)\s+(.+)",
        r"(?:definitely|absolutely)\s+(?:do|include)\s+(.+)",
        r"make\s+sure\s+(?:to\s+)?(?:do|include)\s+(.+)",
        r"don'?t\s+forget\s+(?:to\s+)?(.+)",
    ]

    ORDER_PATTERNS = [
        r"(.+?)\s+after\s+(.+)",
        r"(.+?)\s+following\s+(.+)",
        r"(.+?)\s+then\s+(.+)",  # "run then beach" → beach after run
        r"first\s+(.+?)\s+then\s+(.+)",  # "first run then beach"
        r"(.+?)\s+before\s+(.+)",  # reversed: A before B → B after A
    ]

    TIME_PATTERNS = [
        r"(.+?)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+(.+)",
    ]

    def __init__(self, tasks: list[Task]):
        """Initialize with available tasks.

        Args:
            tasks: List of tasks to match against.
        """
        self.tasks = tasks
        self.task_names = [t.name for t in tasks]
        self.task_names_lower = {t.name.lower(): t.name for t in tasks}
        self.categories = list(set(t.category for t in tasks))

    def match(self, text: str) -> ConstraintSet:
        """Parse natural language into typed constraints.

        Args:
            text: User's constraint description.

        Returns:
            ConstraintSet with extracted constraints.
        """
        cs = ConstraintSet()
        text_lower = text.lower().strip()

        # Try to extract ordering constraints first (most specific)
        ordering = self._extract_ordering(text_lower)
        for constraint in ordering:
            cs.add(constraint)

        # Extract time-based constraints
        time_constraints = self._extract_time_slots(text_lower)
        for constraint in time_constraints:
            cs.add(constraint)

        # Extract must-include task constraints
        task_constraints = self._extract_must_include_tasks(text_lower)
        for constraint in task_constraints:
            # Avoid duplicates from ordering
            existing_tasks = {c.task_name for c in cs.constraints if isinstance(c, MustIncludeTask)}
            if constraint.task_name not in existing_tasks:
                cs.add(constraint)

        # Extract category constraints
        category_constraints = self._extract_categories(text_lower)
        for constraint in category_constraints:
            cs.add(constraint)

        return cs

    def _extract_ordering(self, text: str) -> list[OrderedAfter]:
        """Extract ordering constraints from text."""
        constraints = []

        for pattern in self.ORDER_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()

                if "before" in pattern:
                    # "A before B" means B comes after A
                    first_text, second_text = groups[0], groups[1]
                    first_task = self._find_task(first_text)
                    second_task = self._find_task(second_text)
                    if first_task and second_task:
                        constraints.append(OrderedAfter(
                            task_name=second_task,
                            after_task=first_task,
                        ))
                elif "first" in pattern:
                    # "first A then B" means B after A
                    first_text, second_text = groups[0], groups[1]
                    first_task = self._find_task(first_text)
                    second_task = self._find_task(second_text)
                    if first_task and second_task:
                        constraints.append(OrderedAfter(
                            task_name=second_task,
                            after_task=first_task,
                        ))
                else:
                    # "A after B" or "A then B" → A after B
                    first_text, second_text = groups[0], groups[1]
                    first_task = self._find_task(first_text)
                    second_task = self._find_task(second_text)
                    if first_task and second_task:
                        if "then" in pattern:
                            # "run then beach" → beach after run
                            constraints.append(OrderedAfter(
                                task_name=second_task,
                                after_task=first_task,
                            ))
                        else:
                            # "beach after run" → beach after run
                            constraints.append(OrderedAfter(
                                task_name=first_task,
                                after_task=second_task,
                            ))

        return constraints

    def _extract_time_slots(self, text: str) -> list[FixedTimeSlot]:
        """Extract fixed time slot constraints from text."""
        constraints = []

        # Pattern: "meeting at 2pm" or "2pm meeting"
        pattern = r"(.+?)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?"
        matches = re.finditer(pattern, text, re.IGNORECASE)

        for match in matches:
            task_text = match.group(1)
            hour = int(match.group(2))
            minute = int(match.group(3)) if match.group(3) else 0
            ampm = match.group(4)

            # Convert to 24-hour
            if ampm:
                if ampm.lower() == "pm" and hour != 12:
                    hour += 12
                elif ampm.lower() == "am" and hour == 12:
                    hour = 0

            task_name = self._find_task(task_text)
            if task_name:
                start_time = hour * 60 + minute
                constraints.append(FixedTimeSlot(
                    task_name=task_name,
                    start_time=start_time,
                ))

        return constraints

    def _extract_must_include_tasks(self, text: str) -> list[MustIncludeTask]:
        """Extract must-include task constraints from text."""
        constraints = []

        # Try explicit patterns first
        for pattern in self.MUST_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                task_text = match.group(1)
                task_name = self._find_task(task_text)
                if task_name:
                    constraints.append(MustIncludeTask(task_name=task_name))

        # Also check for direct task name mentions
        for task in self.tasks:
            if task.name.lower() in text:
                if not any(c.task_name == task.name for c in constraints):
                    constraints.append(MustIncludeTask(task_name=task.name))

        return constraints

    def _extract_categories(self, text: str) -> list[MustIncludeCategory]:
        """Extract category constraints from text."""
        constraints = []

        # Look for category keywords
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if category not in self.categories:
                continue

            for keyword in keywords:
                # Check for patterns like "need a workout", "include something healthy"
                if keyword in text:
                    # Verify it's not just part of a task name we already matched
                    if not any(keyword in t.name.lower() for t in self.tasks if t.name.lower() in text):
                        constraints.append(MustIncludeCategory(category=category))
                        break

        return constraints

    def _find_task(self, text: str) -> str | None:
        """Find a task name in text.

        Args:
            text: Text that might contain a task name.

        Returns:
            Matched task name or None.
        """
        text = text.strip().lower()

        # Exact match
        if text in self.task_names_lower:
            return self.task_names_lower[text]

        # Partial match - task name contained in text
        for task_lower, task_name in self.task_names_lower.items():
            if task_lower in text or text in task_lower:
                return task_name

        # Fuzzy match - check if most words match
        text_words = set(text.split())
        for task_lower, task_name in self.task_names_lower.items():
            task_words = set(task_lower.split())
            if len(task_words) >= 2:
                overlap = len(text_words & task_words)
                if overlap >= len(task_words) * 0.5:
                    return task_name

        return None


def get_constraint_matcher(tasks: list[Task]) -> ConstraintMatcher:
    """Factory function to create a ConstraintMatcher."""
    return ConstraintMatcher(tasks)
