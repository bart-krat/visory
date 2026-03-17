import json
from app.state import TaskWithDuration, TimeWindow, ScheduledTask, DailyPlan
from app.chat import get_chat_service


DEFAULT_RULE = """Schedule tasks in this priority order:
1. Health/Exercise tasks first (morning energy)
2. Work tasks next (peak productivity)
3. Leisure tasks last (wind down)

Additional guidelines:
- Respect the user's available time window
- Add 5-minute buffers between tasks
- Group similar categories together when possible
"""


class OptimizerService:
    """Service for creating optimized daily schedules."""

    def __init__(self):
        self.chat_service = get_chat_service()
        self.rule = DEFAULT_RULE

    def create_optimizer(self, custom_rule: str | None = None) -> str:
        """Create/set the optimization rule.

        Args:
            custom_rule: Optional custom rule. Uses default if not provided.

        Returns:
            The active rule.
        """
        if custom_rule:
            self.rule = custom_rule
        else:
            self.rule = DEFAULT_RULE
        return self.rule

    def run_optimizer(
        self,
        tasks_with_duration: list[TaskWithDuration],
        time_window: TimeWindow,
    ) -> DailyPlan:
        """Run the optimizer to create a daily schedule.

        Args:
            tasks_with_duration: Tasks with categories and durations.
            time_window: Available time window for scheduling.

        Returns:
            Optimized DailyPlan with scheduled tasks.
        """
        task_list = "\n".join(
            f"- {t.task} ({t.category}, {t.duration_minutes} min)"
            for t in tasks_with_duration
        )

        system_prompt = f"""You are a daily schedule optimizer. Create an optimized schedule based on the given rule.

OPTIMIZATION RULE:
{self.rule}

Return valid JSON only with this structure:
{{
  "schedule": [
    {{"task": "task name", "category": "category", "start_time": "HH:MM", "end_time": "HH:MM", "duration_minutes": N}},
    ...
  ]
}}

Order tasks according to the rule. Calculate exact start/end times that fit within the time window."""

        user_prompt = f"""Create an optimized schedule for these tasks:

{task_list}

Available time window: {time_window.start_time} to {time_window.end_time}

Return the JSON schedule."""

        response = self.chat_service.simple_chat(
            user_message=user_prompt,
            system_prompt=system_prompt,
        )

        # Parse JSON response
        try:
            content = response.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            data = json.loads(content)

            schedule = [
                ScheduledTask(
                    task=item["task"],
                    category=item["category"],
                    start_time=item["start_time"],
                    end_time=item["end_time"],
                    duration_minutes=item["duration_minutes"],
                )
                for item in data["schedule"]
            ]

            return DailyPlan(schedule=schedule, time_window=time_window)

        except (json.JSONDecodeError, KeyError, TypeError):
            # Fallback: create simple sequential schedule
            return self._fallback_schedule(tasks_with_duration, time_window)

    def _fallback_schedule(
        self,
        tasks: list[TaskWithDuration],
        time_window: TimeWindow,
    ) -> DailyPlan:
        """Create a simple sequential schedule as fallback."""
        # Sort by category priority: health, work, leisure
        priority = {"health": 0, "work": 1, "leisure": 2}
        sorted_tasks = sorted(tasks, key=lambda t: priority.get(t.category, 2))

        schedule = []
        current_hour, current_min = map(int, time_window.start_time.split(":"))

        for task in sorted_tasks:
            start = f"{current_hour:02d}:{current_min:02d}"

            # Add duration
            total_minutes = current_hour * 60 + current_min + task.duration_minutes
            end_hour = total_minutes // 60
            end_min = total_minutes % 60
            end = f"{end_hour:02d}:{end_min:02d}"

            schedule.append(ScheduledTask(
                task=task.task,
                category=task.category,
                start_time=start,
                end_time=end,
                duration_minutes=task.duration_minutes,
            ))

            # Add 5 min buffer
            total_minutes += 5
            current_hour = total_minutes // 60
            current_min = total_minutes % 60

        return DailyPlan(schedule=schedule, time_window=time_window)


_optimizer_service: OptimizerService | None = None


def get_optimizer_service() -> OptimizerService:
    """Get or create the singleton OptimizerService instance."""
    global _optimizer_service
    if _optimizer_service is None:
        _optimizer_service = OptimizerService()
    return _optimizer_service
