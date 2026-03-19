#!/usr/bin/env python3
"""CLI script to run the utility questionnaire standalone.

Usage:
    python run_utility.py
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from app.utility import UtilityService


def main():
    print("=" * 60)
    print("VISORY - Values Assessment Questionnaire")
    print("=" * 60)
    print()
    print("This questionnaire helps understand your priorities")
    print("to better optimize your daily schedule.")
    print()
    print("Answer each question honestly. Type your response and press Enter.")
    print("-" * 60)
    print()

    service = UtilityService()

    # Start questionnaire
    question = service.start()
    print(question)

    # Loop through questions
    while True:
        try:
            answer = input("\nYour answer: ").strip()

            if not answer:
                print("Please provide an answer.")
                continue

            next_question, is_complete = service.answer(answer)

            if is_complete:
                break

            print()
            print(next_question)

        except KeyboardInterrupt:
            print("\n\nQuestionnaire cancelled.")
            return

    # Evaluate
    print()
    print("-" * 60)
    print("Analyzing your responses...")
    print()

    try:
        weights = service.evaluate()

        print("=" * 60)
        print("YOUR UTILITY WEIGHTS")
        print("=" * 60)
        print()
        print(f"  Work:    {weights.work:.1f}")
        print(f"  Health:  {weights.health:.1f}")
        print(f"  Personal: {weights.personal:.1f}")
        print(f"  -----------------")
        print(f"  Total:   {weights.work + weights.health + weights.personal:.1f}")
        print()
        print(f"Analysis: {weights.reasoning}")
        print()
        print("=" * 60)

    except Exception as e:
        print(f"Error during evaluation: {e}")
        return


if __name__ == "__main__":
    main()
