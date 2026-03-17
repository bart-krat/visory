import json
from app.chat import get_chat_service

CATEGORIES = ["work", "health", "leisure"]

CATEGORIZE_SYSTEM_PROMPT = """You are a task categorizer. Given a list of tasks, classify each one into exactly one category: work, health, or leisure.

Categories:
- work: professional tasks, meetings, emails, reports, deadlines, projects
- health: exercise, medical appointments, wellness, sleep, nutrition
- leisure: hobbies, entertainment, socializing, relaxation, personal fun

Respond with valid JSON only. Return an array of objects, each with "task" (the original text) and "category" (one of: work, health, leisure).

Example input: ["finish report", "go to gym", "watch movie"]
Example output: [{"task": "finish report", "category": "work"}, {"task": "go to gym", "category": "health"}, {"task": "watch movie", "category": "leisure"}]"""


class CategorizeService:
    """Service for categorizing tasks using LLM."""

    def __init__(self):
        self.chat_service = get_chat_service()

    def categorize(self, tasks: list[str]) -> list[dict]:
        """Categorize a list of tasks.

        Args:
            tasks: List of task strings to categorize.

        Returns:
            List of dicts with 'task' and 'category' keys.
        """
        if not tasks:
            return []

        prompt = f"Categorize these tasks: {json.dumps(tasks)}"

        response = self.chat_service.simple_chat(
            user_message=prompt,
            system_prompt=CATEGORIZE_SYSTEM_PROMPT,
        )

        # Parse JSON response
        try:
            # Handle markdown code blocks if present
            content = response.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            result = json.loads(content)

            # Validate structure
            validated = []
            for item in result:
                task = item.get("task", "")
                category = item.get("category", "").lower()
                if category not in CATEGORIES:
                    category = "leisure"  # Default fallback
                validated.append({"task": task, "category": category})

            return validated

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Fallback: return tasks as uncategorized leisure
            return [{"task": t, "category": "leisure"} for t in tasks]


_categorize_service: CategorizeService | None = None


def get_categorize_service() -> CategorizeService:
    """Get or create the singleton CategorizeService instance."""
    global _categorize_service
    if _categorize_service is None:
        _categorize_service = CategorizeService()
    return _categorize_service
