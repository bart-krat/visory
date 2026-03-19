"""LLM-based optimizer for handling ambiguous or complex constraints.

This optimizer uses an LLM to generate schedules when constraints are too
ambiguous or complex for rule-based optimizers to handle effectively.
"""
import json
from app.state import Task, TimeWindow, DailyPlan, ScheduledTask, ConstraintSet
from app.optimize.base import BaseOptimizer
from app.chat import get_chat_service
from app.utils import clean_json_response


LLM_OPTIMIZER_SYSTEM_PROMPT = """You are an expert daily schedule optimizer with natural language understanding. Given a list of tasks with durations and utilities, time constraints, and user preferences (including ambiguous or subjective ones), create an optimal schedule.

Your goal is to:
1. **INTERPRET AND APPLY user preferences** - Even if they're vague or subjective (e.g., "spread things out", "front-load work", "ease into the day"), use your reasoning to translate them into concrete scheduling decisions
2. Respect all explicit time constraints (fixed times, time ranges, ordering)
3. Maximize total utility by including high-value tasks
4. Create a realistic, executable schedule

**Common interpretation guidelines:**
- "spread out" / "space out" → Add larger buffers (15-30 min) between tasks instead of the default 5 min
- "front-load" → Schedule high-priority tasks early in the time window
- "ease into the day" → Start with lighter/shorter tasks, build up to intensive ones
- "prioritize energy" / "when fresh" → Schedule demanding tasks early
- "wind down" / "relax later" → Save lighter tasks for end of day

Respond with valid JSON only in this exact format:
{
  "schedule": [
    {
      "task": "Task name",
      "category": "work|health|personal",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "duration_minutes": 30
    }
  ],
  "reasoning": "Brief explanation of how you interpreted preferences and made scheduling decisions"
}

IMPORTANT:
- Times must be in 24-hour "HH:MM" format (e.g., "09:00", "14:30")
- Tasks must fit within the provided time window
- **Actively interpret ambiguous constraints** - don't ignore them, use reasoning to apply them
- Explain your interpretation in the reasoning field"""


class LLMOptimizer(BaseOptimizer):
    """LLM-based optimizer for complex or ambiguous scheduling scenarios.

    This optimizer is used as a fallback when:
    - User provides ambiguous natural language constraints
    - Constraints are too complex for enumeration (too many tasks)
    - Mixed constraint types that are hard to reconcile

    The LLM receives full context and uses reasoning to create a schedule
    that best satisfies the user's intent.
    """

    def __init__(self, buffer_minutes: int = 5):
        """Initialize LLM optimizer.

        Args:
            buffer_minutes: Default buffer time between tasks.
        """
        self.buffer_minutes = buffer_minutes
        self.chat_service = get_chat_service()
        self.last_reasoning = None  # Store reasoning from last optimization

    def optimize(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
        constraints: ConstraintSet | None = None,
    ) -> DailyPlan:
        """Generate schedule using LLM reasoning.

        Args:
            tasks: List of tasks with name, category, utility, duration.
            time_window: Available time window (start_time, end_time).
            constraints: Optional ConstraintSet with all constraint types.

        Returns:
            DailyPlan with LLM-generated schedule.
        """
        if not tasks:
            return DailyPlan(schedule=[], time_window=time_window)

        constraints = constraints or ConstraintSet()

        # Build comprehensive prompt with all context
        prompt = self._build_prompt(tasks, time_window, constraints)

        try:
            # Call LLM
            response = self.chat_service.simple_chat(
                user_message=prompt,
                system_prompt=LLM_OPTIMIZER_SYSTEM_PROMPT,
            )

            # Parse response
            schedule = self._parse_response(response, time_window)
            return schedule

        except Exception as e:
            # Fallback to simple scheduling if LLM fails
            print(f"LLM optimizer failed: {e}. Falling back to simple scheduling.")
            return self._fallback_schedule(tasks, time_window)

    def _build_prompt(
        self,
        tasks: list[Task],
        time_window: TimeWindow,
        constraints: ConstraintSet,
    ) -> str:
        """Build comprehensive prompt for LLM.

        Args:
            tasks: Tasks to schedule.
            time_window: Available time window.
            constraints: All constraints to consider.

        Returns:
            Formatted prompt string with all context.
        """
        # Format tasks
        tasks_info = []
        for task in tasks:
            tasks_info.append({
                "name": task.name,
                "category": task.category,
                "duration_minutes": task.duration,
                "utility": task.utility,
            })

        # Format constraints
        constraint_desc = []

        # Mandatory tasks
        if constraints.mandatory_tasks:
            constraint_desc.append(
                f"MUST include these tasks: {', '.join(constraints.mandatory_tasks)}"
            )

        # Mandatory categories
        if constraints.mandatory_categories:
            constraint_desc.append(
                f"MUST include at least one task from: {', '.join(constraints.mandatory_categories)}"
            )

        # Fixed time slots
        if constraints.fixed_slots:
            for task_name, time_minutes in constraints.fixed_slots.items():
                hours = time_minutes // 60
                minutes = time_minutes % 60
                constraint_desc.append(
                    f"'{task_name}' MUST start at {hours:02d}:{minutes:02d}"
                )

        # Ordering constraints
        if constraints.ordering_constraints:
            for before_task, after_task in constraints.ordering_constraints:
                constraint_desc.append(
                    f"'{after_task}' MUST come after '{before_task}'"
                )

        # Time range constraints
        if constraints.time_range_constraints:
            for task_name, (after_time, before_time) in constraints.time_range_constraints.items():
                range_desc = f"'{task_name}' must be scheduled"
                if after_time is not None:
                    h, m = divmod(after_time, 60)
                    range_desc += f" after {h:02d}:{m:02d}"
                if before_time is not None:
                    h, m = divmod(before_time, 60)
                    range_desc += f" before {h:02d}:{m:02d}"
                constraint_desc.append(range_desc)

        # Undefined/ambiguous constraints - THESE ARE CRITICAL TO INTERPRET
        undefined_constraints = [c for c in constraints.constraints if hasattr(c, 'description')]
        if undefined_constraints:
            constraint_desc.append("")
            constraint_desc.append("🎯 USER'S PREFERENCE (interpret and apply this):")
            for c in undefined_constraints:
                constraint_desc.append(f"   \"{c.description}\" - Use your reasoning to interpret what this means for task scheduling")

        # Build final prompt
        prompt_parts = [
            f"TIME WINDOW: {time_window.start_time} to {time_window.end_time}",
            "",
            "AVAILABLE TASKS:",
            json.dumps(tasks_info, indent=2),
            "",
        ]

        if constraint_desc:
            prompt_parts.append("CONSTRAINTS:")
            for desc in constraint_desc:
                prompt_parts.append(f"- {desc}")
            prompt_parts.append("")

        if undefined_constraints:
            prompt_parts.append(
                "🔥 CRITICAL: The user has provided a preference that you MUST interpret and apply to the schedule. "
                "Use your reasoning to understand what they mean and create a schedule that reflects their intent. "
                "Explain in your reasoning how you interpreted and applied their preference."
            )
        else:
            prompt_parts.append(
                "Create an optimal schedule that maximizes utility while respecting all constraints. "
                "Include as many high-utility tasks as possible."
            )

        return "\n".join(prompt_parts)

    def _parse_response(self, response: str, time_window: TimeWindow) -> DailyPlan:
        """Parse LLM JSON response into DailyPlan.

        Args:
            response: Raw LLM response string.
            time_window: Time window for validation.

        Returns:
            DailyPlan with parsed schedule.

        Raises:
            ValueError: If response format is invalid.
        """
        # Clean and parse JSON
        cleaned = clean_json_response(response)
        data = json.loads(cleaned)

        # Extract schedule
        schedule_data = data.get("schedule", [])
        schedule = []

        for item in schedule_data:
            task = ScheduledTask(
                task=item["task"],
                category=item["category"],
                start_time=item["start_time"],
                end_time=item["end_time"],
                duration_minutes=item["duration_minutes"],
            )
            schedule.append(task)

        # Store reasoning for display to user
        if "reasoning" in data:
            self.last_reasoning = data['reasoning']
        else:
            self.last_reasoning = None

        return DailyPlan(schedule=schedule, time_window=time_window)

    def _fallback_schedule(self, tasks: list[Task], time_window: TimeWindow) -> DailyPlan:
        """Create simple fallback schedule if LLM fails.

        Args:
            tasks: Tasks to schedule.
            time_window: Available time window.

        Returns:
            Basic schedule with highest utility tasks.
        """
        # Sort by utility (descending)
        sorted_tasks = sorted(tasks, key=lambda t: t.utility, reverse=True)

        # Select tasks that fit
        available_minutes = self._time_window_minutes(time_window)
        selected: list[Task] = []
        time_used = 0

        for task in sorted_tasks:
            task_time = task.duration + self.buffer_minutes
            if time_used + task.duration <= available_minutes:
                selected.append(task)
                time_used += task_time

        return self._schedule_tasks(selected, time_window, self.buffer_minutes)
