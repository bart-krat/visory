"""Test the three optimizers with a sample task set."""
from app.state import Task, TimeWindow, CATEGORY_UTILITY
from app.optimize import (
    SimpleOptimizer,
    GreedyOptimizer,
    KnapsackOptimizer,
    OptimizerRouter,
    OptimizerType,
)

# Test data set (simulating tasks after categorize + constraints phases)
TASKS = [
    Task(name="go for run", category="health", utility=CATEGORY_UTILITY["health"], duration=60),
    Task(name="cost report", category="work", utility=CATEGORY_UTILITY["work"], duration=120),
    Task(name="movies", category="leisure", utility=CATEGORY_UTILITY["leisure"], duration=180),
    Task(name="go to gym", category="health", utility=CATEGORY_UTILITY["health"], duration=90),
    Task(name="meet boss", category="work", utility=CATEGORY_UTILITY["work"], duration=60),
    Task(name="read a book", category="leisure", utility=CATEGORY_UTILITY["leisure"], duration=120),
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


def test_greedy_optimizer():
    """Test GreedyOptimizer - maximizes utility/time ratio."""
    optimizer = GreedyOptimizer()
    plan = optimizer.optimize(TASKS, TIME_WINDOW)
    print_plan("GreedyOptimizer (max utility/time ratio)", plan)

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

    categories = {t.category for t in plan.schedule}
    assert "health" in categories, "Missing health task"
    assert "work" in categories, "Missing work task"
    assert "leisure" in categories, "Missing leisure task"
    print("\n  ✓ All required categories covered")


def test_knapsack_tight_window():
    """Test KnapsackOptimizer with tight time window."""
    optimizer = KnapsackOptimizer()
    tight_window = TimeWindow(start_time="09:00", end_time="13:00")
    plan = optimizer.optimize(TASKS, tight_window)
    print_plan("KnapsackOptimizer (4-hour window)", plan)

    categories = {t.category for t in plan.schedule}
    if {"health", "work", "leisure"} <= categories:
        print("\n  ✓ All categories covered despite tight window")
    else:
        print(f"\n  ✗ Could not cover all categories: {categories}")


def test_router_auto_select():
    """Test the OptimizerRouter auto-selection."""
    router = OptimizerRouter()

    print("\n" + "="*50)
    print("Router Auto-Selection Test")
    print("="*50)

    # 8hr window - all tasks fit → SIMPLE
    wide_window = TimeWindow("09:00", "17:00")
    selected = router._select_optimizer(TASKS, wide_window)
    print(f"\n  8hr window: {selected.value}")

    # 4hr window - tasks don't fit → KNAPSACK (with constraints)
    tight_window = TimeWindow("09:00", "13:00")
    selected = router._select_optimizer(TASKS, tight_window)
    print(f"  4hr window (constraints): {selected.value}")

    # 4hr window - no constraints → GREEDY
    router.require_all_categories = False
    selected = router._select_optimizer(TASKS, tight_window)
    print(f"  4hr window (no constraints): {selected.value}")


if __name__ == "__main__":
    test_simple_optimizer()
    test_greedy_optimizer()
    test_knapsack_optimizer()
    test_knapsack_tight_window()
    test_router_auto_select()
    print("\n\n✓ All tests passed!")
