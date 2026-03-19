"""Run constraint matcher evaluation and report accuracy.

This script tests the constraint matcher (matcher.py) against ground truth
dataset and reports exact match accuracy, partial match accuracy, and errors.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict
import json

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from matcher_eval_data import MATCHER_EVAL_DATA, SAMPLE_TASKS
from app.state import Task
from app.constraints.matcher import ConstraintMatcher


def normalize_constraint(constraint_dict):
    """Normalize constraint dict for comparison (sort keys, handle None)."""
    # Create a normalized tuple for comparison
    ctype = constraint_dict.get("type")

    if ctype == "must_include_task":
        return ("must_include_task", constraint_dict.get("task_name"))
    elif ctype == "must_include_category":
        return ("must_include_category", constraint_dict.get("category"))
    elif ctype == "fixed_time_slot":
        return ("fixed_time_slot", constraint_dict.get("task_name"), constraint_dict.get("start_time"))
    elif ctype == "ordered_after":
        return ("ordered_after", constraint_dict.get("task_name"), constraint_dict.get("after_task"))
    elif ctype == "time_range":
        return ("time_range", constraint_dict.get("task_name"),
                constraint_dict.get("after_time"), constraint_dict.get("before_time"))
    elif ctype == "undefined":
        return ("undefined", constraint_dict.get("description"))
    else:
        return ("unknown", str(constraint_dict))


def compare_constraints(expected, actual):
    """Compare expected and actual constraint lists.

    Returns:
        exact_match: bool - True if lists are exactly the same
        missing: list - Constraints in expected but not in actual
        extra: list - Constraints in actual but not in expected
    """
    expected_normalized = {normalize_constraint(c) for c in expected}
    actual_normalized = {normalize_constraint(c) for c in actual}

    exact_match = expected_normalized == actual_normalized
    missing = expected_normalized - actual_normalized
    extra = actual_normalized - expected_normalized

    return exact_match, missing, extra


def format_constraint(constraint_tuple):
    """Format a normalized constraint tuple for display."""
    if constraint_tuple[0] == "must_include_task":
        return f"MustIncludeTask({constraint_tuple[1]})"
    elif constraint_tuple[0] == "must_include_category":
        return f"MustIncludeCategory({constraint_tuple[1]})"
    elif constraint_tuple[0] == "fixed_time_slot":
        time_str = f"{constraint_tuple[2] // 60:02d}:{constraint_tuple[2] % 60:02d}"
        return f"FixedTimeSlot({constraint_tuple[1]} at {time_str})"
    elif constraint_tuple[0] == "ordered_after":
        return f"OrderedAfter({constraint_tuple[1]} after {constraint_tuple[2]})"
    elif constraint_tuple[0] == "time_range":
        after = f"{constraint_tuple[2] // 60:02d}:{constraint_tuple[2] % 60:02d}" if constraint_tuple[2] else "start"
        before = f"{constraint_tuple[3] // 60:02d}:{constraint_tuple[3] % 60:02d}" if constraint_tuple[3] else "end"
        return f"TimeRange({constraint_tuple[1]} between {after}-{before})"
    elif constraint_tuple[0] == "undefined":
        return f"Undefined(\"{constraint_tuple[1]}\")"
    else:
        return str(constraint_tuple)


def run_evaluation():
    """Run matcher evaluation."""
    print("=" * 80)
    print("CONSTRAINT MATCHER EVALUATION")
    print("=" * 80)
    print()

    # Convert sample tasks to Task objects
    tasks = [Task(name=t["name"], category=t["category"], utility=100, duration=30)
             for t in SAMPLE_TASKS]

    # Initialize matcher
    matcher = ConstraintMatcher(tasks)

    # Results tracking
    exact_matches = 0
    partial_matches = 0
    failures = 0
    mismatches = []

    print(f"Testing {len(MATCHER_EVAL_DATA)} constraint patterns...")
    print()

    # Run each test case
    for i, test_case in enumerate(MATCHER_EVAL_DATA, 1):
        test_id = test_case["id"]
        user_input = test_case["user_input"]
        expected = test_case["expected_output"]
        difficulty = test_case["difficulty"]

        print(f"\n{'='*80}")
        print(f"TEST {i}: {test_id} ({difficulty})")
        print(f"Input: \"{user_input}\"")
        print(f"{'='*80}")

        try:
            # Run matcher
            result = matcher.match(user_input)
            actual = result.to_dict()

            # Compare results
            exact_match, missing, extra = compare_constraints(expected, actual)

            if exact_match:
                exact_matches += 1
                print("✓ EXACT MATCH")
                print(f"  Matched all {len(expected)} constraint(s)")
            elif len(missing) == 0 and len(extra) > 0:
                partial_matches += 1
                print("⚠ PARTIAL MATCH (extra constraints)")
                print(f"  Expected {len(expected)}, got {len(actual)}")
                print("  Extra constraints:")
                for c in extra:
                    print(f"    + {format_constraint(c)}")
            elif len(missing) > 0:
                failures += 1
                print("✗ MISMATCH")
                print(f"  Expected {len(expected)}, got {len(actual)}")

                if missing:
                    print("  Missing constraints:")
                    for c in missing:
                        print(f"    - {format_constraint(c)}")

                if extra:
                    print("  Extra constraints:")
                    for c in extra:
                        print(f"    + {format_constraint(c)}")

                mismatches.append({
                    "test_id": test_id,
                    "input": user_input,
                    "expected": expected,
                    "actual": actual,
                    "missing": missing,
                    "extra": extra
                })
            else:
                # Edge case: both missing and extra but some overlap
                partial_matches += 1
                print("⚠ PARTIAL MATCH")
                print(f"  Expected {len(expected)}, got {len(actual)}")

                if missing:
                    print("  Missing:")
                    for c in missing:
                        print(f"    - {format_constraint(c)}")

                if extra:
                    print("  Extra:")
                    for c in extra:
                        print(f"    + {format_constraint(c)}")

        except Exception as e:
            failures += 1
            print(f"✗ ERROR: {str(e)}")
            mismatches.append({
                "test_id": test_id,
                "input": user_input,
                "error": str(e)
            })

    # Print summary
    total = len(MATCHER_EVAL_DATA)
    exact_pct = (exact_matches / total) * 100
    partial_pct = (partial_matches / total) * 100
    failure_pct = (failures / total) * 100

    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total test cases:    {total}")
    print(f"✓ Exact matches:     {exact_matches:2d} ({exact_pct:5.1f}%)")
    print(f"⚠ Partial matches:   {partial_matches:2d} ({partial_pct:5.1f}%)")
    print(f"✗ Failures/Errors:   {failures:2d} ({failure_pct:5.1f}%)")
    print()

    # Performance rating
    print("=" * 80)
    if exact_pct >= 90:
        print("✅ EXCELLENT - Matcher is performing very well!")
    elif exact_pct >= 75:
        print("✓ GOOD - Matcher is performing adequately")
    elif exact_pct >= 60:
        print("⚠ FAIR - Matcher needs improvement")
    else:
        print("❌ POOR - Matcher needs significant work")
    print("=" * 80)

    # Detailed mismatch report
    if mismatches:
        print("\n\n" + "=" * 80)
        print("DETAILED MISMATCH REPORT")
        print("=" * 80)

        for i, mismatch in enumerate(mismatches, 1):
            print(f"\n{i}. {mismatch['test_id']}")
            print(f"   Input: \"{mismatch['input']}\"")

            if "error" in mismatch:
                print(f"   Error: {mismatch['error']}")
            else:
                print(f"   Expected: {json.dumps(mismatch['expected'], indent=2)}")
                print(f"   Actual: {json.dumps(mismatch['actual'], indent=2)}")


if __name__ == "__main__":
    run_evaluation()
