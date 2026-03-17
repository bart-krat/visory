from app.state import CategorizedTask, TaskWithDuration, TimeWindow
from app.chat import get_chat_service


CONSTRAINTS_SYSTEM_PROMPT = """You are Visory, helping users plan their day. The user has provided their tasks which have been categorized.

Your job is to ask them about:
1. How long each task will take (in minutes)
2. What time window they have available today (start and end time)

Be conversational and friendly. Ask about all tasks in one message. Keep it concise."""


class ConstraintsService:
    """Service for gathering task constraints via LLM conversation."""

    def __init__(self):
        self.chat_service = get_chat_service()

    def generate_constraints_question(self, categorized_tasks: list[CategorizedTask]):
        """Generate a streaming LLM question about task constraints.

        Args:
            categorized_tasks: The user's categorized tasks.

        Yields:
            String chunks of the LLM response.
        """
        task_list = "\n".join(
            f"- {t.task} ({t.category})" for t in categorized_tasks
        )

        prompt = f"""The user has these tasks for today:
{task_list}

Ask them how long each task will take and what time window they have available today. Be friendly and concise."""

        messages = [{"role": "user", "content": prompt}]

        for chunk in self.chat_service.chat_stream(
            messages=messages,
            system_prompt=CONSTRAINTS_SYSTEM_PROMPT,
        ):
            yield chunk

    def parse_constraints_response(
        self,
        categorized_tasks: list[CategorizedTask],
        user_response: str,
        conversation_history: list[dict],
    ) -> tuple[list[TaskWithDuration], TimeWindow] | None:
        """Parse user's constraint answers using LLM.

        Returns:
            Tuple of (tasks with durations, time window) or None if incomplete.
        """
        import json

        parse_prompt = """Extract the task durations and time window from the user's response.

Return valid JSON only:
{
  "durations": {"task name": minutes, ...},
  "start_time": "HH:MM",
  "end_time": "HH:MM"
}

If information is missing, return: {"incomplete": true, "missing": ["list of what's missing"]}"""

        messages = conversation_history + [
            {"role": "user", "content": user_response}
        ]

        response = self.chat_service.chat(
            messages=[{"role": "user", "content": f"User said: {user_response}\n\nTasks: {[t.task for t in categorized_tasks]}"}],
            system_prompt=parse_prompt,
            temperature=0.1,
        )

        try:
            content = response.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            data = json.loads(content)

            if data.get("incomplete"):
                return None

            tasks_with_duration = []
            for ct in categorized_tasks:
                duration = data["durations"].get(ct.task, 30)
                tasks_with_duration.append(TaskWithDuration(
                    task=ct.task,
                    category=ct.category,
                    duration_minutes=duration,
                ))

            time_window = TimeWindow(
                start_time=data["start_time"],
                end_time=data["end_time"],
            )

            return tasks_with_duration, time_window

        except (json.JSONDecodeError, KeyError):
            return None


_constraints_service: ConstraintsService | None = None


def get_constraints_service() -> ConstraintsService:
    """Get or create the singleton ConstraintsService instance."""
    global _constraints_service
    if _constraints_service is None:
        _constraints_service = ConstraintsService()
    return _constraints_service
