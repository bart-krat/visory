"""Semantic matching for custom constraints.

Matches natural language constraint descriptions to knapsack-compatible
parameters (mandatory_tasks, mandatory_categories).
"""
from dataclasses import dataclass

from app.state import CustomConstraint, Task


@dataclass
class MatchResult:
    """Result of semantic matching."""
    mandatory_tasks: set[str]
    mandatory_categories: set[str]
    confidence: float  # 0-1
    explanation: str


class ConstraintMatcher:
    """Matches custom text constraints to knapsack parameters.

    Uses keyword-based and semantic matching to identify:
    - Specific tasks that must be included
    - Categories that must be represented

    Future: Could use embeddings for better semantic matching.
    """

    # Category keywords for matching
    CATEGORY_KEYWORDS = {
        "health": [
            "health", "healthy", "fitness", "exercise", "workout", "gym",
            "run", "running", "walk", "walking", "yoga", "meditation",
            "sleep", "rest", "diet", "nutrition", "physical", "body",
            "wellness", "wellbeing", "active", "sport", "sports",
        ],
        "work": [
            "work", "working", "job", "career", "office", "meeting",
            "meetings", "project", "deadline", "email", "emails",
            "professional", "business", "productivity", "productive",
            "task", "tasks", "assignment", "report", "presentation",
        ],
        "personal": [
            "personal", "hobby", "hobbies", "fun", "relax", "relaxing",
            "entertainment", "social", "friends", "family", "leisure",
            "creative", "reading", "gaming", "music", "art", "travel",
        ],
    }

    # Constraint intent keywords
    MUST_KEYWORDS = [
        "must", "need", "have to", "required", "important", "essential",
        "definitely", "absolutely", "necessary", "mandatory", "critical",
        "make sure", "ensure", "don't forget", "remember to", "include",
    ]

    AT_LEAST_KEYWORDS = [
        "at least", "at least one", "minimum", "some", "any",
    ]

    def __init__(self, tasks: list[Task]):
        """Initialize with available tasks.

        Args:
            tasks: List of tasks to match against.
        """
        self.tasks = tasks
        self.task_names = [t.name for t in tasks]
        self.task_name_lower = {t.name.lower(): t.name for t in tasks}
        self.categories = list(set(t.category for t in tasks))

    def match(self, constraint: CustomConstraint) -> CustomConstraint:
        """Match a custom constraint to knapsack parameters.

        Updates the CustomConstraint in-place with matched tasks/categories.

        Args:
            constraint: The custom constraint to match.

        Returns:
            The updated CustomConstraint with match results.
        """
        text = constraint.raw_text.lower()

        matched_tasks: set[str] = set()
        matched_categories: set[str] = set()
        explanations: list[str] = []

        # Match specific tasks by name
        task_matches = self._match_tasks(text)
        if task_matches:
            matched_tasks.update(task_matches)
            explanations.append(f"Found task references: {', '.join(task_matches)}")

        # Match categories by keywords
        category_matches = self._match_categories(text)
        if category_matches:
            matched_categories.update(category_matches)
            explanations.append(f"Found category references: {', '.join(category_matches)}")

        # Calculate confidence based on matches found
        confidence = self._calculate_confidence(text, matched_tasks, matched_categories)

        # Update the constraint
        constraint.matched_tasks = list(matched_tasks)
        constraint.matched_categories = list(matched_categories)
        constraint.is_matched = bool(matched_tasks or matched_categories)
        constraint.match_confidence = confidence
        constraint.match_explanation = "; ".join(explanations) if explanations else "No specific matches found"

        return constraint

    def _match_tasks(self, text: str) -> set[str]:
        """Find task names mentioned in the text."""
        matched = set()

        for task in self.tasks:
            task_name_lower = task.name.lower()

            # Exact match
            if task_name_lower in text:
                matched.add(task.name)
                continue

            # Fuzzy match - check if most words match
            task_words = set(task_name_lower.split())
            if len(task_words) >= 2:
                matches = sum(1 for word in task_words if word in text)
                if matches >= len(task_words) * 0.7:  # 70% of words match
                    matched.add(task.name)

        return matched

    def _match_categories(self, text: str) -> set[str]:
        """Find category references in the text."""
        matched = set()

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            # Only match categories that exist in the tasks
            if category not in self.categories:
                continue

            for keyword in keywords:
                if keyword in text:
                    matched.add(category)
                    break

        return matched

    def _calculate_confidence(
        self,
        text: str,
        matched_tasks: set[str],
        matched_categories: set[str],
    ) -> float:
        """Calculate confidence score for the match."""
        if not matched_tasks and not matched_categories:
            return 0.0

        score = 0.0

        # Task matches are high confidence
        if matched_tasks:
            score += 0.6 * len(matched_tasks) / len(self.tasks)

        # Category matches
        if matched_categories:
            score += 0.4 * len(matched_categories) / len(self.categories)

        # Boost for explicit constraint language
        has_must = any(kw in text for kw in self.MUST_KEYWORDS)
        has_at_least = any(kw in text for kw in self.AT_LEAST_KEYWORDS)

        if has_must:
            score *= 1.2
        if has_at_least:
            score *= 1.1

        return min(score, 1.0)

    def to_knapsack_params(self, constraint: CustomConstraint) -> MatchResult:
        """Convert a matched CustomConstraint to knapsack parameters.

        Args:
            constraint: A CustomConstraint that has been matched.

        Returns:
            MatchResult with sets ready for the knapsack optimizer.
        """
        return MatchResult(
            mandatory_tasks=set(constraint.matched_tasks),
            mandatory_categories=set(constraint.matched_categories),
            confidence=constraint.match_confidence,
            explanation=constraint.match_explanation,
        )


def get_constraint_matcher(tasks: list[Task]) -> ConstraintMatcher:
    """Factory function to create a ConstraintMatcher."""
    return ConstraintMatcher(tasks)
