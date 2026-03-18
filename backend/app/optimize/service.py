"""Optimizer service.

Uses OptimizerRouter to auto-select the appropriate optimizer.
"""
from app.state import Task, TimeWindow, DailyPlan
from app.optimize.router import OptimizerRouter, OptimizerType


class OptimizerService:
    """Service for task optimization.

    Auto-selects optimizer based on:
    - Tasks fit in window → SimpleOptimizer
    - Tasks don't fit + constraints → KnapsackOptimizer
    - Tasks don't fit + no constraints → GreedyOptimizer
    """

    def __init__(self):
        """Initialize the optimizer service."""
        self.router = OptimizerRouter()

    def create_optimizer(self, require_all_categories: bool = True) -> None:
        """Configure the optimizer.

        Args:
            require_all_categories: Whether to enforce category coverage.
        """
        self.router.require_all_categories = require_all_categories

    def run_optimizer(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
    ) -> DailyPlan:
        """Run optimization on tasks.

        Auto-selects the appropriate optimizer based on task/window fit
        and constraint requirements.

        Args:
            tasks: Tasks with name, category, utility, and duration.
            time_window: Available time window.

        Returns:
            Optimized DailyPlan.
        """
        return self.router.optimize(tasks, time_window, optimizer_type=None)


_optimizer_service: OptimizerService | None = None


def get_optimizer_service() -> OptimizerService:
    """Get or create the singleton OptimizerService instance."""
    global _optimizer_service
    if _optimizer_service is None:
        _optimizer_service = OptimizerService()
    return _optimizer_service
