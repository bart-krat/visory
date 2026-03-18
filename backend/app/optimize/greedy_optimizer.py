from app.state import Task, TimeWindow, DailyPlan
from app.optimize.base import BaseOptimizer


class GreedyOptimizer(BaseOptimizer):
    """Greedy optimizer that maximizes utility/time ratio.

    Selects tasks by sorting them by utility per minute (utility/duration)
    and greedily picking tasks until the time window is full.
    """

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
    ) -> DailyPlan:
        """Select tasks greedily by utility/time ratio.

        Args:
            tasks: Tasks with utility values.
            time_window: Available time window.

        Returns:
            DailyPlan with greedily selected tasks.
        """
        if not tasks:
            return DailyPlan(schedule=[], time_window=time_window)

        available_minutes = self._time_window_minutes(time_window)

        # Sort by utility/duration ratio (descending)
        sorted_tasks = sorted(
            tasks,
            key=lambda t: t.utility / t.duration if t.duration > 0 else 0,
            reverse=True,
        )

        selected: list[Task] = []
        remaining_time = available_minutes

        for task in sorted_tasks:
            if task.duration <= remaining_time:
                selected.append(task)
                remaining_time -= task.duration
                # Account for buffer time between tasks
                remaining_time -= 5

        # Sort selected tasks by category priority for scheduling
        category_order = {"health": 0, "work": 1, "personal": 2}
        selected.sort(key=lambda t: category_order.get(t.category, 2))

        return self._schedule_tasks(selected, time_window)
