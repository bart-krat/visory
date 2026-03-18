from functools import lru_cache
from dataclasses import dataclass

from app.state import Task, TimeWindow, DailyPlan, ScheduledTask
from app.optimize.base import BaseOptimizer


@dataclass
class TimeGap:
    """A gap of available time."""
    start: int  # minutes from midnight
    end: int    # minutes from midnight

    @property
    def duration(self) -> int:
        return self.end - self.start


class KnapsackOptimizer(BaseOptimizer):
    """Knapsack optimizer using dynamic programming with flexible constraints.

    Algorithm (Approach A - Fix slots first):
    1. Lock in fixed-slot tasks at their designated times
    2. Calculate available time gaps around fixed tasks
    3. Run knapsack on flexible tasks to optimally fill gaps
    4. Merge fixed and flexible tasks into final schedule
    """

    def __init__(self, buffer_minutes: int = 5):
        self.buffer_minutes = buffer_minutes

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
        mandatory_tasks: set[str] | None = None,
        mandatory_categories: set[str] | None = None,
        fixed_slots: dict[str, int] | None = None,
    ) -> DailyPlan:
        if not tasks:
            return DailyPlan(schedule=[], time_window=time_window)

        # Default constraints
        # None/empty means no constraints, NOT "default to all categories"
        mandatory_tasks = mandatory_tasks or set()
        mandatory_categories = frozenset(mandatory_categories) if mandatory_categories else frozenset()
        fixed_slots = fixed_slots or {}

        # Convert time window to minutes
        start_h, start_m = map(int, time_window.start_time.split(":"))
        end_h, end_m = map(int, time_window.end_time.split(":"))
        window_start = start_h * 60 + start_m
        window_end = end_h * 60 + end_m

        # Step 1: Separate fixed and flexible tasks
        fixed_tasks = []
        flexible_tasks = []
        for task in tasks:
            if task.name in fixed_slots:
                fixed_tasks.append((task, fixed_slots[task.name]))
            else:
                flexible_tasks.append(task)

        # Sort fixed tasks by start time
        fixed_tasks.sort(key=lambda x: x[1])

        # Step 2: Validate fixed tasks fit in window
        for task, slot_start in fixed_tasks:
            slot_end = slot_start + task.duration
            if slot_start < window_start or slot_end > window_end:
                # Fixed task doesn't fit - return empty if mandatory
                if task.name in mandatory_tasks:
                    return DailyPlan(schedule=[], time_window=time_window)
                # Otherwise skip this fixed task
                fixed_tasks = [(t, s) for t, s in fixed_tasks if t.name != task.name]
                flexible_tasks.append(task)

        # Step 3: Calculate time gaps around fixed tasks
        gaps = self._calculate_gaps(fixed_tasks, window_start, window_end)

        # Step 4: Track which constraints are already satisfied by fixed tasks
        fixed_categories = {task.category for task, _ in fixed_tasks}
        fixed_task_names = {task.name for task, _ in fixed_tasks}

        # Remaining constraints for flexible tasks
        remaining_categories = mandatory_categories - fixed_categories
        remaining_mandatory = mandatory_tasks - fixed_task_names

        # Step 5: Run knapsack on flexible tasks to fill gaps
        selected_flexible = self._solve_with_gaps(
            tuple(flexible_tasks),
            gaps,
            remaining_mandatory,
            remaining_categories,
        )

        if selected_flexible is None:
            # Can't satisfy constraints
            return DailyPlan(schedule=[], time_window=time_window)

        # Step 6: Schedule flexible tasks into gaps
        scheduled_flexible = self._schedule_in_gaps(selected_flexible, gaps)

        # Step 7: Merge fixed and flexible into final schedule
        all_scheduled = []

        # Add fixed tasks
        for task, slot_start in fixed_tasks:
            all_scheduled.append(self._create_scheduled_task(task, slot_start))

        # Add flexible tasks
        all_scheduled.extend(scheduled_flexible)

        # Sort by start time
        all_scheduled.sort(key=lambda s: s.start_time)

        return DailyPlan(schedule=all_scheduled, time_window=time_window)

    def _calculate_gaps(
        self,
        fixed_tasks: list[tuple[Task, int]],
        window_start: int,
        window_end: int,
    ) -> list[TimeGap]:
        """Calculate available time gaps around fixed tasks."""
        gaps = []
        current_pos = window_start

        for task, slot_start in fixed_tasks:
            # Gap before this fixed task
            gap_end = slot_start - self.buffer_minutes  # Leave buffer before fixed task
            if gap_end > current_pos:
                gaps.append(TimeGap(start=current_pos, end=gap_end))

            # Move past this fixed task
            current_pos = slot_start + task.duration + self.buffer_minutes

        # Gap after all fixed tasks
        if current_pos < window_end:
            gaps.append(TimeGap(start=current_pos, end=window_end))

        return gaps

    def _solve_with_gaps(
        self,
        tasks: tuple[Task, ...],
        gaps: list[TimeGap],
        mandatory_tasks: set[str],
        mandatory_categories: frozenset[str],
    ) -> list[Task] | None:
        """Solve knapsack to select tasks that fit in gaps and satisfy constraints."""
        if not tasks:
            # No flexible tasks - check if constraints are already satisfied
            if not mandatory_tasks and not mandatory_categories:
                return []
            return None

        total_gap_time = sum(g.duration for g in gaps)
        buffer = self.buffer_minutes

        @lru_cache(maxsize=None)
        def recurse(
            index: int,
            time_remaining: int,
            cats_found: frozenset,
            tasks_done: frozenset,
        ) -> tuple[float, tuple[int, ...]]:
            # Base case
            if index == len(tasks):
                if mandatory_categories <= cats_found and mandatory_tasks <= tasks_done:
                    return (0.0, ())
                return (float("-inf"), ())

            task = tasks[index]
            task_time = task.duration + buffer

            # Option 1: Skip (can't skip mandatory tasks)
            skip_util, skip_idx = float("-inf"), ()
            if task.name not in mandatory_tasks:
                skip_util, skip_idx = recurse(index + 1, time_remaining, cats_found, tasks_done)

            # Option 2: Take (if fits)
            take_util, take_idx = float("-inf"), ()
            if task.duration <= time_remaining:
                new_cats = cats_found | {task.category}
                new_done = tasks_done | {task.name}
                new_time = time_remaining - task_time

                sub_util, sub_idx = recurse(index + 1, new_time, new_cats, new_done)
                if sub_util > float("-inf"):
                    take_util = task.utility + sub_util
                    take_idx = (index,) + sub_idx

            if take_util > skip_util:
                return (take_util, take_idx)
            return (skip_util, skip_idx)

        utility, indices = recurse(0, total_gap_time, frozenset(), frozenset())
        recurse.cache_clear()

        if utility == float("-inf"):
            return None

        return [tasks[i] for i in indices]

    def _schedule_in_gaps(
        self,
        tasks: list[Task],
        gaps: list[TimeGap],
    ) -> list[ScheduledTask]:
        """Schedule selected tasks into available gaps."""
        # Sort tasks by category priority for nice ordering
        category_order = {"health": 0, "work": 1, "leisure": 2}
        sorted_tasks = sorted(tasks, key=lambda t: category_order.get(t.category, 2))

        scheduled = []
        task_idx = 0
        buffer = self.buffer_minutes

        for gap in gaps:
            current_time = gap.start

            while task_idx < len(sorted_tasks):
                task = sorted_tasks[task_idx]
                task_end = current_time + task.duration

                if task_end <= gap.end:
                    scheduled.append(self._create_scheduled_task(task, current_time))
                    current_time = task_end + buffer
                    task_idx += 1
                else:
                    # Task doesn't fit in this gap, try next gap
                    break

        return scheduled

    def _create_scheduled_task(self, task: Task, start_minute: int) -> ScheduledTask:
        """Create a ScheduledTask from a Task and start time in minutes."""
        end_minute = start_minute + task.duration
        return ScheduledTask(
            task=task.name,
            category=task.category,
            start_time=f"{start_minute // 60:02d}:{start_minute % 60:02d}",
            end_time=f"{end_minute // 60:02d}:{end_minute % 60:02d}",
            duration_minutes=task.duration,
        )
