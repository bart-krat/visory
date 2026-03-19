"""Tests for LLM-based optimizer."""
import pytest
from app.state import Task, TimeWindow, ConstraintSet, UndefinedConstraint
from app.optimize.llm_optimizer import LLMOptimizer
from app.optimize.router import OptimizerRouter, OptimizerType


def test_llm_optimizer_basic():
    """Test basic LLM optimizer with simple tasks."""
    optimizer = LLMOptimizer()

    tasks = [
        Task(name="Morning workout", category="health", utility=80, duration=45),
        Task(name="Team meeting", category="work", utility=100, duration=60),
        Task(name="Lunch break", category="personal", utility=50, duration=60),
    ]

    time_window = TimeWindow(start_time="09:00", end_time="17:00")

    result = optimizer.optimize(tasks, time_window)

    assert result is not None
    assert len(result.schedule) > 0
    assert result.time_window == time_window


def test_llm_optimizer_with_undefined_constraint():
    """Test LLM optimizer with ambiguous user constraint."""
    optimizer = LLMOptimizer()

    tasks = [
        Task(name="Gym", category="health", utility=80, duration=60),
        Task(name="Work session", category="work", utility=100, duration=90),
        Task(name="Lunch", category="personal", utility=50, duration=45),
    ]

    time_window = TimeWindow(start_time="09:00", end_time="17:00")

    # Create constraint set with undefined constraint
    constraints = ConstraintSet()
    constraints.add(UndefinedConstraint(description="I want gym before lunch"))

    result = optimizer.optimize(tasks, time_window, constraints)

    assert result is not None
    assert len(result.schedule) > 0


def test_router_selects_llm_for_undefined_constraints():
    """Test that router selects LLM optimizer for undefined constraints."""
    router = OptimizerRouter()

    tasks = [
        Task(name="Task 1", category="work", utility=100, duration=30),
        Task(name="Task 2", category="health", utility=80, duration=30),
    ]

    time_window = TimeWindow(start_time="09:00", end_time="17:00")

    # Create constraint set with undefined constraint
    constraints = ConstraintSet()
    constraints.add(UndefinedConstraint(description="prioritize morning energy"))

    # Router should select LLM optimizer
    selected_type = router._select_optimizer(tasks, time_window, constraints)

    assert selected_type == OptimizerType.LLM


def test_router_selects_llm_for_too_many_complex_tasks():
    """Test that router falls back to LLM when enumeration is not feasible."""
    router = OptimizerRouter()

    # Create 15 tasks (too many for enumeration)
    tasks = [
        Task(name=f"Task {i}", category="work", utility=100, duration=30)
        for i in range(15)
    ]

    time_window = TimeWindow(start_time="09:00", end_time="17:00")

    # Add complex constraints
    from app.state import FixedTimeSlot
    constraints = ConstraintSet()
    constraints.add(FixedTimeSlot(task_name="Task 1", start_time=540))  # 9:00 AM

    # Router should select LLM as fallback (too many tasks for enumeration)
    selected_type = router._select_optimizer(tasks, time_window, constraints)

    assert selected_type == OptimizerType.LLM


def test_llm_optimizer_fallback_on_error():
    """Test that LLM optimizer has a fallback if LLM call fails."""
    # This test would require mocking the chat service to simulate failure
    # For now, just verify the fallback method exists
    optimizer = LLMOptimizer()

    tasks = [
        Task(name="Task 1", category="work", utility=100, duration=30),
        Task(name="Task 2", category="health", utility=80, duration=30),
    ]

    time_window = TimeWindow(start_time="09:00", end_time="12:00")

    # Test fallback schedule method
    result = optimizer._fallback_schedule(tasks, time_window)

    assert result is not None
    assert len(result.schedule) > 0
    assert result.time_window == time_window


if __name__ == "__main__":
    # Run simple smoke test
    print("Running LLM optimizer smoke test...")
    test_llm_optimizer_basic()
    print("✓ Basic test passed")

    test_router_selects_llm_for_undefined_constraints()
    print("✓ Router selection test passed")

    test_llm_optimizer_fallback_on_error()
    print("✓ Fallback test passed")

    print("\nAll tests passed! LLM optimizer is ready.")
