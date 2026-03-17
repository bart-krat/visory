from functools import lru_cache

from app.state import Task, TimeWindow, DailyPlan
from app.optimize.base import BaseOptimizer


class KnapsackOptimizer(BaseOptimizer):
    """Knapsack optimizer using dynamic programming.

    Finds the optimal subset of tasks that:
    1. Maximizes total utility
    2. Fits within the time window
    3. Includes at least one task from each required category
    """

    def __init__(
        self,
        required_categories: set[str] | None = None,
        buffer_minutes: int = 5,
    ):
        """Initialize the optimizer.

        Args:
            required_categories: Categories that must have at least one task.
                                 Defaults to {"work", "leisure", "health"}.
            buffer_minutes: Buffer time between tasks.
        """
        self.required_categories = frozenset(
            required_categories or {"work", "leisure", "health"}
        )
        self.buffer_minutes = buffer_minutes

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
    ) -> DailyPlan:
        if not tasks:
            return DailyPlan(schedule=[], time_window=time_window)

        available_minutes = self._time_window_minutes(time_window)
        task_tuple = tuple(tasks)

        selected = self._solve(task_tuple, available_minutes)

        if selected is None:
            return DailyPlan(schedule=[], time_window=time_window)

        # Sort by category priority for scheduling
        selected_list = list(selected)
        category_order = {"health": 0, "work": 1, "leisure": 2}
        selected_list.sort(key=lambda t: category_order.get(t.category, 2))

        return self._schedule_tasks(selected_list, time_window, self.buffer_minutes)

    def _solve(
        self,
        tasks: tuple[Task, ...],
        time_budget: int,
    ) -> tuple[Task, ...] | None:
        """Solve using memoized recursion.

        State: (index, time_left, categories_found)

        At each task, we either skip or take it.
        At the base case, we check if all required categories are covered.
        """
        required = self.required_categories
        buffer = self.buffer_minutes

        @lru_cache(maxsize=None)
        def recurse(
            index: int,
            time_left: int,
            cats_found: frozenset,
        ) -> tuple[float, tuple[int, ...]]:
            """
            Returns (total_utility, indices_of_selected_tasks).
            Returns (-inf, ()) for invalid paths (constraint not satisfied).
            """
            # Base case: processed all tasks
            if index == len(tasks):
                if required <= cats_found:
                    # All required categories present - valid solution
                    return (0.0, ())
                else:
                    # Missing categories - invalid path
                    return (float("-inf"), ())

            task = tasks[index]

            # Option 1: Skip this task
            skip_util, skip_indices = recurse(index + 1, time_left, cats_found)

            # Option 2: Take this task
            take_util, take_indices = float("-inf"), ()

            if task.duration <= time_left:
                # Update categories found
                new_cats = cats_found | {task.category}
                # Subtract duration + buffer from remaining time
                new_time = time_left - task.duration - buffer

                sub_util, sub_indices = recurse(index + 1, new_time, new_cats)

                if sub_util > float("-inf"):
                    take_util = task.utility + sub_util
                    take_indices = (index,) + sub_indices

            # Return the better option
            if take_util > skip_util:
                return (take_util, take_indices)
            return (skip_util, skip_indices)

        # Start recursion with empty categories found
        utility, indices = recurse(0, time_budget, frozenset())

        # Clear memoization cache
        recurse.cache_clear()

        # No valid solution found
        if utility == float("-inf"):
            return None

        return tuple(tasks[i] for i in indices)
