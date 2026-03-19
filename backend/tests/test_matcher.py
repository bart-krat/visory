#!/usr/bin/env python3
"""CLI test script for the constraint matcher.

Usage:
    python test_matcher.py "I need to go to the gym"
    python test_matcher.py "meeting at 2pm, then lunch"
    python test_matcher.py --tasks "Gym,Meeting,Lunch,Report" "gym before lunch"
    python test_matcher.py --interactive
"""
import argparse
import sys

from dotenv import load_dotenv
load_dotenv()

from app.state import Task
from app.constraints.matcher import ConstraintMatcher


# Default test tasks
DEFAULT_TASKS = [
    Task(name="Gym", category="health", utility=80, duration=60),
    Task(name="Run", category="health", utility=70, duration=30),
    Task(name="Meeting", category="work", utility=90, duration=60),
    Task(name="Report", category="work", utility=75, duration=45),
    Task(name="Lunch", category="personal", utility=60, duration=30),
    Task(name="Call mom", category="personal", utility=50, duration=20),
    Task(name="Read book", category="personal", utility=40, duration=60),
]


def parse_tasks(tasks_str: str) -> list[Task]:
    """Parse comma-separated task names into Task objects."""
    categories = ["health", "work", "personal"]
    tasks = []
    for i, name in enumerate(tasks_str.split(",")):
        name = name.strip()
        if name:
            tasks.append(Task(
                name=name,
                category=categories[i % 3],
                utility=80,
                duration=30,
            ))
    return tasks


def test_constraint(constraint_text: str, tasks: list[Task]) -> None:
    """Test a constraint and show the output."""
    print("\n" + "=" * 60)
    print(f"INPUT: \"{constraint_text}\"")
    print("=" * 60)

    print("\nAvailable tasks:")
    for t in tasks:
        print(f"  - {t.name} ({t.category})")

    print("\nMatching...")
    matcher = ConstraintMatcher(tasks)
    constraint_set = matcher.match(constraint_text)

    print("\n" + "-" * 40)
    print("RESULT:")
    print("-" * 40)

    if constraint_set.is_empty():
        print("  No constraints matched.")
    else:
        print(f"  Description: {constraint_set.describe()}")
        print(f"\n  Constraints ({len(constraint_set.constraints)}):")
        for c in constraint_set.constraints:
            print(f"    - {c}")

        print(f"\n  Mandatory tasks: {list(constraint_set.mandatory_tasks)}")
        print(f"  Mandatory categories: {list(constraint_set.mandatory_categories)}")
        print(f"  Fixed slots: {constraint_set.fixed_slots}")
        print(f"  Ordering constraints: {constraint_set.ordering_constraints}")

        print(f"\n  Raw dict:")
        for item in constraint_set.to_dict():
            print(f"    {item}")

    print()


def interactive_mode(tasks: list[Task]) -> None:
    """Run in interactive mode."""
    print("\nConstraint Matcher - Interactive Mode")
    print("=" * 40)
    print("Available tasks:")
    for t in tasks:
        print(f"  - {t.name} ({t.category})")
    print("\nType a constraint and press Enter.")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            text = input("Constraint> ").strip()
            if text.lower() in ["quit", "exit", "q"]:
                print("Bye!")
                break
            if not text:
                continue
            test_constraint(text, tasks)
        except KeyboardInterrupt:
            print("\nBye!")
            break
        except EOFError:
            break


def main():
    parser = argparse.ArgumentParser(
        description="Test the constraint matcher with custom inputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_matcher.py "I need to go to the gym"
  python test_matcher.py "meeting at 2pm"
  python test_matcher.py "gym before lunch"
  python test_matcher.py --tasks "Workout,Standup,Coffee,Email" "workout first thing"
  python test_matcher.py --interactive
        """,
    )
    parser.add_argument(
        "constraint",
        nargs="?",
        help="The constraint text to test",
    )
    parser.add_argument(
        "--tasks",
        "-t",
        help="Comma-separated list of task names (default: Gym,Run,Meeting,Report,Lunch,Call mom,Read book)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode",
    )

    args = parser.parse_args()

    # Parse tasks
    if args.tasks:
        tasks = parse_tasks(args.tasks)
    else:
        tasks = DEFAULT_TASKS

    if args.interactive:
        interactive_mode(tasks)
    elif args.constraint:
        test_constraint(args.constraint, tasks)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
