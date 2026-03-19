"""Enumeration optimizer - guarantees optimal solution for small task sets.

Tries all valid task subsets and orderings to find the globally optimal
schedule that satisfies all constraints.
"""
from itertools import combinations, permutations
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


class EnumerationOptimizer(BaseOptimizer):
    """Enumeration optimizer that guarantees optimal solution.

    Algorithm:
    1. Generate all subsets of tasks (2^n)
    2. Filter subsets that satisfy mandatory constraints
    3. For each valid subset, try all permutations (n!)
    4. Filter permutations that satisfy ordering constraints
    5. Try to schedule each permutation into gaps
    6. Return the feasible schedule with highest utility

    Complexity: O(2^n * n!) - only suitable for n <= 8-10 tasks.
    """

    def __init__(self, buffer_minutes: int = 5, max_tasks: int = 10):
        self.buffer_minutes = buffer_minutes
        self.max_tasks = max_tasks

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
        mandatory_tasks: set[str] | None = None,
        mandatory_categories: set[str] | None = None,
        fixed_slots: dict[str, int] | None = None,
        ordering_constraints: list[tuple[str, str]] | None = None,
        time_range_constraints: dict[str, tuple[int | None, int | None]] | None = None,
    ) -> DailyPlan:
        """Find optimal schedule by enumeration.

        Args:
            tasks: Tasks to schedule.
            time_window: Available time window.
            mandatory_tasks: Task names that must be included.
            mandatory_categories: Categories that must have at least one task.
            fixed_slots: Tasks fixed at specific times {task_name: minute_of_day}.
            ordering_constraints: List of (before, after) task name pairs.
            time_range_constraints: Tasks with time range restrictions {task_name: (after_time, before_time)}.

        Returns:
            Optimal DailyPlan, or empty plan if no valid schedule exists.
        """
        if not tasks:
            return DailyPlan(schedule=[], time_window=time_window)

        if len(tasks) > self.max_tasks:
            raise ValueError(
                f"Too many tasks ({len(tasks)}) for enumeration. "
                f"Max supported: {self.max_tasks}"
            )

        # Defaults
        mandatory_tasks = mandatory_tasks or set()
        mandatory_categories = mandatory_categories or set()
        fixed_slots = fixed_slots or {}
        ordering_constraints = ordering_constraints or []
        time_range_constraints = time_range_constraints or {}

        # Convert time window to minutes
        window_start, window_end = self._parse_time_window(time_window)

        # Separate fixed and flexible tasks
        fixed_tasks = []
        flexible_tasks = []
        for task in tasks:
            if task.name in fixed_slots:
                fixed_tasks.append((task, fixed_slots[task.name]))
            else:
                flexible_tasks.append(task)

        # Sort and validate fixed tasks
        fixed_tasks.sort(key=lambda x: x[1])
        valid_fixed = self._validate_fixed_tasks(
            fixed_tasks, window_start, window_end, mandatory_tasks
        )
        if valid_fixed is None:
            return DailyPlan(schedule=[], time_window=time_window)
        fixed_tasks = valid_fixed

        # Calculate gaps around fixed tasks
        gaps = self._calculate_gaps(fixed_tasks, window_start, window_end)

        # Track what's already satisfied by fixed tasks
        fixed_task_names = {t.name for t, _ in fixed_tasks}
        fixed_categories = {t.category for t, _ in fixed_tasks}

        remaining_mandatory_tasks = mandatory_tasks - fixed_task_names
        remaining_mandatory_categories = mandatory_categories - fixed_categories

        # Generate all valid subsets with their utilities
        # A valid subset must contain all mandatory tasks and categories
        valid_subsets = []

        for subset_size in range(len(flexible_tasks) + 1):
            for subset in combinations(flexible_tasks, subset_size):
                subset_list = list(subset)

                # Check mandatory task constraint
                subset_names = {t.name for t in subset_list}
                if not remaining_mandatory_tasks <= subset_names:
                    continue

                # Check mandatory category constraint
                subset_categories = {t.category for t in subset_list}
                if not remaining_mandatory_categories <= subset_categories:
                    continue

                # Calculate utility and store
                subset_utility = sum(t.utility for t in subset_list)
                valid_subsets.append((subset_list, subset_utility))

        # Sort by utility DESCENDING - highest utility first
        valid_subsets.sort(key=lambda x: -x[1])

        # Compute implicit time constraints from ordering constraints with fixed tasks
        # If task A must come after fixed task B, then A must start after B ends
        # If task A must come before fixed task B, then A must start before B starts
        implicit_time_constraints = dict(time_range_constraints) if time_range_constraints else {}
        task_durations = {t.name: t.duration for t in tasks}

        for before_task, after_task in ordering_constraints:
            # If before_task is fixed, after_task must start after before_task ends
            if before_task in fixed_slots:
                fixed_end = fixed_slots[before_task] + task_durations.get(before_task, 0) + self.buffer_minutes
                if after_task in implicit_time_constraints:
                    # Merge: take the later "after" time
                    existing = implicit_time_constraints[after_task]
                    implicit_time_constraints[after_task] = (
                        max(existing[0] or 0, fixed_end),
                        existing[1],
                    )
                else:
                    implicit_time_constraints[after_task] = (fixed_end, None)

            # If after_task is fixed, before_task must start before after_task starts
            if after_task in fixed_slots:
                fixed_start = fixed_slots[after_task] - self.buffer_minutes
                if before_task in implicit_time_constraints:
                    # Merge: take the earlier "before" time
                    existing = implicit_time_constraints[before_task]
                    before_time = existing[1]
                    if before_time is None:
                        before_time = fixed_start
                    else:
                        before_time = min(before_time, fixed_start)
                    implicit_time_constraints[before_task] = (existing[0], before_time)
                else:
                    implicit_time_constraints[before_task] = (None, fixed_start)

        # Try subsets in order of decreasing utility
        # FIRST valid solution is GUARANTEED optimal
        best_flexible_schedule = None

        for subset_list, subset_utility in valid_subsets:
            # Try all permutations of this subset
            for perm in permutations(subset_list):
                perm_list = list(perm)

                # Try to schedule this permutation with implicit time constraints
                schedule = self._try_schedule(perm_list, gaps, implicit_time_constraints)
                if schedule is None:
                    continue

                # Check ordering constraints against FULL schedule (fixed + flexible)
                full_schedule = []
                for task, slot_start in fixed_tasks:
                    full_schedule.append((task.name, slot_start))
                for st in schedule:
                    start_mins = int(st.start_time.split(":")[0]) * 60 + int(st.start_time.split(":")[1])
                    full_schedule.append((st.task, start_mins))

                if not self._satisfies_ordering_with_times(full_schedule, ordering_constraints):
                    continue

                # FOUND! First valid = optimal (sorted by utility desc)
                best_flexible_schedule = schedule
                break

            # If we found a valid schedule, stop searching
            if best_flexible_schedule is not None:
                break

        if best_flexible_schedule is None and remaining_mandatory_tasks:
            # Can't satisfy constraints
            return DailyPlan(schedule=[], time_window=time_window)

        # Merge fixed and flexible schedules
        all_scheduled = []

        # Add fixed tasks
        for task, slot_start in fixed_tasks:
            all_scheduled.append(self._create_scheduled_task(task, slot_start))

        # Add flexible tasks
        if best_flexible_schedule:
            all_scheduled.extend(best_flexible_schedule)

        # Sort by start time
        all_scheduled.sort(key=lambda s: s.start_time)

        return DailyPlan(schedule=all_scheduled, time_window=time_window)

    def _parse_time_window(self, time_window: TimeWindow) -> tuple[int, int]:
        """Parse time window to minutes from midnight."""
        start_h, start_m = map(int, time_window.start_time.split(":"))
        end_h, end_m = map(int, time_window.end_time.split(":"))
        return start_h * 60 + start_m, end_h * 60 + end_m

    def _validate_fixed_tasks(
        self,
        fixed_tasks: list[tuple[Task, int]],
        window_start: int,
        window_end: int,
        mandatory_tasks: set[str],
    ) -> list[tuple[Task, int]] | None:
        """Validate fixed tasks fit in window. Returns None if mandatory task doesn't fit."""
        valid = []
        for task, slot_start in fixed_tasks:
            slot_end = slot_start + task.duration
            if slot_start >= window_start and slot_end <= window_end:
                valid.append((task, slot_start))
            elif task.name in mandatory_tasks:
                return None  # Mandatory fixed task doesn't fit
        return valid

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
            gap_end = slot_start - self.buffer_minutes
            if gap_end > current_pos:
                gaps.append(TimeGap(start=current_pos, end=gap_end))
            current_pos = slot_start + task.duration + self.buffer_minutes

        if current_pos < window_end:
            gaps.append(TimeGap(start=current_pos, end=window_end))

        return gaps

    def _satisfies_ordering(
        self,
        tasks: list[Task],
        ordering_constraints: list[tuple[str, str]],
    ) -> bool:
        """Check if task ordering satisfies all ordering constraints."""
        if not ordering_constraints:
            return True

        # Build position map
        position = {t.name: i for i, t in enumerate(tasks)}

        for before, after in ordering_constraints:
            # Both tasks must be present for constraint to apply
            if before not in position or after not in position:
                continue
            if position[before] >= position[after]:
                return False

        return True

    def _try_schedule(
        self,
        tasks: list[Task],
        gaps: list[TimeGap],
        time_range_constraints: dict[str, tuple[int | None, int | None]] | None = None,
    ) -> list[ScheduledTask] | None:
        """Try to schedule tasks in order into gaps, respecting time range constraints.

        Args:
            tasks: Tasks to schedule in order.
            gaps: Available time gaps.
            time_range_constraints: Time range restrictions {task_name: (after_time, before_time)}.

        Returns:
            List of scheduled tasks, or None if tasks don't fit.
        """
        if not tasks:
            return []

        time_range_constraints = time_range_constraints or {}
        scheduled = []
        task_idx = 0
        buffer = self.buffer_minutes

        for gap in gaps:
            current_time = gap.start

            while task_idx < len(tasks):
                task = tasks[task_idx]
                task_end = current_time + task.duration

                # Check if task fits in this gap physically
                if task_end > gap.end:
                    # Task doesn't fit in this gap, try next gap
                    break

                # Check time range constraint if exists
                if task.name in time_range_constraints:
                    after_time, before_time = time_range_constraints[task.name]

                    # Check if current_time satisfies the constraint
                    if after_time is not None and current_time < after_time:
                        # Task must start after after_time, but current_time is too early
                        # Try to advance to after_time if it's still in this gap
                        if after_time < gap.end and after_time + task.duration <= gap.end:
                            current_time = after_time
                            task_end = current_time + task.duration
                        else:
                            # Can't place this task in this gap due to time range constraint
                            break

                    if before_time is not None and current_time >= before_time:
                        # Task must start before before_time, but current_time is too late
                        # This task can't go in this or any later gap
                        break

                # Task fits and satisfies constraints
                scheduled.append(self._create_scheduled_task(task, current_time))
                current_time = task_end + buffer
                task_idx += 1

        # Check if all tasks were scheduled
        if task_idx < len(tasks):
            return None

        return scheduled

    def _create_scheduled_task(self, task: Task, start_minute: int) -> ScheduledTask:
        """Create a ScheduledTask from a Task and start time."""
        end_minute = start_minute + task.duration
        return ScheduledTask(
            task=task.name,
            category=task.category,
            start_time=f"{start_minute // 60:02d}:{start_minute % 60:02d}",
            end_time=f"{end_minute // 60:02d}:{end_minute % 60:02d}",
            duration_minutes=task.duration,
        )

    def _satisfies_ordering_with_times(
        self,
        scheduled: list[tuple[str, int]],
        ordering_constraints: list[tuple[str, str]],
    ) -> bool:
        """Check ordering constraints using actual scheduled times.

        Args:
            scheduled: List of (task_name, start_minute) for ALL tasks (fixed + flexible).
            ordering_constraints: List of (before, after) task name pairs.

        Returns:
            True if all ordering constraints are satisfied.
        """
        if not ordering_constraints:
            return True

        # Build time map: task_name -> start_minute
        time_map = {name: start for name, start in scheduled}

        for before, after in ordering_constraints:
            # Both tasks must be scheduled for constraint to apply
            if before not in time_map or after not in time_map:
                continue

            # "before" task must start earlier than "after" task
            if time_map[before] >= time_map[after]:
                return False

        return True
