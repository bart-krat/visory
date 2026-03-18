"""Knapsack optimizer - selects optimal subset of tasks by utility.

Uses dynamic programming to select tasks that maximize utility
while fitting within the time budget and satisfying constraints.
"""
from functools import lru_cache

from app.state import Task, TimeWindow, DailyPlan
from app.optimize.base import BaseOptimizer


class KnapsackOptimizer(BaseOptimizer):
    """Knapsack optimizer using dynamic programming.

    Selects the optimal subset of tasks that:
    - Fits within the time window
    - Includes all mandatory tasks
    - Includes at least one task from each mandatory category
    - Maximizes total utility

    Does NOT handle: fixed time slots or ordering constraints.
    Use EnumerationOptimizer for those.
    """

    def __init__(self, buffer_minutes: int = 5):
        self.buffer_minutes = buffer_minutes

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
        mandatory_tasks: set[str] | None = None,
        mandatory_categories: set[str] | None = None,
    ) -> DailyPlan:
        """Select optimal tasks using knapsack DP.

        Args:
            tasks: Tasks to select from.
            time_window: Available time window.
            mandatory_tasks: Task names that must be included.
            mandatory_categories: Categories that must have at least one task.

        Returns:
            DailyPlan with selected tasks scheduled sequentially.
        """
        if not tasks:
            return DailyPlan(schedule=[], time_window=time_window)

        mandatory_tasks = mandatory_tasks or set()
        mandatory_categories = frozenset(mandatory_categories) if mandatory_categories else frozenset()
        available_minutes = self._time_window_minutes(time_window)

        # Select tasks using DP
        selected = self._knapsack_select(
            tuple(tasks),
            available_minutes,
            mandatory_tasks,
            mandatory_categories,
        )

        if selected is None:
            # Can't satisfy constraints
            return DailyPlan(schedule=[], time_window=time_window)

        # Sort by category for nice presentation
        category_order = {"health": 0, "work": 1, "personal": 2}
        selected.sort(key=lambda t: category_order.get(t.category, 2))

        return self._schedule_tasks(selected, time_window, self.buffer_minutes)

    def _knapsack_select(
        self,
        tasks: tuple[Task, ...],
        capacity: int,
        mandatory_tasks: set[str],
        mandatory_categories: frozenset[str],
    ) -> list[Task] | None:
        """Select tasks using knapsack DP.

        Returns None if constraints can't be satisfied.
        """
        buffer = self.buffer_minutes

        @lru_cache(maxsize=None)
        def recurse(
            index: int,
            time_remaining: int,
            tasks_done: frozenset,
            cats_found: frozenset,
        ) -> tuple[float, tuple[int, ...]]:
            # Base case
            if index == len(tasks):
                if mandatory_tasks <= tasks_done and mandatory_categories <= cats_found:
                    return (0.0, ())
                return (float("-inf"), ())

            task = tasks[index]
            task_time = task.duration + buffer

            # Option 1: Skip (can't skip mandatory tasks)
            skip_util, skip_idx = float("-inf"), ()
            if task.name not in mandatory_tasks:
                skip_util, skip_idx = recurse(index + 1, time_remaining, tasks_done, cats_found)

            # Option 2: Take (if fits)
            take_util, take_idx = float("-inf"), ()
            if task.duration <= time_remaining:
                new_done = tasks_done | {task.name}
                new_cats = cats_found | {task.category}
                new_time = time_remaining - task_time

                sub_util, sub_idx = recurse(index + 1, new_time, new_done, new_cats)
                if sub_util > float("-inf"):
                    take_util = task.utility + sub_util
                    take_idx = (index,) + sub_idx

            if take_util > skip_util:
                return (take_util, take_idx)
            return (skip_util, skip_idx)

        utility, indices = recurse(0, capacity, frozenset(), frozenset())
        recurse.cache_clear()

        if utility == float("-inf"):
            return None

        return [tasks[i] for i in indices]
