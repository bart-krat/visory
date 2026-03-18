"""Optimizer service.

Uses OptimizerRouter to auto-select the appropriate optimizer.
"""
from app.optimize.router import OptimizerRouter


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


_optimizer_service: OptimizerService | None = None


def get_optimizer_service() -> OptimizerService:
    """Get or create the singleton OptimizerService instance."""
    global _optimizer_service
    if _optimizer_service is None:
        _optimizer_service = OptimizerService()
    return _optimizer_service
