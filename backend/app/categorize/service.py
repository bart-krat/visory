import json
from pydantic import BaseModel, ValidationError, field_validator
from app.chat import get_chat_service
from app.state import Task, DEFAULT_UTILITY_WEIGHTS
from app.utils import clean_json_response

CATEGORIES = ["work", "health", "personal"]


class CategorizedTask(BaseModel):
    """A single categorized task from the LLM."""
    task: str
    category: str

    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        """Ensure category is one of the valid options."""
        v = v.lower()
        if v not in CATEGORIES:
            raise ValueError(f'Category must be one of: {", ".join(CATEGORIES)}. Got: {v}')
        return v

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
            content = clean_json_response(response)
            result = json.loads(content)

            # Validate with Pydantic schema
            validated = [CategorizedTask(**item) for item in result]

            # Build Task objects from validated data
            tasks = []
            for item in validated:
                category = item.category.lower()
                utility = weights.get(category, 100.0)
                tasks.append(Task(name=item.task, category=category, utility=utility))

            return tasks

        except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as e:
            # Log validation failures for debugging
            if isinstance(e, ValidationError):
                print(f"Categorization validation failed: {e}")
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
