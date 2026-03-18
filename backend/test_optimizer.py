#!/usr/bin/env python3
"""Test script for the enumeration optimizer with ordering constraints."""

from dotenv import load_dotenv
load_dotenv()

from app.state import Task, TimeWindow, ConstraintSet, MustIncludeTask, OrderedAfter, FixedTimeSlot
from app.optimize.enumeration_optimizer import EnumerationOptimizer


def test_meet_boss_before_gym():
    """Test: 'meet boss before i go to the gym' with gym fixed at 10:00"""

    print("=" * 60)
    print("TEST: meet boss before gym (gym fixed at 10:00)")
    print("=" * 60)

    # Tasks from the user's scenario
    tasks = [
        Task(name="gym", category="health", utility=80, duration=30),
        Task(name="run", category="health", utility=70, duration=30),
        Task(name="meet boss", category="work", utility=90, duration=30),
        Task(name="finish report", category="work", utility=75, duration=30),
        Task(name="beach", category="personal", utility=60, duration=30),
        Task(name="read book", category="personal", utility=40, duration=30),
    ]

    time_window = TimeWindow(start_time="09:00", end_time="17:00")

    # Constraints from "meet boss before i go to the gym"
    # This creates:
    #   - OrderedAfter: gym after meet boss → ordering_constraints = [("meet boss", "gym")]
    #   - MustIncludeTask: meet boss
    #   - MustIncludeTask: gym
    #   - FixedTimeSlot: gym at 10:00 (600 minutes)

    constraint_set = ConstraintSet()
    constraint_set.add(OrderedAfter(task_name="gym", after_task="meet boss"))
    constraint_set.add(MustIncludeTask(task_name="meet boss"))
    constraint_set.add(MustIncludeTask(task_name="gym"))
    constraint_set.add(FixedTimeSlot(task_name="gym", start_time=600))  # 10:00 AM

    print("\nTasks:")
    for t in tasks:
        print(f"  - {t.name} ({t.category}): utility={t.utility}, duration={t.duration}min")

    print(f"\nTime window: {time_window.start_time} - {time_window.end_time}")

    print("\nConstraints:")
    print(f"  - {constraint_set.describe()}")
    print(f"  - Mandatory tasks: {constraint_set.mandatory_tasks}")
    print(f"  - Fixed slots: {constraint_set.fixed_slots}")
    print(f"  - Ordering: {constraint_set.ordering_constraints}")

    # Run optimizer
    optimizer = EnumerationOptimizer()

    print("\nRunning optimizer...")
    result = optimizer.optimize(
        tasks=tasks,
        time_window=time_window,
        mandatory_tasks=constraint_set.mandatory_tasks,
        mandatory_categories=constraint_set.mandatory_categories,
        fixed_slots=constraint_set.fixed_slots,
        ordering_constraints=constraint_set.ordering_constraints,
    )

    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)

    if not result.schedule:
        print("  No valid schedule found!")
    else:
        print(f"\nSchedule ({len(result.schedule)} tasks):\n")
        total_utility = 0
        for item in result.schedule:
            # Find the task to get utility
            task_utility = next((t.utility for t in tasks if t.name == item.task), 0)
            total_utility += task_utility
            emoji = {"health": "💪", "work": "💼", "personal": "🎮"}.get(item.category, "📌")
            print(f"  {emoji} {item.start_time} - {item.end_time}: {item.task} ({item.duration_minutes}min, utility={task_utility})")

        print(f"\nTotal utility: {total_utility}")

        # Verify constraints
        print("\n" + "-" * 40)
        print("CONSTRAINT VERIFICATION:")
        print("-" * 40)

        # Check gym is at 10:00
        gym_task = next((t for t in result.schedule if t.task == "gym"), None)
        if gym_task:
            print(f"  ✓ gym at {gym_task.start_time} (expected: 10:00)")
            assert gym_task.start_time == "10:00", f"gym should be at 10:00, got {gym_task.start_time}"

        # Check meet boss is included
        meet_boss_task = next((t for t in result.schedule if t.task == "meet boss"), None)
        if meet_boss_task:
            print(f"  ✓ meet boss included at {meet_boss_task.start_time}")
        else:
            print("  ✗ meet boss NOT included!")

        # Check ordering: meet boss before gym
        if gym_task and meet_boss_task:
            gym_start = int(gym_task.start_time.split(":")[0]) * 60 + int(gym_task.start_time.split(":")[1])
            boss_start = int(meet_boss_task.start_time.split(":")[0]) * 60 + int(meet_boss_task.start_time.split(":")[1])

            if boss_start < gym_start:
                print(f"  ✓ meet boss ({meet_boss_task.start_time}) is BEFORE gym ({gym_task.start_time})")
            else:
                print(f"  ✗ ORDERING VIOLATED: meet boss ({meet_boss_task.start_time}) is AFTER gym ({gym_task.start_time})")


def test_no_valid_schedule():
    """Test case where ordering constraint can't be satisfied with fixed slot."""

    print("\n" + "=" * 60)
    print("TEST: Impossible constraint (gym at 09:00, meet boss before gym)")
    print("=" * 60)

    tasks = [
        Task(name="gym", category="health", utility=80, duration=30),
        Task(name="meet boss", category="work", utility=90, duration=30),
    ]

    # Window starts at 09:00, gym fixed at 09:00
    # meet boss must be before gym, but there's no time before 09:00!
    time_window = TimeWindow(start_time="09:00", end_time="17:00")

    constraint_set = ConstraintSet()
    constraint_set.add(OrderedAfter(task_name="gym", after_task="meet boss"))
    constraint_set.add(MustIncludeTask(task_name="meet boss"))
    constraint_set.add(MustIncludeTask(task_name="gym"))
    constraint_set.add(FixedTimeSlot(task_name="gym", start_time=540))  # 09:00 AM - start of window!

    print(f"\nConstraints: {constraint_set.describe()}")
    print("This should be IMPOSSIBLE - no time before 09:00 for meet boss")

    optimizer = EnumerationOptimizer()
    result = optimizer.optimize(
        tasks=tasks,
        time_window=time_window,
        mandatory_tasks=constraint_set.mandatory_tasks,
        fixed_slots=constraint_set.fixed_slots,
        ordering_constraints=constraint_set.ordering_constraints,
    )

    if not result.schedule:
        print("\n  ✓ Correctly returned empty schedule (constraint impossible)")
    else:
        print("\n  ✗ ERROR: Should have returned empty schedule!")
        for item in result.schedule:
            print(f"    {item.start_time}: {item.task}")


if __name__ == "__main__":
    test_meet_boss_before_gym()
    test_no_valid_schedule()
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
