"""Run optimizer evaluation across all test cases and optimizers.

Tests all 5 optimizers (simple, greedy, knapsack, enumeration, llm) against
10 diverse test cases and reports validity, constraint satisfaction, and performance.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict
import time

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from optimizer_eval_data import OPTIMIZER_EVAL_DATA
from app.state import Task, TimeWindow, ConstraintSet, DailyPlan
from app.state import MustIncludeTask, MustIncludeCategory, FixedTimeSlot, OrderedAfter, TimeRangeConstraint, UndefinedConstraint
from app.optimize.router import OptimizerRouter, OptimizerType


def build_constraint_set(constraint_data_list):
    """Convert constraint dict list to ConstraintSet."""
    cs = ConstraintSet()

    for cdata in constraint_data_list:
        ctype = cdata.get("type")

        if ctype == "must_include_task":
            cs.add(MustIncludeTask(task_name=cdata["task_name"]))
        elif ctype == "must_include_category":
            cs.add(MustIncludeCategory(category=cdata["category"]))
        elif ctype == "fixed_time_slot":
            cs.add(FixedTimeSlot(task_name=cdata["task_name"], start_time=cdata["start_time"]))
        elif ctype == "ordered_after":
            cs.add(OrderedAfter(task_name=cdata["task_name"], after_task=cdata["after_task"]))
        elif ctype == "time_range":
            cs.add(TimeRangeConstraint(
                task_name=cdata["task_name"],
                after_time=cdata.get("after_time"),
                before_time=cdata.get("before_time")
            ))
        elif ctype == "undefined":
            cs.add(UndefinedConstraint(description=cdata["description"]))

    return cs


def convert_test_case(test_data):
    """Convert test case dict to proper data structures."""
    tasks = [
        Task(
            name=t["name"],
            category=t["category"],
            utility=t["utility"],
            duration=t["duration"],
            time_slot=t.get("time_slot")
        )
        for t in test_data["tasks"]
    ]

    time_window = TimeWindow(
        start_time=test_data["time_window"]["start_time"],
        end_time=test_data["time_window"]["end_time"]
    )

    constraints = build_constraint_set(test_data.get("constraints", []))

    return tasks, time_window, constraints


def validate_schedule(daily_plan, time_window, tasks, constraints, test_id):
    """Validate that schedule meets basic requirements."""
    issues = []

    if not daily_plan or not daily_plan.schedule:
        return ["Empty schedule"], False

    # Check 1: Tasks fit in time window
    tw_start_min = parse_time(time_window.start_time)
    tw_end_min = parse_time(time_window.end_time)

    for task in daily_plan.schedule:
        task_start = parse_time(task.start_time)
        task_end = parse_time(task.end_time)

        if task_start < tw_start_min:
            issues.append(f"{task.task} starts before time window")
        if task_end > tw_end_min:
            issues.append(f"{task.task} ends after time window")

    # Check 2: No overlaps
    sorted_tasks = sorted(daily_plan.schedule, key=lambda t: parse_time(t.start_time))
    for i in range(len(sorted_tasks) - 1):
        curr_end = parse_time(sorted_tasks[i].end_time)
        next_start = parse_time(sorted_tasks[i + 1].start_time)
        if curr_end > next_start:
            issues.append(f"Overlap: {sorted_tasks[i].task} and {sorted_tasks[i+1].task}")

    # Check 3: Constraint validation
    scheduled_task_names = {t.task for t in daily_plan.schedule}

    for c in constraints.constraints:
        if isinstance(c, MustIncludeTask):
            if c.task_name not in scheduled_task_names:
                issues.append(f"Missing mandatory task: {c.task_name}")

        elif isinstance(c, MustIncludeCategory):
            scheduled_categories = {t.category for t in daily_plan.schedule}
            if c.category not in scheduled_categories:
                issues.append(f"Missing mandatory category: {c.category}")

        elif isinstance(c, FixedTimeSlot):
            for task in daily_plan.schedule:
                if task.task == c.task_name:
                    actual_start = parse_time(task.start_time)
                    if actual_start != c.start_time:
                        expected_time = f"{c.start_time // 60:02d}:{c.start_time % 60:02d}"
                        issues.append(f"{c.task_name} not at fixed time {expected_time}")

        elif isinstance(c, OrderedAfter):
            task_positions = {}
            for i, task in enumerate(daily_plan.schedule):
                task_positions[task.task] = i

            if c.task_name in task_positions and c.after_task in task_positions:
                if task_positions[c.task_name] <= task_positions[c.after_task]:
                    issues.append(f"{c.task_name} not after {c.after_task}")

        elif isinstance(c, TimeRangeConstraint):
            for task in daily_plan.schedule:
                if task.task == c.task_name:
                    task_start = parse_time(task.start_time)
                    if c.after_time is not None and task_start < c.after_time:
                        issues.append(f"{c.task_name} scheduled too early")
                    if c.before_time is not None and task_start >= c.before_time:
                        issues.append(f"{c.task_name} scheduled too late")

    is_valid = len(issues) == 0
    return issues, is_valid


def parse_time(time_str):
    """Convert HH:MM to minutes from midnight."""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def run_single_optimizer(optimizer_type, tasks, time_window, constraints, test_id):
    """Run a single optimizer on a test case."""
    try:
        router = OptimizerRouter()
        start_time = time.time()

        daily_plan, _, _ = router.optimize(
            tasks=tasks,
            time_window=time_window,
            constraints=constraints,
            optimizer_type=optimizer_type
        )

        elapsed = time.time() - start_time

        issues, is_valid = validate_schedule(daily_plan, time_window, tasks, constraints, test_id)

        return {
            "success": True,
            "daily_plan": daily_plan,
            "is_valid": is_valid,
            "issues": issues,
            "elapsed_ms": elapsed * 1000,
            "num_tasks_scheduled": len(daily_plan.schedule) if daily_plan else 0
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "is_valid": False,
            "issues": [f"Optimizer error: {str(e)}"],
            "elapsed_ms": 0,
            "num_tasks_scheduled": 0
        }


def run_evaluation():
    """Run full evaluation across all test cases and optimizers."""
    print("=" * 80)
    print("OPTIMIZER EVALUATION")
    print("=" * 80)
    print()

    all_optimizers = [
        OptimizerType.SIMPLE,
        OptimizerType.GREEDY,
        OptimizerType.KNAPSACK,
        OptimizerType.ENUMERATION,
        OptimizerType.LLM
    ]

    results = defaultdict(lambda: defaultdict(dict))
    summary = defaultdict(lambda: {"valid": 0, "invalid": 0, "errors": 0})

    # Run each test case
    for test_data in OPTIMIZER_EVAL_DATA:
        test_id = test_data["id"]
        print(f"\n{'='*80}")
        print(f"TEST: {test_id} ({test_data['difficulty']})")
        print(f"Description: {test_data['description']}")
        print(f"Tasks: {len(test_data['tasks'])}, Constraints: {len(test_data['constraints'])}")
        print(f"{'='*80}")

        tasks, time_window, constraints = convert_test_case(test_data)

        # Run each optimizer
        for opt_type in all_optimizers:
            print(f"\n  {opt_type.value:15s} ... ", end="", flush=True)

            result = run_single_optimizer(opt_type, tasks, time_window, constraints, test_id)
            results[test_id][opt_type.value] = result

            # Update summary
            if not result["success"]:
                summary[opt_type.value]["errors"] += 1
                print(f"❌ ERROR: {result['error']}")
            elif result["is_valid"]:
                summary[opt_type.value]["valid"] += 1
                print(f"✓ Valid ({result['num_tasks_scheduled']} tasks, {result['elapsed_ms']:.1f}ms)")
            else:
                summary[opt_type.value]["invalid"] += 1
                print(f"✗ Invalid: {', '.join(result['issues'][:2])}")

    # Print summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    print(f"{'Optimizer':<15s} {'Valid':<8s} {'Invalid':<10s} {'Errors':<8s} {'Success Rate':<15s}")
    print("-" * 80)

    for opt_type in all_optimizers:
        stats = summary[opt_type.value]
        total = stats["valid"] + stats["invalid"] + stats["errors"]
        success_rate = (stats["valid"] / total * 100) if total > 0 else 0

        status = ""
        if success_rate >= 90:
            status = "✅"
        elif success_rate >= 70:
            status = "⚠️"
        else:
            status = "❌"

        print(f"{opt_type.value:<15s} {stats['valid']:<8d} {stats['invalid']:<10d} {stats['errors']:<8d} {success_rate:>6.1f}%  {status}")

    print()

    # Detailed results per test case
    print("\n" + "=" * 80)
    print("DETAILED RESULTS BY TEST CASE")
    print("=" * 80)

    for test_data in OPTIMIZER_EVAL_DATA:
        test_id = test_data["id"]
        print(f"\n{test_id} ({test_data['difficulty']}):")

        test_results = results[test_id]
        for opt_type in all_optimizers:
            result = test_results[opt_type.value]
            status = "✓" if result["is_valid"] else "✗"
            tasks_scheduled = result["num_tasks_scheduled"]
            print(f"  {opt_type.value:<15s} {status} ({tasks_scheduled} tasks)")

    print("\n" + "=" * 80)
    print("Evaluation complete!")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()
