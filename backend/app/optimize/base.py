from abc import ABC, abstractmethod

from app.state import Task, TimeWindow, DailyPlan, ScheduledTask
from app.utils import time_window_minutes


class BaseOptimizer(ABC):
    """Abstract base class for task optimizers."""

    @abstractmethod
    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
    ) -> DailyPlan:
        """Select and schedule tasks within the time window.

        Args:
            tasks: Tasks with utility values to optimize.
            time_window: Available time window for scheduling.

        Returns:
            DailyPlan with selected and scheduled tasks.
        """
        pass

    def _time_window_minutes(self, time_window: TimeWindow) -> int:
        """Convert TimeWindow to total available minutes."""
        return time_window_minutes(time_window.start_time, time_window.end_time)

    def _schedule_tasks(
        self,
        selected_tasks: list[Task],
        time_window: TimeWindow,
        buffer_minutes: int = 5,
    ) -> DailyPlan:
        """Convert selected tasks into a scheduled DailyPlan.

        Args:
            selected_tasks: Tasks to schedule (in desired order).
            time_window: Time window for scheduling.
            buffer_minutes: Buffer between tasks.

        Returns:
            DailyPlan with concrete start/end times.
        """
        schedule = []
        start_h, start_m = map(int, time_window.start_time.split(":"))
        current_minutes = start_h * 60 + start_m

        for task in selected_tasks:
            start_time = f"{current_minutes // 60:02d}:{current_minutes % 60:02d}"
            end_minutes = current_minutes + task.duration
            end_time = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"

            schedule.append(ScheduledTask(
                task=task.name,
                category=task.category,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=task.duration,
            ))

            current_minutes = end_minutes + buffer_minutes

        return DailyPlan(schedule=schedule, time_window=time_window)
