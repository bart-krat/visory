"""Evaluation dataset for constraint matcher (matcher.py).

This dataset contains 20 natural language constraint inputs with expected
parsed constraint outputs. Edit the expected outputs to ensure accuracy.

Categories:
- Parseable constraints: Should be converted to typed constraints
- Ambiguous constraints: Should return UndefinedConstraint
"""

# Available tasks for context (matcher needs to know available tasks)
SAMPLE_TASKS = [
    {"name": "Gym", "category": "health"},
    {"name": "Run", "category": "health"},
    {"name": "Swim", "category": "health"},
    {"name": "Yoga", "category": "health"},
    {"name": "Workout", "category": "health"},
    {"name": "Meeting", "category": "work"},
    {"name": "Client call", "category": "work"},
    {"name": "Code review", "category": "work"},
    {"name": "Email", "category": "work"},
    {"name": "Report", "category": "work"},
    {"name": "Beach", "category": "personal"},
    {"name": "Lunch", "category": "personal"},
    {"name": "Dinner", "category": "personal"},
    {"name": "Movie", "category": "personal"},
    {"name": "Reading", "category": "personal"},
]

MATCHER_EVAL_DATA = [
    # ========================================================================
    # SIMPLE TASK INCLUSION
    # ========================================================================
    {
        "id": "simple_include_1",
        "user_input": "I need to go to the gym",
        "expected_output": [
            {"type": "must_include_task", "task_name": "Gym"}
        ],
        "difficulty": "easy"
    },

    {
        "id": "simple_include_2",
        "user_input": "must include meeting",
        "expected_output": [
            {"type": "must_include_task", "task_name": "Meeting"}
        ],
        "difficulty": "easy"
    },

    # ========================================================================
    # ORDERING CONSTRAINTS
    # ========================================================================
    {
        "id": "ordering_1",
        "user_input": "beach after run",
        "expected_output": [
            {"type": "ordered_after", "task_name": "Beach", "after_task": "Run"},
            {"type": "must_include_task", "task_name": "Beach"},
            {"type": "must_include_task", "task_name": "Run"}
        ],
        "difficulty": "medium"
    },

    {
        "id": "ordering_2",
        "user_input": "I want to swim before lunch",
        "expected_output": [
            {"type": "ordered_after", "task_name": "Lunch", "after_task": "Swim"},
            {"type": "must_include_task", "task_name": "Swim"},
            {"type": "must_include_task", "task_name": "Lunch"}
        ],
        "difficulty": "medium"
    },

    {
        "id": "ordering_3",
        "user_input": "yoga then meeting",
        "expected_output": [
            {"type": "ordered_after", "task_name": "Meeting", "after_task": "Yoga"},
            {"type": "must_include_task", "task_name": "Yoga"},
            {"type": "must_include_task", "task_name": "Meeting"}
        ],
        "difficulty": "medium"
    },

    # ========================================================================
    # FIXED TIME SLOTS
    # ========================================================================
    {
        "id": "fixed_time_1",
        "user_input": "meeting at 2pm",
        "expected_output": [
            {"type": "fixed_time_slot", "task_name": "Meeting", "start_time": 840}  # 14:00 = 840 minutes
        ],
        "difficulty": "medium"
    },

    {
        "id": "fixed_time_2",
        "user_input": "client call at 9:00 AM",
        "expected_output": [
            {"type": "fixed_time_slot", "task_name": "Client call", "start_time": 540}  # 09:00 = 540 minutes
        ],
        "difficulty": "medium"
    },

    {
        "id": "fixed_time_3",
        "user_input": "lunch at noon",
        "expected_output": [
            {"type": "fixed_time_slot", "task_name": "Lunch", "start_time": 720}  # 12:00 = 720 minutes
        ],
        "difficulty": "medium"
    },

    # ========================================================================
    # TIME RANGE CONSTRAINTS
    # ========================================================================
    {
        "id": "time_range_1",
        "user_input": "workout in the morning",
        "expected_output": [
            {"type": "time_range", "task_name": "Workout", "after_time": 360, "before_time": 720},  # 6am-12pm
            {"type": "must_include_task", "task_name": "Workout"}
        ],
        "difficulty": "medium"
    },

    {
        "id": "time_range_2",
        "user_input": "gym before noon",
        "expected_output": [
            {"type": "time_range", "task_name": "Gym", "after_time": None, "before_time": 720},  # before 12pm
            {"type": "must_include_task", "task_name": "Gym"}
        ],
        "difficulty": "medium"
    },

    {
        "id": "time_range_3",
        "user_input": "run in the afternoon",
        "expected_output": [
            {"type": "time_range", "task_name": "Run", "after_time": 720, "before_time": 1020},  # 12pm-5pm
            {"type": "must_include_task", "task_name": "Run"}
        ],
        "difficulty": "medium"
    },

    {
        "id": "time_range_4",
        "user_input": "email after 3pm",
        "expected_output": [
            {"type": "time_range", "task_name": "Email", "after_time": 900, "before_time": None},  # after 15:00
            {"type": "must_include_task", "task_name": "Email"}
        ],
        "difficulty": "medium"
    },

    # ========================================================================
    # CATEGORY CONSTRAINTS
    # ========================================================================
    {
        "id": "category_1",
        "user_input": "include a health task",
        "expected_output": [
            {"type": "must_include_category", "category": "health"}
        ],
        "difficulty": "easy"
    },

    {
        "id": "category_2",
        "user_input": "need something for work",
        "expected_output": [
            {"type": "must_include_category", "category": "work"}
        ],
        "difficulty": "easy"
    },

    # ========================================================================
    # COMPLEX COMBINATIONS
    # ========================================================================
    {
        "id": "complex_1",
        "user_input": "gym in the morning and meeting at 2pm",
        "expected_output": [
            {"type": "time_range", "task_name": "Gym", "after_time": 360, "before_time": 720},
            {"type": "must_include_task", "task_name": "Gym"},
            {"type": "fixed_time_slot", "task_name": "Meeting", "start_time": 840}
        ],
        "difficulty": "hard"
    },

    {
        "id": "complex_2",
        "user_input": "swim before lunch at noon",
        "expected_output": [
            {"type": "ordered_after", "task_name": "Lunch", "after_task": "Swim"},
            {"type": "must_include_task", "task_name": "Swim"},
            {"type": "fixed_time_slot", "task_name": "Lunch", "start_time": 720}
        ],
        "difficulty": "hard"
    },

    # ========================================================================
    # AMBIGUOUS/UNDEFINED CONSTRAINTS (should return UndefinedConstraint)
    # ========================================================================
    {
        "id": "ambiguous_1",
        "user_input": "spread everything out evenly",
        "expected_output": [
            {"type": "undefined", "description": "spread everything out evenly"}
        ],
        "difficulty": "easy"
    },

    {
        "id": "ambiguous_2",
        "user_input": "make the schedule fun and energizing",
        "expected_output": [
            {"type": "undefined", "description": "make the schedule fun and energizing"}
        ],
        "difficulty": "easy"
    },

    {
        "id": "ambiguous_3",
        "user_input": "prioritize when I have most energy",
        "expected_output": [
            {"type": "undefined", "description": "prioritize when I have most energy"}
        ],
        "difficulty": "easy"
    },

    {
        "id": "ambiguous_4",
        "user_input": "ease into the day gently",
        "expected_output": [
            {"type": "undefined", "description": "ease into the day gently"}
        ],
        "difficulty": "easy"
    },
]


def print_dataset_summary():
    """Print summary of matcher eval dataset."""
    print(f"Total test cases: {len(MATCHER_EVAL_DATA)}")
    print()

    # Count by difficulty
    difficulty_counts = {}
    for test in MATCHER_EVAL_DATA:
        diff = test.get("difficulty", "unknown")
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

    print("Difficulty distribution:")
    for diff, count in sorted(difficulty_counts.items()):
        print(f"  {diff}: {count}")
    print()

    # Count by constraint type
    constraint_types = {}
    for test in MATCHER_EVAL_DATA:
        for constraint in test["expected_output"]:
            ctype = constraint["type"]
            constraint_types[ctype] = constraint_types.get(ctype, 0) + 1

    print("Constraint type distribution:")
    for ctype, count in sorted(constraint_types.items()):
        print(f"  {ctype}: {count}")
    print()

    # List all test cases
    print("Test cases:")
    for i, test in enumerate(MATCHER_EVAL_DATA, 1):
        num_constraints = len(test["expected_output"])
        print(f"  {i:2d}. {test['id']:20s} - {num_constraints} constraints ({test['difficulty']})")
        print(f"      Input: \"{test['user_input']}\"")


if __name__ == "__main__":
    print("=" * 80)
    print("CONSTRAINT MATCHER EVALUATION DATASET")
    print("=" * 80)
    print()
    print_dataset_summary()
    print()
    print("Edit the 'expected_output' arrays in this file to ensure accuracy.")
    print()

    # Show first example in detail
    print("=" * 80)
    print("EXAMPLE TEST CASE:")
    print("=" * 80)
    example = MATCHER_EVAL_DATA[0]
    print(f"ID: {example['id']}")
    print(f"Input: \"{example['user_input']}\"")
    print(f"Expected output:")
    for constraint in example["expected_output"]:
        print(f"  {constraint}")
