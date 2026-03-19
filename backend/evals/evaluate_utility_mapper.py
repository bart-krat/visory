"""Evaluation script for utility questionnaire.

Tests the psychometric evaluation against 3 distinct answer sets:
- Health-Focused: Should return highest weight for health
- Career-Focused: Should return highest weight for work
- Personal-Focused: Should return highest weight for personal
"""
import csv
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utility.service import UtilityQuestionnaire


def load_test_data(csv_path: str) -> dict[str, list[str]]:
    """Load test data from CSV.

    Returns:
        Dict with keys: 'Health-Focused', 'Career-Focused', 'Personal-Focused'
        Each value is a list of 10 answers.
    """
    answer_sets = {
        "Health-Focused": [],
        "Career-Focused": [],
        "Personal-Focused": [],
    }

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            answer_sets["Health-Focused"].append(row["Health-Focused"])
            answer_sets["Career-Focused"].append(row["Career-Focused"])
            answer_sets["Personal-Focused"].append(row["Personal-Focused"])

    return answer_sets


def run_evaluation(name: str, answers: list[str], expected_highest: str) -> dict:
    """Run questionnaire with given answers and evaluate.

    Args:
        name: Name of the answer set (e.g., "Health-Focused")
        answers: List of 10 answers
        expected_highest: Expected category with highest weight ("health", "work", or "personal")

    Returns:
        Dict with results including pass/fail status
    """
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Expected highest weight: {expected_highest}")
    print('='*60)

    # Create questionnaire and submit all answers
    questionnaire = UtilityQuestionnaire()

    for i, answer in enumerate(answers):
        question = questionnaire.get_current_question()
        print(f"\nQ{i+1}: {question}")
        print(f"A{i+1}: {answer}")
        questionnaire.submit_answer(answer)

    # Evaluate
    print("\n" + "-"*60)
    print("Evaluating with LLM...")
    weights = questionnaire.evaluate()

    # Display results
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    print(f"Work:     {weights.work:.1f}/300")
    print(f"Health:   {weights.health:.1f}/300")
    print(f"Personal: {weights.personal:.1f}/300")
    print(f"\nReasoning: {weights.reasoning}")

    # Determine which category has highest weight
    weights_dict = {
        "work": weights.work,
        "health": weights.health,
        "personal": weights.personal,
    }
    actual_highest = max(weights_dict, key=weights_dict.get)

    # Check if test passed
    passed = actual_highest == expected_highest

    print("\n" + "-"*60)
    if passed:
        print(f"✅ PASS: Highest weight is {actual_highest} (expected {expected_highest})")
    else:
        print(f"❌ FAIL: Highest weight is {actual_highest} (expected {expected_highest})")
    print("-"*60)

    return {
        "name": name,
        "expected": expected_highest,
        "actual": actual_highest,
        "passed": passed,
        "weights": {
            "work": weights.work,
            "health": weights.health,
            "personal": weights.personal,
        },
        "reasoning": weights.reasoning,
    }


def main():
    """Run all evaluations and report results."""
    csv_path = Path(__file__).parent / "questionnaire_test_data.csv"

    if not csv_path.exists():
        print(f"❌ Error: CSV file not found at {csv_path}")
        return

    print("Loading test data...")
    answer_sets = load_test_data(csv_path)

    # Run evaluations
    results = []

    # Test 1: Health-Focused
    results.append(run_evaluation(
        "Health-Focused",
        answer_sets["Health-Focused"],
        expected_highest="health"
    ))

    # Test 2: Career-Focused
    results.append(run_evaluation(
        "Career-Focused",
        answer_sets["Career-Focused"],
        expected_highest="work"
    ))

    # Test 3: Personal-Focused
    results.append(run_evaluation(
        "Personal-Focused",
        answer_sets["Personal-Focused"],
        expected_highest="personal"
    ))

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status} - {result['name']}: Expected {result['expected']}, Got {result['actual']}")
        print(f"        Weights: Work={result['weights']['work']:.1f}, "
              f"Health={result['weights']['health']:.1f}, "
              f"Personal={result['weights']['personal']:.1f}")

    print("\n" + "-"*60)
    print(f"Tests Passed: {passed_count}/{total_count}")
    print("-"*60)

    if passed_count == total_count:
        print("\n🎉 All tests passed! The utility questionnaire is working correctly.")
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed. Review the LLM evaluation logic.")


if __name__ == "__main__":
    main()
