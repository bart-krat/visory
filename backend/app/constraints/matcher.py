"""LLM-based semantic matching for custom constraints.

Uses the LLM to parse natural language constraint descriptions into typed
ConstraintSet objects that optimizers can understand.
"""
import json
import re

from app.state import (
    Task,
    ConstraintSet,
    MustIncludeTask,
    MustIncludeCategory,
    FixedTimeSlot,
    OrderedAfter,
)
from app.chat import get_chat_service


CONSTRAINT_MATCHING_PROMPT = '''You are a constraint parser for a daily planning app.

## Available Tasks
{tasks_list}

## Available Categories
{categories_list}

## Available Constraint Types

1. **MustIncludeTask** - A specific task must be in the schedule
   Format: {{"type": "must_include_task", "task_name": "<exact task name>"}}

2. **MustIncludeCategory** - At least one task from a category must be included
   Format: {{"type": "must_include_category", "category": "<health|work|personal>"}}

3. **FixedTimeSlot** - A task must be scheduled at a specific time
   Format: {{"type": "fixed_time_slot", "task_name": "<exact task name>", "start_time": <minutes from midnight>}}
   (e.g., 9:00 AM = 540, 2:00 PM = 840, 5:30 PM = 1050)

4. **OrderedAfter** - A task must come after another task
   Format: {{"type": "ordered_after", "task_name": "<task that comes second>", "after_task": "<task that comes first>"}}

## Examples

User: "I need to go to the gym"
Tasks available: ["Gym", "Meeting", "Lunch"]
Output: [{{"type": "must_include_task", "task_name": "Gym"}}]

User: "beach after run"
Tasks available: ["Run", "Beach", "Work"]
Output: [{{"type": "ordered_after", "task_name": "Beach", "after_task": "Run"}}, {{"type": "must_include_task", "task_name": "Beach"}}, {{"type": "must_include_task", "task_name": "Run"}}]

User: "meeting at 2pm"
Tasks available: ["Meeting", "Gym", "Lunch"]
Output: [{{"type": "fixed_time_slot", "task_name": "Meeting", "start_time": 840}}]

User: "I want to do something healthy"
Tasks available: ["Work task", "Report"]
Categories: health, work, personal
Output: [{{"type": "must_include_category", "category": "health"}}]

User: "first gym then lunch, and meeting at 3pm"
Tasks available: ["Gym", "Lunch", "Meeting"]
Output: [{{"type": "ordered_after", "task_name": "Lunch", "after_task": "Gym"}}, {{"type": "must_include_task", "task_name": "Gym"}}, {{"type": "must_include_task", "task_name": "Lunch"}}, {{"type": "fixed_time_slot", "task_name": "Meeting", "start_time": 900}}]

User: "no constraints" or "none" or "just optimize"
Output: []

## Instructions

Parse the user's constraint request and output a JSON array of constraints.
- Use EXACT task names from the available tasks list
- Only reference tasks that exist in the available tasks
- If a task name doesn't match exactly, find the closest match
- If the user mentions a generic category (health, work, personal) without specific tasks, use MustIncludeCategory
- When using OrderedAfter, also include MustIncludeTask for both tasks to ensure they're selected
- Output ONLY the JSON array, no explanation

## User Request
"{user_input}"

## Output (JSON array only)
'''


class ConstraintMatcher:
    """LLM-based constraint matcher.

    Uses the chat service to parse natural language into typed constraints.
    """

    def __init__(self, tasks: list[Task]):
        """Initialize with available tasks."""
        self.tasks = tasks
        self.task_names = [t.name for t in tasks]
        self.categories = list(set(t.category for t in tasks))
        self.chat_service = get_chat_service()

    def match(self, text: str) -> ConstraintSet:
        """Parse natural language into typed constraints using LLM.

        Args:
            text: User's constraint description.

        Returns:
            ConstraintSet with extracted constraints.
        """
        cs = ConstraintSet()

        # Handle empty or no-constraint inputs
        text_lower = text.lower().strip()
        if not text_lower or text_lower in ["none", "no", "no constraints", "skip", ""]:
            return cs

        # Build the prompt with available tasks and categories
        tasks_list = "\n".join(f"- {t.name} ({t.category})" for t in self.tasks)
        categories_list = ", ".join(self.categories)

        prompt = CONSTRAINT_MATCHING_PROMPT.format(
            tasks_list=tasks_list,
            categories_list=categories_list,
            user_input=text,
        )

        try:
            # Call LLM
            response = self.chat_service.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a JSON constraint parser. Output only valid JSON arrays.",
            )

            # Parse the response
            constraints_data = self._parse_llm_response(response)

            # Convert to typed constraints
            for item in constraints_data:
                constraint = self._dict_to_constraint(item)
                if constraint:
                    cs.add(constraint)

        except Exception as e:
            # If LLM fails, return empty constraint set
            print(f"Constraint matching error: {e}")

        return cs

    def _parse_llm_response(self, response: str) -> list[dict]:
        """Parse LLM response to extract JSON array."""
        response = response.strip()

        # Try to find JSON array in response
        # Sometimes LLM wraps it in markdown code blocks
        if "```json" in response:
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                response = match.group(1)
        elif "```" in response:
            match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                response = match.group(1)

        # Find the JSON array
        start = response.find('[')
        end = response.rfind(']') + 1

        if start >= 0 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)

        return []

    def _dict_to_constraint(self, data: dict):
        """Convert a dict to a typed constraint."""
        ctype = data.get("type")

        if ctype == "must_include_task":
            task_name = data.get("task_name")
            # Validate task exists
            if task_name in self.task_names:
                return MustIncludeTask(task_name=task_name)
            # Try case-insensitive match
            for name in self.task_names:
                if name.lower() == task_name.lower():
                    return MustIncludeTask(task_name=name)

        elif ctype == "must_include_category":
            category = data.get("category")
            if category in self.categories:
                return MustIncludeCategory(category=category)

        elif ctype == "fixed_time_slot":
            task_name = data.get("task_name")
            start_time = data.get("start_time")
            # Validate task exists
            matched_name = None
            if task_name in self.task_names:
                matched_name = task_name
            else:
                for name in self.task_names:
                    if name.lower() == task_name.lower():
                        matched_name = name
                        break
            if matched_name and isinstance(start_time, int):
                return FixedTimeSlot(task_name=matched_name, start_time=start_time)

        elif ctype == "ordered_after":
            task_name = data.get("task_name")
            after_task = data.get("after_task")
            # Validate both tasks exist
            matched_task = None
            matched_after = None
            for name in self.task_names:
                if name.lower() == task_name.lower():
                    matched_task = name
                if name.lower() == after_task.lower():
                    matched_after = name
            if matched_task and matched_after:
                return OrderedAfter(task_name=matched_task, after_task=matched_after)

        return None


def get_constraint_matcher(tasks: list[Task]) -> ConstraintMatcher:
    """Factory function to create a ConstraintMatcher."""
    return ConstraintMatcher(tasks)
