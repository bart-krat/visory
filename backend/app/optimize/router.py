from enum import Enum

from app.state import Task, TimeWindow, DailyPlan
from app.optimize.base import BaseOptimizer
from app.optimize.simple_optimizer import SimpleOptimizer
from app.optimize.greedy_optimizer import GreedyOptimizer
from app.optimize.knapsack_optimizer import KnapsackOptimizer


class OptimizerType(str, Enum):
    SIMPLE = "simple"      # Orders by category: Health -> Work -> Leisure
    GREEDY = "greedy"      # Maximizes utility/time ratio
    KNAPSACK = "knapsack"  # DP with category coverage constraint


class OptimizerRouter:
    """Routes optimization requests to the appropriate optimizer.

    Routing logic:
    1. If total task duration fits in window → SimpleOptimizer
       (No selection needed, just order tasks)

    2. If duration > window AND no constraints → GreedyOptimizer
       (Need to select tasks, greedy is fast and good enough)

    3. If duration > window AND has constraints → KnapsackOptimizer
       (Need optimal selection respecting constraints)
    """

    def __init__(self, require_all_categories: bool = True):
        """Initialize router.

        Args:
            require_all_categories: Whether to enforce that the plan
                                    includes at least one task from each
                                    category (health, work, leisure).
        """
        self._optimizers: dict[OptimizerType, BaseOptimizer] = {
            OptimizerType.SIMPLE: SimpleOptimizer(),
            OptimizerType.GREEDY: GreedyOptimizer(),
            OptimizerType.KNAPSACK: KnapsackOptimizer(),
        }
        self.require_all_categories = require_all_categories

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
        optimizer_type: OptimizerType | None = None,
    ) -> DailyPlan:
        """Run optimization, auto-selecting optimizer if not specified.

        Args:
            tasks: Tasks to optimize.
            time_window: Available time window.
            optimizer_type: Force a specific optimizer. If None, auto-select.

        Returns:
            Optimized DailyPlan.
        """
        if optimizer_type is None:
            optimizer_type = self._select_optimizer(tasks, time_window)

        optimizer = self._optimizers[optimizer_type]
        return optimizer.optimize(tasks, time_window)

    def _select_optimizer(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
    ) -> OptimizerType:
        """Auto-select the appropriate optimizer.

        Logic:
        1. tasks fit in window → SIMPLE
        2. tasks don't fit, no constraints → GREEDY
        3. tasks don't fit, has constraints → KNAPSACK
        """
        total_duration = sum(t.duration for t in tasks)
        buffer_time = (len(tasks) - 1) * 5 if len(tasks) > 1 else 0
        total_with_buffer = total_duration + buffer_time

        available_minutes = self._time_window_minutes(time_window)

        # All tasks fit → just order them
        if total_with_buffer <= available_minutes:
            return OptimizerType.SIMPLE

        # Tasks don't fit, need selection
        if self.require_all_categories:
            return OptimizerType.KNAPSACK
        else:
            return OptimizerType.GREEDY

    def _time_window_minutes(self, time_window: TimeWindow) -> int:
        """Convert TimeWindow to total available minutes."""
        start_h, start_m = map(int, time_window.start_time.split(":"))
        end_h, end_m = map(int, time_window.end_time.split(":"))
        return (end_h * 60 + end_m) - (start_h * 60 + start_m)


_router: OptimizerRouter | None = None


def get_optimizer_router() -> OptimizerRouter:
    global _router
    if _router is None:
        _router = OptimizerRouter()
    return _router
