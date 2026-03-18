"""Optimizer router - selects and configures the appropriate optimizer."""
from enum import Enum

from app.state import Task, TimeWindow, DailyPlan, ConstraintSet
from app.optimize.base import BaseOptimizer
from app.optimize.simple_optimizer import SimpleOptimizer
from app.optimize.greedy_optimizer import GreedyOptimizer
from app.optimize.knapsack_optimizer import KnapsackOptimizer
from app.optimize.enumeration_optimizer import EnumerationOptimizer
from app.utils import time_window_minutes


class OptimizerType(str, Enum):
    SIMPLE = "simple"          # Orders by category: Health -> Work -> Personal
    GREEDY = "greedy"          # Maximizes utility/time ratio
    KNAPSACK = "knapsack"      # DP with mandatory tasks/categories
    ENUMERATION = "enumeration"  # Brute force optimal (tasks < 10, complex constraints)


class OptimizerRouter:
    """Routes optimization requests to the appropriate optimizer.

    Accepts a ConstraintSet and selects the best optimizer based on:
    - Number of tasks
    - Types of constraints present
    - Whether tasks fit in the time window
    """

    def __init__(self):
        """Initialize router."""
        self._optimizers: dict[OptimizerType, BaseOptimizer] = {
            OptimizerType.SIMPLE: SimpleOptimizer(),
            OptimizerType.GREEDY: GreedyOptimizer(),
            OptimizerType.KNAPSACK: KnapsackOptimizer(),
            OptimizerType.ENUMERATION: EnumerationOptimizer(),
        }
        self._constraints = ConstraintSet()

    @property
    def constraints(self) -> ConstraintSet:
        """Get current constraints."""
        return self._constraints

    def set_constraints(self, constraints: ConstraintSet) -> None:
        """Set constraints for optimization.

        Args:
            constraints: ConstraintSet with typed constraints.
        """
        self._constraints = constraints

    def clear_constraints(self) -> None:
        """Clear all constraints."""
        self._constraints = ConstraintSet()

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
        constraints: ConstraintSet | None = None,
        optimizer_type: OptimizerType | None = None,
    ) -> DailyPlan:
        """Run optimization with the given constraints.

        Args:
            tasks: Tasks to optimize.
            time_window: Available time window.
            constraints: Constraints to apply. If None, uses stored constraints.
            optimizer_type: Force a specific optimizer. If None, auto-select.

        Returns:
            Optimized DailyPlan.
        """
        # Use provided constraints or fall back to stored
        cs = constraints if constraints is not None else self._constraints

        # Auto-select optimizer if not specified
        if optimizer_type is None:
            optimizer_type = self._select_optimizer(tasks, time_window, cs)

        optimizer = self._optimizers[optimizer_type]

        # Route to appropriate optimizer with extracted constraints
        if optimizer_type == OptimizerType.KNAPSACK:
            return optimizer.optimize(
                tasks,
                time_window,
                mandatory_tasks=cs.mandatory_tasks or None,
                mandatory_categories=cs.mandatory_categories or None,
            )

        if optimizer_type == OptimizerType.ENUMERATION:
            return optimizer.optimize(
                tasks,
                time_window,
                mandatory_tasks=cs.mandatory_tasks or None,
                mandatory_categories=cs.mandatory_categories or None,
                fixed_slots=cs.fixed_slots or None,
                ordering_constraints=cs.ordering_constraints or None,
            )

        # SIMPLE and GREEDY don't use constraints
        return optimizer.optimize(tasks, time_window)

    def _select_optimizer(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
        constraints: ConstraintSet,
    ) -> OptimizerType:
        """Auto-select the appropriate optimizer.

        Selection logic:
        1. Complex constraints (fixed_slots, ordering) → ENUMERATION (if tasks < 10)
        2. Tasks fit in window → SIMPLE
        3. Tasks overflow + has constraints → KNAPSACK
        4. Tasks overflow + no constraints → GREEDY
        """
        num_tasks = len(tasks)

        # Complex constraints require enumeration
        if constraints.has_complex_constraints():
            if num_tasks < 10:
                return OptimizerType.ENUMERATION
            else:
                # Too many tasks - fall back to knapsack (ignores complex constraints)
                return OptimizerType.KNAPSACK

        # Check if tasks fit in window
        total_duration = sum(t.duration for t in tasks)
        buffer_time = (num_tasks - 1) * 5 if num_tasks > 1 else 0
        total_with_buffer = total_duration + buffer_time
        available_minutes = self._time_window_minutes(time_window)

        # All tasks fit → just order them
        if total_with_buffer <= available_minutes:
            return OptimizerType.SIMPLE

        # Tasks don't fit, need selection
        if constraints.mandatory_tasks or constraints.mandatory_categories:
            return OptimizerType.KNAPSACK
        else:
            return OptimizerType.GREEDY

    def _time_window_minutes(self, tw: TimeWindow) -> int:
        """Convert TimeWindow to total available minutes."""
        return time_window_minutes(tw.start_time, tw.end_time)


_router: OptimizerRouter | None = None


def get_optimizer_router() -> OptimizerRouter:
    """Get the global optimizer router instance."""
    global _router
    if _router is None:
        _router = OptimizerRouter()
    return _router
