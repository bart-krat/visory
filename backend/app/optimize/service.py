"""Optimizer service facade for backward compatibility.

Wraps the OptimizerRouter and converts between TaskWithDuration and Task.
"""
from app.state import Task, TaskWithDuration, TimeWindow, DailyPlan
from app.optimize.router import OptimizerRouter, OptimizerType, get_optimizer_router


# Default utility values by category
DEFAULT_UTILITY = {
    "health": 10.0,
    "work": 8.0,
    "leisure": 5.0,
}


class OptimizerService:
    """Service facade for task optimization.

    Converts TaskWithDuration to Task and delegates to OptimizerRouter.
    """

    def __init__(self, optimizer_type: OptimizerType = OptimizerType.SIMPLE):
        self.router = get_optimizer_router()
        self.optimizer_type = optimizer_type

    def create_optimizer(self, optimizer_type: OptimizerType | None = None) -> None:
        """Set the optimizer type to use.

        Args:
            optimizer_type: Which optimizer to use. Defaults to SIMPLE.
        """
        if optimizer_type:
            self.optimizer_type = optimizer_type

    def run_optimizer(
        self,
        tasks_with_duration: list[TaskWithDuration],
        time_window: TimeWindow,
    ) -> DailyPlan:
        """Run optimization on tasks.

        Args:
            tasks_with_duration: Tasks with categories and durations.
            time_window: Available time window.

        Returns:
            Optimized DailyPlan.
        """
        # Convert TaskWithDuration to Task
        tasks = [
            Task(
                name=t.task,
                duration=t.duration_minutes,
                utility=DEFAULT_UTILITY.get(t.category, 5.0),
                category=t.category,
            )
            for t in tasks_with_duration
        ]

        return self.router.optimize(tasks, time_window, self.optimizer_type)


_optimizer_service: OptimizerService | None = None


def get_optimizer_service() -> OptimizerService:
    """Get or create the singleton OptimizerService instance."""
    global _optimizer_service
    if _optimizer_service is None:
        _optimizer_service = OptimizerService()
    return _optimizer_service
