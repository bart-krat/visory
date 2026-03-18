from app.state import Task, TimeWindow, DailyPlan
from app.optimize.base import BaseOptimizer
from app.utils import CATEGORY_ORDER


class SimpleOptimizer(BaseOptimizer):
    """Simple optimizer that orders tasks by category priority.

    Orders tasks as: Health -> Work -> Personal
    Schedules all tasks sequentially with buffer time between them.
    No selection logic - includes all tasks that fit.
    """

    def __init__(self, buffer_minutes: int = 5):
        self.buffer_minutes = buffer_minutes

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
    ) -> DailyPlan:
        if not tasks:
            return DailyPlan(schedule=[], time_window=time_window)

        # Sort by category: health, work, personal
        sorted_tasks = sorted(
            tasks,
            key=lambda t: CATEGORY_ORDER.get(t.category, 2),
        )

        # Filter to tasks that fit in time window
        available_minutes = self._time_window_minutes(time_window)
        selected: list[Task] = []
        time_used = 0

        for task in sorted_tasks:
            task_time = task.duration + self.buffer_minutes
            if time_used + task.duration <= available_minutes:
                selected.append(task)
                time_used += task_time

        return self._schedule_tasks(selected, time_window, self.buffer_minutes)
