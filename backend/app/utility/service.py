"""Utility assessment module.

Asks users questions about their values and priorities,
then uses an LLM to derive utility weights for work, health, and personal.
"""
import json
from dataclasses import dataclass, field
from app.chat import get_chat_service
from app.utils import clean_json_response


QUESTIONS = [
    "What is the most important thing in your life right now?",
    "What are your current goals?",
    "What are your biggest challenges?",
    "Would you say you live to work or work to live?",
    "How would you rate your health?",
    "How often do you exercise?",
    "What do you want to change in your life?",
    "How do you like to spend your free time?",
    "Do you live under a lot of stress?",
    "What brings you the most joy?",
]


EVALUATION_PROMPT = """You are an expert psychologist and life coach analyzing a user's values questionnaire.

Based on the conversation below, evaluate how much the user values each life domain:
- **Work**: Career, professional growth, productivity, achievements, financial success
- **Health**: Physical fitness, mental wellbeing, exercise, nutrition, sleep, stress management
- **Personal**: Hobbies, relationships, fun, relaxation, entertainment, social activities, family time

## Scoring Rules
1. Assign weights to work, health, and personal
2. The three weights MUST sum to exactly 300
3. Each weight should be between 50 and 150 (reasonable bounds)
4. Higher weight = user values this domain more
5. Don't just count mentions - consider the depth, emotion, sentiment and emphasis in their answers

## Analysis Framework
For each question, consider:
- Q1 (Most important): Direct indicator of primary values
- Q2 (Goals): What they're striving for reveals priorities
- Q3 (Challenges): Where they struggle shows what matters
- Q4 (Live to work): Direct work-life balance indicator
- Q5 (Health rating): Self-awareness of health importance
- Q6 (Exercise): Behavioral indicator of health priority
- Q7 (Want to change): Reveals dissatisfaction and desires
- Q8 (Free time): How personal time is valued and spent
- Q9 (Stress): Impact of work/life on wellbeing
- Q10 (Joy): Core values and happiness sources

## Response Format
Respond with ONLY a JSON object (no markdown, no explanation):
{
    "work": <number>,
    "health": <number>,
    "personal": <number>,
    "reasoning": "<brief 1-2 sentence explanation>"
}

## Conversation to Analyze
"""


@dataclass
class UtilityWeights:
    """Utility weights for task categories."""
    work: float
    health: float
    personal: float
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "work": self.work,
            "health": self.health,
            "personal": self.personal,
            "reasoning": self.reasoning,
        }

    @classmethod
    def default(cls) -> "UtilityWeights":
        """Return default balanced weights."""
        return cls(work=100, health=100, personal=100, reasoning="Default balanced weights")


@dataclass
class UtilityQuestionnaire:
    """Manages the utility assessment questionnaire flow.

    Usage:
        questionnaire = UtilityQuestionnaire()

        # Get first question
        question = questionnaire.get_current_question()

        # Submit answer and get next question (or None if done)
        next_question = questionnaire.submit_answer("My answer...")

        # When done, evaluate
        if questionnaire.is_complete():
            weights = questionnaire.evaluate()
    """
    questions: list[str] = field(default_factory=lambda: QUESTIONS.copy())
    answers: list[str] = field(default_factory=list)
    current_index: int = 0
    weights: UtilityWeights | None = None

    def get_current_question(self) -> str | None:
        """Get the current question, or None if questionnaire is complete."""
        if self.current_index >= len(self.questions):
            return None
        return self.questions[self.current_index]

    def get_question_number(self) -> int:
        """Get current question number (1-indexed)."""
        return self.current_index + 1

    def get_total_questions(self) -> int:
        """Get total number of questions."""
        return len(self.questions)

    def submit_answer(self, answer: str) -> str | None:
        """Submit an answer and advance to the next question.

        Args:
            answer: The user's answer to the current question.

        Returns:
            The next question, or None if questionnaire is complete.
        """
        if self.current_index >= len(self.questions):
            return None

        self.answers.append(answer)
        self.current_index += 1

        return self.get_current_question()

    def is_complete(self) -> bool:
        """Check if all questions have been answered."""
        return len(self.answers) >= len(self.questions)

    def get_conversation(self) -> list[dict]:
        """Get the Q&A as a conversation format."""
        conversation = []
        for i, (q, a) in enumerate(zip(self.questions, self.answers)):
            conversation.append({
                "question_number": i + 1,
                "question": q,
                "answer": a,
            })
        return conversation

    def get_conversation_text(self) -> str:
        """Get the Q&A as formatted text for LLM."""
        lines = []
        for i, (q, a) in enumerate(zip(self.questions, self.answers)):
            lines.append(f"Q{i+1}: {q}")
            lines.append(f"A{i+1}: {a}")
            lines.append("")
        return "\n".join(lines)

    def evaluate(self) -> UtilityWeights:
        """Send the conversation to LLM and get utility weights.

        Returns:
            UtilityWeights with work, health, personal values summing to 300.
        """
        if not self.is_complete():
            raise ValueError("Questionnaire not complete. Answer all questions first.")

        chat_service = get_chat_service()

        # Build the evaluation prompt
        conversation_text = self.get_conversation_text()
        full_prompt = EVALUATION_PROMPT + conversation_text

        # Call LLM
        response = chat_service.simple_chat(
            user_message=full_prompt,
            system_prompt="You are a precise JSON response generator. Output only valid JSON.",
        )

        # Parse response
        self.weights = self._parse_weights(response)
        return self.weights

    def _parse_weights(self, response: str) -> UtilityWeights:
        """Parse the LLM response into UtilityWeights."""
        try:
            clean = clean_json_response(response)
            data = json.loads(clean)

            work = float(data.get("work", 100))
            health = float(data.get("health", 100))
            personal = float(data.get("personal", 100))
            reasoning = data.get("reasoning", "")

            # Validate sum
            total = work + health + personal
            if abs(total - 300) > 1:  # Allow small floating point errors
                # Normalize to 300
                factor = 300 / total
                work *= factor
                health *= factor
                personal *= factor

            # Ensure bounds
            work = max(50, min(150, work))
            health = max(50, min(150, health))
            personal = max(50, min(150, personal))

            # Re-normalize after bounding
            total = work + health + personal
            if abs(total - 300) > 1:
                factor = 300 / total
                work *= factor
                health *= factor
                personal *= factor

            return UtilityWeights(
                work=round(work, 1),
                health=round(health, 1),
                personal=round(personal, 1),
                reasoning=reasoning,
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response was: {response}")
            return UtilityWeights.default()

    def reset(self):
        """Reset the questionnaire to start over."""
        self.answers = []
        self.current_index = 0
        self.weights = None


class UtilityService:
    """Service for running the utility assessment.

    High-level interface for the questionnaire flow.
    """

    def __init__(self):
        self.questionnaire: UtilityQuestionnaire | None = None

    def start(self) -> str:
        """Start a new questionnaire and return the first question."""
        self.questionnaire = UtilityQuestionnaire()
        return self._format_question(self.questionnaire.get_current_question())

    def answer(self, response: str) -> tuple[str | None, bool]:
        """Submit an answer and get the next question.

        Args:
            response: User's answer to the current question.

        Returns:
            Tuple of (next_question_or_none, is_complete)
        """
        if not self.questionnaire:
            raise ValueError("Questionnaire not started. Call start() first.")

        next_q = self.questionnaire.submit_answer(response)

        if next_q:
            return self._format_question(next_q), False
        else:
            return None, True

    def evaluate(self) -> UtilityWeights:
        """Evaluate the completed questionnaire."""
        if not self.questionnaire:
            raise ValueError("Questionnaire not started.")
        return self.questionnaire.evaluate()

    def get_progress(self) -> tuple[int, int]:
        """Get current progress (current, total)."""
        if not self.questionnaire:
            return 0, len(QUESTIONS)
        return self.questionnaire.get_question_number(), self.questionnaire.get_total_questions()

    def _format_question(self, question: str) -> str:
        """Format a question with progress indicator."""
        current, total = self.get_progress()
        return f"Question {current}/{total}: {question}"


# Singleton instance
_utility_service: UtilityService | None = None


def get_utility_service() -> UtilityService:
    """Get or create the singleton UtilityService instance."""
    global _utility_service
    if _utility_service is None:
        _utility_service = UtilityService()
    return _utility_service
