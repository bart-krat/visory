"""Run categorizer evaluation and report accuracy.

This script tests the task categorizer against the ground truth dataset
and reports accuracy, confusion matrix, and misclassified examples.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (OPENAI_API_KEY, etc.)
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from categorizer_eval_data import CATEGORIZER_EVAL_DATA
from app.categorize.service import CategorizeService
from collections import defaultdict


def run_evaluation():
    """Run categorizer on eval dataset and compute metrics."""
    print("=" * 70)
    print("CATEGORIZER EVALUATION")
    print("=" * 70)
    print()

    # Initialize categorizer
    categorizer = CategorizeService()

    # Extract task names
    task_names = [item["task"] for item in CATEGORIZER_EVAL_DATA]

    # Run categorization
    print(f"Categorizing {len(task_names)} tasks...")
    try:
        results = categorizer.categorize(task_names)
    except Exception as e:
        print(f"❌ Error during categorization: {e}")
        return

    # Build prediction map
    predictions = {task.name: task.category for task in results}

    # Compute metrics
    correct = 0
    total = len(CATEGORIZER_EVAL_DATA)
    misclassifications = []
    confusion_matrix = defaultdict(lambda: defaultdict(int))

    for item in CATEGORIZER_EVAL_DATA:
        task_name = item["task"]
        expected = item["expected_category"]
        predicted = predictions.get(task_name, "UNKNOWN")

        confusion_matrix[expected][predicted] += 1

        if predicted == expected:
            correct += 1
        else:
            misclassifications.append({
                "task": task_name,
                "expected": expected,
                "predicted": predicted,
            })

    accuracy = (correct / total) * 100

    # Print results
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    print(f"✓ Correct:   {correct}/{total}")
    print(f"✗ Incorrect: {len(misclassifications)}/{total}")
    print(f"📊 Accuracy:  {accuracy:.1f}%")
    print()

    # Print confusion matrix
    print("=" * 70)
    print("CONFUSION MATRIX")
    print("=" * 70)
    print()
    categories = ["work", "health", "personal"]

    # Header
    print(f"{'Actual \\ Predicted':20s}", end="")
    for cat in categories:
        print(f"{cat:>12s}", end="")
    print()
    print("-" * 56)

    # Rows
    for actual in categories:
        print(f"{actual:20s}", end="")
        for predicted in categories:
            count = confusion_matrix[actual][predicted]
            print(f"{count:>12d}", end="")
        print()
    print()

    # Per-category accuracy
    print("=" * 70)
    print("PER-CATEGORY ACCURACY")
    print("=" * 70)
    print()
    for category in categories:
        total_in_category = sum(confusion_matrix[category].values())
        if total_in_category > 0:
            correct_in_category = confusion_matrix[category][category]
            cat_accuracy = (correct_in_category / total_in_category) * 100
            print(f"{category:10s}: {correct_in_category}/{total_in_category} ({cat_accuracy:.1f}%)")
    print()

    # Print misclassifications
    if misclassifications:
        print("=" * 70)
        print("MISCLASSIFICATIONS")
        print("=" * 70)
        print()
        for i, item in enumerate(misclassifications, 1):
            print(f"{i}. \"{item['task']}\"")
            print(f"   Expected: {item['expected']}")
            print(f"   Predicted: {item['predicted']}")
            print()
    else:
        print("🎉 No misclassifications! Perfect accuracy!")
        print()

    # Summary
    print("=" * 70)
    if accuracy >= 95:
        print("✅ EXCELLENT - Categorizer is performing very well!")
    elif accuracy >= 85:
        print("✓ GOOD - Categorizer is performing adequately")
    elif accuracy >= 70:
        print("⚠ FAIR - Categorizer needs improvement")
    else:
        print("❌ POOR - Categorizer needs significant improvement")
    print("=" * 70)


if __name__ == "__main__":
    run_evaluation()
