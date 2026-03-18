import json
from app.chat import get_chat_service
from app.state import Task, DEFAULT_UTILITY_WEIGHTS

CATEGORIES = ["work", "health", "personal"]

CATEGORIZE_SYSTEM_PROMPT = """You are a task categorizer. Given a list of tasks, classify each one into exactly one category: work, health, or personal.

Categories:
- work: professional tasks, meetings, emails, reports, deadlines, projects, upskilling
- health: exercise, medical appointments, wellness, sleep, nutrition
- personal: hobbies, entertainment, socializing, relaxation, personal fun, family time

Respond with valid JSON only. Return an array of objects, each with "task" (the original text) and "category" (one of: work, health, personal).

Example input: ["finish report", "go to gym", "watch movie"]
Example output: [{"task": "finish report", "category": "work"}, {"task": "go to gym", "category": "health"}, {"task": "watch movie", "category": "personal"}]"""


class CategorizeService:
    """Service for categorizing tasks using LLM."""

    def __init__(self):
        self.chat_service = get_chat_service()

    def categorize(
        self,
        task_names: list[str],
        utility_weights: dict[str, float] | None = None,
    ) -> list[Task]:
        """Categorize a list of tasks.

        Args:
            task_names: List of task name strings to categorize.
            utility_weights: Optional dict with 'work', 'health', 'personal' weights.
                            If not provided, uses default balanced weights.

        Returns:
            List of Task objects with name, category, and utility set.
            Duration is left at 0 (filled by constraints phase).
        """
        if not task_names:
            return []

        # Use provided weights or defaults
        weights = utility_weights or DEFAULT_UTILITY_WEIGHTS

        prompt = f"Categorize these tasks: {json.dumps(task_names)}"

        response = self.chat_service.simple_chat(
            user_message=prompt,
            system_prompt=CATEGORIZE_SYSTEM_PROMPT,
        )

        # Parse JSON response
        try:
            content = response.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            result = json.loads(content)

            # Build Task objects
            tasks = []
            for item in result:
                name = item.get("task", "")
                category = item.get("category", "").lower()
                if category not in CATEGORIES:
                    category = "personal"  # Default fallback
                utility = weights.get(category, 100.0)
                tasks.append(Task(name=name, category=category, utility=utility))

            return tasks

        except (json.JSONDecodeError, KeyError, TypeError):
            # Fallback: return tasks as uncategorized personal
            return [
                Task(name=t, category="personal", utility=weights.get("personal", 100.0))
                for t in task_names
            ]


_categorize_service: CategorizeService | None = None


def get_categorize_service() -> CategorizeService:
    """Get or create the singleton CategorizeService instance."""
    global _categorize_service
    if _categorize_service is None:
        _categorize_service = CategorizeService()
    return _categorize_service
