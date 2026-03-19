"""Evaluation dataset for optimizer testing.

This dataset contains 10 test cases with varying complexity levels.
Each test case includes tasks, time window, constraints, and validation criteria.
"""

# Test case structure matches the state format
OPTIMIZER_EVAL_DATA = [
    # ========================================================================
    # TEST 1: Simple - All tasks fit perfectly
    # ========================================================================
    {
        "id": "simple_all_fit",
        "description": "3 short tasks, plenty of time, no constraints",
        "tasks": [
            {"name": "Morning jog", "category": "health", "utility": 80, "duration": 30, "time_slot": None},
            {"name": "Team meeting", "category": "work", "utility": 100, "duration": 60, "time_slot": None},
            {"name": "Lunch", "category": "personal", "utility": 50, "duration": 45, "time_slot": None},
        ],
        "time_window": {"start_time": "09:00", "end_time": "17:00"},
        "constraints": [],
        "expected_characteristics": {
            "all_tasks_included": True,
            "respects_category_order": True,  # Health -> Work -> Personal
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "easy"
    },

    # ========================================================================
    # TEST 2: Task overflow - Need selection
    # ========================================================================
    {
        "id": "overflow_selection",
        "description": "5 tasks but only 2 hours available - must select subset",
        "tasks": [
            {"name": "Quick workout", "category": "health", "utility": 70, "duration": 30, "time_slot": None},
            {"name": "Code review", "category": "work", "utility": 100, "duration": 45, "time_slot": None},
            {"name": "Lunch break", "category": "personal", "utility": 60, "duration": 30, "time_slot": None},
            {"name": "Email cleanup", "category": "work", "utility": 40, "duration": 30, "time_slot": None},
            {"name": "Walk", "category": "health", "utility": 50, "duration": 20, "time_slot": None},
        ],
        "time_window": {"start_time": "14:00", "end_time": "16:00"},
        "constraints": [],
        "expected_characteristics": {
            "all_tasks_included": False,
            "high_utility_included": True,  # Should prioritize utility
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "medium"
    },

    # ========================================================================
    # TEST 3: Mandatory task constraint
    # ========================================================================
    {
        "id": "mandatory_task",
        "description": "4 tasks, tight window, must include 'Client call'",
        "tasks": [
            {"name": "Gym session", "category": "health", "utility": 80, "duration": 60, "time_slot": None},
            {"name": "Client call", "category": "work", "utility": 90, "duration": 30, "time_slot": None},
            {"name": "Lunch", "category": "personal", "utility": 60, "duration": 45, "time_slot": None},
            {"name": "Documentation", "category": "work", "utility": 70, "duration": 60, "time_slot": None},
        ],
        "time_window": {"start_time": "10:00", "end_time": "13:00"},
        "constraints": [
            {"type": "must_include_task", "task_name": "Client call"}
        ],
        "expected_characteristics": {
            "all_tasks_included": False,
            "client_call_included": True,
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "medium"
    },

    # ========================================================================
    # TEST 4: Mandatory category constraint
    # ========================================================================
    {
        "id": "mandatory_category",
        "description": "5 tasks, must include at least one health task",
        "tasks": [
            {"name": "Stand-up meeting", "category": "work", "utility": 90, "duration": 15, "time_slot": None},
            {"name": "Deep work", "category": "work", "utility": 100, "duration": 90, "time_slot": None},
            {"name": "Yoga", "category": "health", "utility": 60, "duration": 45, "time_slot": None},
            {"name": "Lunch", "category": "personal", "utility": 50, "duration": 30, "time_slot": None},
            {"name": "Email", "category": "work", "utility": 70, "duration": 30, "time_slot": None},
        ],
        "time_window": {"start_time": "09:00", "end_time": "13:00"},
        "constraints": [
            {"type": "must_include_category", "category": "health"}
        ],
        "expected_characteristics": {
            "all_tasks_included": False,
            "health_task_included": True,
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "medium"
    },

    # ========================================================================
    # TEST 5: Fixed time slot
    # ========================================================================
    {
        "id": "fixed_time",
        "description": "3 tasks, 'Meeting' must be at 2:00 PM",
        "tasks": [
            {"name": "Morning workout", "category": "health", "utility": 70, "duration": 45, "time_slot": None},
            {"name": "Important meeting", "category": "work", "utility": 100, "duration": 60, "time_slot": None},
            {"name": "Lunch", "category": "personal", "utility": 60, "duration": 45, "time_slot": None},
        ],
        "time_window": {"start_time": "09:00", "end_time": "17:00"},
        "constraints": [
            {"type": "fixed_time_slot", "task_name": "Important meeting", "start_time": 840}  # 2:00 PM = 840 minutes
        ],
        "expected_characteristics": {
            "all_tasks_included": True,
            "meeting_at_2pm": True,
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "medium"
    },

    # ========================================================================
    # TEST 6: Ordering constraint
    # ========================================================================
    {
        "id": "ordering",
        "description": "3 tasks, 'Beach' must come after 'Run'",
        "tasks": [
            {"name": "Run", "category": "health", "utility": 80, "duration": 30, "time_slot": None},
            {"name": "Beach", "category": "personal", "utility": 70, "duration": 60, "time_slot": None},
            {"name": "Work session", "category": "work", "utility": 90, "duration": 90, "time_slot": None},
        ],
        "time_window": {"start_time": "08:00", "end_time": "14:00"},
        "constraints": [
            {"type": "ordered_after", "task_name": "Beach", "after_task": "Run"},
            {"type": "must_include_task", "task_name": "Beach"},
            {"type": "must_include_task", "task_name": "Run"}
        ],
        "expected_characteristics": {
            "all_tasks_included": True,
            "beach_after_run": True,
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "hard"
    },

    # ========================================================================
    # TEST 7: Time range constraint
    # ========================================================================
    {
        "id": "time_range",
        "description": "4 tasks, 'Workout' must be in morning (before 12pm)",
        "tasks": [
            {"name": "Workout", "category": "health", "utility": 85, "duration": 45, "time_slot": None},
            {"name": "Meetings", "category": "work", "utility": 100, "duration": 90, "time_slot": None},
            {"name": "Lunch", "category": "personal", "utility": 60, "duration": 45, "time_slot": None},
            {"name": "Code review", "category": "work", "utility": 80, "duration": 60, "time_slot": None},
        ],
        "time_window": {"start_time": "08:00", "end_time": "17:00"},
        "constraints": [
            {"type": "time_range", "task_name": "Workout", "after_time": None, "before_time": 720},  # before 12:00 PM
            {"type": "must_include_task", "task_name": "Workout"}
        ],
        "expected_characteristics": {
            "all_tasks_included": False,
            "workout_before_noon": True,
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "hard"
    },

    # ========================================================================
    # TEST 8: Multiple complex constraints
    # ========================================================================
    {
        "id": "complex_multi",
        "description": "5 tasks with fixed time + ordering + mandatory constraints",
        "tasks": [
            {"name": "Stand-up", "category": "work", "utility": 90, "duration": 15, "time_slot": None},
            {"name": "Gym", "category": "health", "utility": 80, "duration": 60, "time_slot": None},
            {"name": "Lunch", "category": "personal", "utility": 70, "duration": 45, "time_slot": None},
            {"name": "Client meeting", "category": "work", "utility": 100, "duration": 60, "time_slot": None},
            {"name": "Email", "category": "work", "utility": 50, "duration": 30, "time_slot": None},
        ],
        "time_window": {"start_time": "09:00", "end_time": "17:00"},
        "constraints": [
            {"type": "fixed_time_slot", "task_name": "Stand-up", "start_time": 540},  # 9:00 AM
            {"type": "ordered_after", "task_name": "Lunch", "after_task": "Gym"},
            {"type": "must_include_task", "task_name": "Client meeting"},
            {"type": "must_include_task", "task_name": "Gym"},
            {"type": "must_include_task", "task_name": "Lunch"}
        ],
        "expected_characteristics": {
            "all_tasks_included": False,
            "standup_at_9am": True,
            "lunch_after_gym": True,
            "client_meeting_included": True,
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "very_hard"
    },

    # ========================================================================
    # TEST 9: Undefined/Ambiguous constraint (LLM optimizer)
    # ========================================================================
    {
        "id": "undefined_ambiguous",
        "description": "3 tasks with ambiguous constraint 'spread them out'",
        "tasks": [
            {"name": "Morning run", "category": "health", "utility": 75, "duration": 30, "time_slot": None},
            {"name": "Work block", "category": "work", "utility": 90, "duration": 90, "time_slot": None},
            {"name": "Evening walk", "category": "health", "utility": 60, "duration": 30, "time_slot": None},
        ],
        "time_window": {"start_time": "07:00", "end_time": "19:00"},
        "constraints": [
            {"type": "undefined", "description": "spread all activities evenly throughout the day"}
        ],
        "expected_characteristics": {
            "all_tasks_included": True,
            "good_spacing": True,  # Should have gaps between tasks
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "hard"
    },

    # ========================================================================
    # TEST 10: High complexity - Many tasks, tight constraints
    # ========================================================================
    {
        "id": "high_complexity",
        "description": "8 tasks, short window, multiple constraint types",
        "tasks": [
            {"name": "Morning yoga", "category": "health", "utility": 70, "duration": 30, "time_slot": None},
            {"name": "Breakfast", "category": "personal", "utility": 60, "duration": 20, "time_slot": None},
            {"name": "Stand-up", "category": "work", "utility": 85, "duration": 15, "time_slot": None},
            {"name": "Deep work", "category": "work", "utility": 100, "duration": 120, "time_slot": None},
            {"name": "Lunch", "category": "personal", "utility": 70, "duration": 45, "time_slot": None},
            {"name": "Client call", "category": "work", "utility": 95, "duration": 60, "time_slot": None},
            {"name": "Email", "category": "work", "utility": 50, "duration": 30, "time_slot": None},
            {"name": "Walk", "category": "health", "utility": 55, "duration": 20, "time_slot": None},
        ],
        "time_window": {"start_time": "08:00", "end_time": "17:00"},
        "constraints": [
            {"type": "time_range", "task_name": "Morning yoga", "after_time": None, "before_time": 600},  # before 10am
            {"type": "fixed_time_slot", "task_name": "Stand-up", "start_time": 540},  # 9:00 AM
            {"type": "ordered_after", "task_name": "Breakfast", "after_task": "Morning yoga"},
            {"type": "must_include_task", "task_name": "Client call"},
            {"type": "must_include_task", "task_name": "Deep work"},
            {"type": "must_include_task", "task_name": "Morning yoga"},
            {"type": "must_include_task", "task_name": "Breakfast"}
        ],
        "expected_characteristics": {
            "all_tasks_included": False,
            "yoga_before_10am": True,
            "breakfast_after_yoga": True,
            "standup_at_9am": True,
            "high_priority_included": True,
            "fits_in_window": True,
            "no_overlaps": True,
        },
        "difficulty": "very_hard"
    },
]


def print_dataset_summary():
    """Print summary of eval dataset."""
    print(f"Total test cases: {len(OPTIMIZER_EVAL_DATA)}")
    print()

    difficulty_counts = {}
    for test in OPTIMIZER_EVAL_DATA:
        diff = test.get("difficulty", "unknown")
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

    print("Difficulty distribution:")
    for diff, count in sorted(difficulty_counts.items()):
        print(f"  {diff}: {count}")
    print()

    print("Test cases:")
    for i, test in enumerate(OPTIMIZER_EVAL_DATA, 1):
        num_tasks = len(test["tasks"])
        num_constraints = len(test["constraints"])
        print(f"  {i:2d}. {test['id']:25s} - {num_tasks} tasks, {num_constraints} constraints ({test['difficulty']})")


if __name__ == "__main__":
    print("=" * 70)
    print("OPTIMIZER EVALUATION DATASET")
    print("=" * 70)
    print()
    print_dataset_summary()
