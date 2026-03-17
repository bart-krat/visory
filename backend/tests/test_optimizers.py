"""Test the three optimizers with a sample task set."""
from app.state import Task, TimeWindow
from app.optimize import (
    SimpleOptimizer,
    GreedyOptimizer,
    KnapsackOptimizer,
    OptimizerRouter,
    OptimizerType,
)

# Test data set
TASKS = [
    Task(name="go for run", duration=60, utility=85, category="health"),
    Task(name="cost report", duration=120, utility=70, category="work"),
    Task(name="movies", duration=180, utility=60, category="leisure"),
    Task(name="go to gym", duration=90, utility=80, category="health"),
    Task(name="meet boss", duration=60, utility=90, category="work"),
    Task(name="read a book", duration=120, utility=55, category="leisure"),
]

# 8 hour window (9am to 5pm)
TIME_WINDOW = TimeWindow(start_time="09:00", end_time="17:00")


def print_plan(name: str, plan):
    """Pretty print a daily plan."""
    print(f"\n{'='*50}")
    print(f"{name}")
    print(f"{'='*50}")

    total_utility = 0
    total_duration = 0
    categories = set()

    for task in plan.schedule:
        print(f"  {task.start_time}-{task.end_time}: {task.task} ({task.category}, {task.duration_minutes}min)")
        total_duration += task.duration_minutes
        categories.add(task.category)
        # Find utility from original task
        for t in TASKS:
            if t.name == task.task:
                total_utility += t.utility
                break

    print(f"\n  Total duration: {total_duration} min")
    print(f"  Total utility: {total_utility}")
    print(f"  Categories covered: {categories}")


def test_simple_optimizer():
    """Test SimpleOptimizer - orders by category priority."""
    optimizer = SimpleOptimizer()
    plan = optimizer.optimize(TASKS, TIME_WINDOW)
    print_plan("SimpleOptimizer (Health → Work → Leisure)", plan)

    # Verify category ordering
    categories = [t.category for t in plan.schedule]
    health_done = False
    work_done = False
    for cat in categories:
        if cat == "work":
            health_done = True
        if cat == "leisure":
            work_done = True
        if cat == "health" and health_done:
            assert False, "Health task after work task"
        if cat == "work" and work_done:
            assert False, "Work task after leisure task"


def test_greedy_optimizer():
    """Test GreedyOptimizer - maximizes utility/time ratio."""
    optimizer = GreedyOptimizer()
    plan = optimizer.optimize(TASKS, TIME_WINDOW)
    print_plan("GreedyOptimizer (max utility/time ratio)", plan)

    # Calculate ratios of selected tasks
    print("\n  Task ratios (utility/duration):")
    for t in TASKS:
        ratio = t.utility / t.duration
        selected = "✓" if any(s.task == t.name for s in plan.schedule) else " "
        print(f"    {selected} {t.name}: {ratio:.2f}")


def test_knapsack_optimizer():
    """Test KnapsackOptimizer - optimal with category constraint."""
    optimizer = KnapsackOptimizer()
    plan = optimizer.optimize(TASKS, TIME_WINDOW)
    print_plan("KnapsackOptimizer (optimal + all categories)", plan)

    # Verify all categories covered
    categories = {t.category for t in plan.schedule}
    assert "health" in categories, "Missing health task"
    assert "work" in categories, "Missing work task"
    assert "leisure" in categories, "Missing leisure task"
    print("\n  ✓ All required categories covered")


def test_knapsack_tight_window():
    """Test KnapsackOptimizer with tight time window."""
    optimizer = KnapsackOptimizer()
    # Only 4 hours available
    tight_window = TimeWindow(start_time="09:00", end_time="13:00")
    plan = optimizer.optimize(TASKS, tight_window)
    print_plan("KnapsackOptimizer (4-hour window)", plan)

    categories = {t.category for t in plan.schedule}
    if {"health", "work", "leisure"} <= categories:
        print("\n  ✓ All categories covered despite tight window")
    else:
        print(f"\n  ✗ Could not cover all categories: {categories}")


def test_router():
    """Test the OptimizerRouter."""
    router = OptimizerRouter()

    print("\n" + "="*50)
    print("Router Test - comparing all optimizers")
    print("="*50)

    for opt_type in OptimizerType:
        plan = router.optimize(TASKS, TIME_WINDOW, opt_type)
        total_utility = sum(
            next(t.utility for t in TASKS if t.name == s.task)
            for s in plan.schedule
        )
        print(f"\n  {opt_type.value}: {len(plan.schedule)} tasks, utility={total_utility}")


if __name__ == "__main__":
    test_simple_optimizer()
    test_greedy_optimizer()
    test_knapsack_optimizer()
    test_knapsack_tight_window()
    test_router()
    print("\n\n✓ All tests passed!")
