"""Evaluation dataset for the task categorizer.

This dataset contains 20 diverse activities with ground truth labels.
Edit the labels as needed to ensure accuracy.

Categories:
- work: professional tasks, meetings, emails, reports, deadlines, projects, upskilling
- health: exercise, medical appointments, wellness, sleep, nutrition
- personal: hobbies, entertainment, socializing, relaxation, personal fun, family time
"""

CATEGORIZER_EVAL_DATA = [
    {"task": "team standup meeting", "expected_category": "work"},
    {"task": "go for a run", "expected_category": "health"},
    {"task": "watch Netflix", "expected_category": "personal"},
    {"task": "finish quarterly report", "expected_category": "work"},
    {"task": "yoga class", "expected_category": "health"},
    {"task": "call mom", "expected_category": "personal"},
    {"task": "review pull requests", "expected_category": "work"},
    {"task": "meal prep for the week", "expected_category": "health"},
    {"task": "play video games", "expected_category": "personal"},
    {"task": "client presentation", "expected_category": "work"},
    {"task": "doctor's appointment", "expected_category": "health"},
    {"task": "dinner with friends", "expected_category": "personal"},
    {"task": "respond to emails", "expected_category": "work"},
    {"task": "meditation", "expected_category": "health"},
    {"task": "read a book", "expected_category": "personal"},
    {"task": "attend workshop on leadership", "expected_category": "work"},
    {"task": "prepare healthy lunch", "expected_category": "health"},
    {"task": "organize closet", "expected_category": "personal"},
    {"task": "code review for project", "expected_category": "work"},
    {"task": "evening walk", "expected_category": "health"},
]

# Summary statistics
def print_statistics():
    """Print dataset statistics."""
    from collections import Counter

    categories = [item["expected_category"] for item in CATEGORIZER_EVAL_DATA]
    counts = Counter(categories)

    print(f"Total activities: {len(CATEGORIZER_EVAL_DATA)}")
    print(f"\nCategory distribution:")
    for category, count in sorted(counts.items()):
        percentage = (count / len(CATEGORIZER_EVAL_DATA)) * 100
        print(f"  {category}: {count} ({percentage:.1f}%)")


if __name__ == "__main__":
    print("Categorizer Evaluation Dataset")
    print("=" * 50)
    print()

    # Display all tasks
    for i, item in enumerate(CATEGORIZER_EVAL_DATA, 1):
        print(f"{i:2d}. {item['task']:40s} → {item['expected_category']}")

    print()
    print("=" * 50)
    print_statistics()
    print()
    print("Edit the 'expected_category' values in this file to correct any labels.")
