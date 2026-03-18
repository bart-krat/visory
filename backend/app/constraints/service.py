import json
from app.state import Task, TimeWindow
from app.chat import get_chat_service
from app.utils import clean_json_response


CONSTRAINTS_SYSTEM_PROMPT = """You are Visory, helping users plan their day. The user has provided their tasks which have been categorized.

Your job is to ask them about:
1. How long each task will take (in minutes)
2. What time window they have available today (start and end time)

Be conversational and friendly. Ask about all tasks in one message. Keep it concise."""


class ConstraintsService:
    """Service for gathering task constraints via LLM conversation."""

    def __init__(self):
        self.chat_service = get_chat_service()

    def parse_constraints_response(
        self,
        tasks: list[Task],
        user_response: str,
        conversation_history: list[dict],
    ) -> tuple[list[Task], TimeWindow] | None:
        """Parse user's constraint answers using LLM.

        Updates the duration field on each task.

        Returns:
            Tuple of (tasks with durations filled, time window) or None if incomplete.
        """
        parse_prompt = """Extract the task durations and time window from the user's response.

Return valid JSON only:
{
  "durations": {"task name": minutes, ...},
  "start_time": "HH:MM",
  "end_time": "HH:MM"
}

If information is missing, return: {"incomplete": true, "missing": ["list of what's missing"]}"""

        response = self.chat_service.chat(
            messages=[{"role": "user", "content": f"User said: {user_response}\n\nTasks: {[t.name for t in tasks]}"}],
            system_prompt=parse_prompt,
            temperature=0.1,
        )

        try:
            content = clean_json_response(response)
            data = json.loads(content)

            if data.get("incomplete"):
                return None

            # Update duration on each task
            for task in tasks:
                duration = data["durations"].get(task.name, 30)
                task.duration = duration

            time_window = TimeWindow(
                start_time=data["start_time"],
                end_time=data["end_time"],
            )

            return tasks, time_window

        except (json.JSONDecodeError, KeyError):
            return None


_constraints_service: ConstraintsService | None = None


def get_constraints_service() -> ConstraintsService:
    """Get or create the singleton ConstraintsService instance."""
    global _constraints_service
    if _constraints_service is None:
        _constraints_service = ConstraintsService()
    return _constraints_service
