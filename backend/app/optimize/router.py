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
    """Routes optimization requests to the appropriate optimizer."""

    def __init__(self, default: OptimizerType = OptimizerType.SIMPLE):
        self._optimizers: dict[OptimizerType, BaseOptimizer] = {
            OptimizerType.SIMPLE: SimpleOptimizer(),
            OptimizerType.GREEDY: GreedyOptimizer(),
            OptimizerType.KNAPSACK: KnapsackOptimizer(),
        }
        self._default = default

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
        optimizer_type: OptimizerType | None = None,
    ) -> DailyPlan:
        """Run optimization with the specified (or default) optimizer."""
        opt_type = optimizer_type or self._default
        optimizer = self._optimizers[opt_type]
        return optimizer.optimize(tasks, time_window)


_router: OptimizerRouter | None = None


def get_optimizer_router() -> OptimizerRouter:
    global _router
    if _router is None:
        _router = OptimizerRouter()
    return _router
