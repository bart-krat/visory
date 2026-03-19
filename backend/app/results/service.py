"""Results service for validating constraints and explaining optimization results."""
from app.chat import get_chat_service
from app.state import Task, DailyPlan, ConstraintSet, FixedTimeSlot, OrderedAfter, TimeRangeConstraint, UndefinedConstraint


RESULTS_SYSTEM_PROMPT = """You are a constraint validation assistant.

Your role is to:
1. Detect contradictions in user constraints (e.g., task A must be before B, but A's fixed time is after B's fixed time)
2. If constraints contradict, explain clearly what's wrong and suggest how to fix it
3. If constraints are valid but the schedule failed, explain which constraints couldn't be satisfied and why
4. If everything works, keep it brief and positive

Be direct and focus on constraint logic, not schedule commentary."""


class ResultsService:
    """Service for generating AI-powered summaries of optimization results."""

    def __init__(self):
        self.chat_service = get_chat_service()

    def summarize_results(
        self,
        daily_plan: DailyPlan,
        all_tasks: list[Task],
        constraint_set: ConstraintSet,
        optimizer_type: str,
    ) -> str:
        """Validate constraints and explain results.

        Three possible outcomes:
        1. Constraints met - optimizer satisfied all constraints
        2. Constraints contradictory - constraints are logically impossible
        3. Constraints not met - optimizer didn't satisfy user's constraints

        Args:
            daily_plan: The optimized schedule from the optimizer.
            all_tasks: All tasks that were available to schedule.
            constraint_set: The constraints that were applied.
            optimizer_type: The type of optimizer used (e.g., "greedy", "enumeration").

        Returns:
            A validation message explaining the outcome.
        """
        # Check for undefined/ambiguous constraints
        undefined_constraints = [c for c in constraint_set.constraints if isinstance(c, UndefinedConstraint)]
        undefined_message = ""
        if undefined_constraints:
            # If LLM optimizer was used, it handled these constraints
            if optimizer_type == "llm":
                undefined_message = "\n\n💡 **AI-Powered Scheduling:** Your preferences were interpreted using AI reasoning:\n"
                for uc in undefined_constraints:
                    undefined_message += f"- \"{uc.description}\"\n"
                undefined_message += "\nThe LLM optimizer applied its understanding of these ambiguous constraints to create your schedule.\n"
            else:
                # Other optimizers can't handle undefined constraints
                undefined_message = "\n\n⚠️ **Note:** Some constraints could not be encoded:\n"
                for uc in undefined_constraints:
                    undefined_message += f"- \"{uc.description}\" - This constraint is too subjective/vague for rule-based optimization\n"
                undefined_message += "\nThese have been ignored during optimization.\n"

        # CASE 2: Check for constraint contradictions
        contradictions = self._detect_contradictions(constraint_set, all_tasks)
        if contradictions:
            return self._explain_contradictions(contradictions) + undefined_message

        # If no schedule was produced
        if len(daily_plan.schedule) == 0:
            if not constraint_set.is_empty():
                # Could be contradictory or just impossible to fit
                return self._explain_constraint_failure(constraint_set, all_tasks, daily_plan) + undefined_message
            else:
                return "Could not fit any tasks in the available time window. Try extending your available hours or reducing task durations."

        # CASE 3: Check if optimizer satisfied the constraints
        unmet_constraints = self._check_constraints_met(daily_plan, constraint_set, all_tasks)
        if unmet_constraints:
            return self._explain_unmet_constraints(unmet_constraints, constraint_set) + undefined_message

        # CASE 1: Success - constraints met and schedule optimized
        scheduled_count = len(daily_plan.schedule)
        total_count = len(all_tasks)

        # Filter out undefined constraints for checking if we have real constraints
        real_constraints = [c for c in constraint_set.constraints if not isinstance(c, UndefinedConstraint)]

        if real_constraints:
            return f"✅ All constraints satisfied. Your optimized schedule is ready!" + undefined_message
        else:
            if scheduled_count == total_count:
                return "Here is your optimized schedule. All tasks have been included!" + undefined_message
            else:
                return f"Here is your optimized schedule. {scheduled_count} out of {total_count} tasks have been scheduled." + undefined_message

    def _detect_contradictions(
        self, constraint_set: ConstraintSet, all_tasks: list[Task]
    ) -> list[str]:
        """Detect logical contradictions in constraints.

        Returns:
            List of contradiction descriptions (empty if no contradictions).
        """
        contradictions = []

        # Get fixed time slots
        fixed_slots = constraint_set.fixed_slots  # {task_name: start_time_minutes}
        ordering_constraints = constraint_set.ordering_constraints  # [(before_task, after_task), ...]

        # Check ordering vs fixed time contradictions
        for before_task, after_task in ordering_constraints:
            before_time = fixed_slots.get(before_task)
            after_time = fixed_slots.get(after_task)

            if before_time is not None and after_time is not None:
                # Both have fixed times - check if ordering is satisfied
                if before_time >= after_time:
                    before_h, before_m = divmod(before_time, 60)
                    after_h, after_m = divmod(after_time, 60)
                    contradictions.append(
                        f"'{after_task}' must come after '{before_task}', but '{after_task}' is fixed at "
                        f"{after_h:02d}:{after_m:02d} and '{before_task}' is fixed at {before_h:02d}:{before_m:02d}"
                    )

        # Check for duplicate fixed time slots
        task_names_by_time = {}
        for task_name, start_time in fixed_slots.items():
            if start_time in task_names_by_time:
                h, m = divmod(start_time, 60)
                contradictions.append(
                    f"Multiple tasks scheduled at {h:02d}:{m:02d}: '{task_names_by_time[start_time]}' and '{task_name}'"
                )
            else:
                task_names_by_time[start_time] = task_name

        # Check for fixed time slots outside time window (if we had access to time_window)
        # This would require passing time_window to this method

        return contradictions

    def _explain_contradictions(self, contradictions: list[str]) -> str:
        """Generate explanation for constraint contradictions."""
        explanation = "⚠️ **Constraint Contradictions Detected**\n\n"
        explanation += "Your constraints cannot be satisfied because:\n\n"
        for i, contradiction in enumerate(contradictions, 1):
            explanation += f"{i}. {contradiction}\n"
        explanation += "\n**Suggestions:**\n"
        explanation += "- Remove conflicting fixed time slots, OR\n"
        explanation += "- Remove ordering constraints that conflict with fixed times, OR\n"
        explanation += "- Adjust the fixed times to match the desired order"
        return explanation

    def _explain_constraint_failure(
        self, constraint_set: ConstraintSet, all_tasks: list[Task], daily_plan: DailyPlan
    ) -> str:
        """Explain which constraints couldn't be satisfied."""
        explanation = "⚠️ **Could not satisfy all constraints**\n\n"

        # Check mandatory tasks
        scheduled_names = {st.task for st in daily_plan.schedule}
        missing_mandatory = constraint_set.mandatory_tasks - scheduled_names

        if missing_mandatory:
            explanation += "**Missing required tasks:**\n"
            for task_name in missing_mandatory:
                # Find the task to show its duration
                task = next((t for t in all_tasks if t.name == task_name), None)
                if task:
                    explanation += f"- '{task_name}' ({task.duration} minutes)\n"
                else:
                    explanation += f"- '{task_name}'\n"

        explanation += "\n**Suggestions:**\n"
        explanation += "- Extend your available time window, OR\n"
        explanation += "- Reduce task durations, OR\n"
        explanation += "- Remove some mandatory constraints"

        return explanation

    def _check_constraints_met(
        self, daily_plan: DailyPlan, constraint_set: ConstraintSet, all_tasks: list[Task]
    ) -> list[str]:
        """Check if the optimizer actually satisfied all constraints.

        Returns:
            List of unmet constraint descriptions (empty if all constraints met).
        """
        unmet = []
        scheduled_names = {st.task for st in daily_plan.schedule}

        # Check mandatory tasks
        for task_name in constraint_set.mandatory_tasks:
            if task_name not in scheduled_names:
                unmet.append(f"Must include '{task_name}' - NOT INCLUDED")

        # Check mandatory categories
        scheduled_categories = {st.category for st in daily_plan.schedule}
        for category in constraint_set.mandatory_categories:
            if category not in scheduled_categories:
                unmet.append(f"Must include a {category} task - NONE INCLUDED")

        # Check fixed time slots
        schedule_dict = {st.task: st for st in daily_plan.schedule}
        for task_name, required_time_minutes in constraint_set.fixed_slots.items():
            if task_name in schedule_dict:
                scheduled_task = schedule_dict[task_name]
                # Parse scheduled start time
                h, m = map(int, scheduled_task.start_time.split(":"))
                actual_time_minutes = h * 60 + m

                if actual_time_minutes != required_time_minutes:
                    req_h, req_m = divmod(required_time_minutes, 60)
                    unmet.append(
                        f"'{task_name}' should be at {req_h:02d}:{req_m:02d} - "
                        f"SCHEDULED AT {scheduled_task.start_time}"
                    )
            else:
                req_h, req_m = divmod(required_time_minutes, 60)
                unmet.append(f"'{task_name}' should be at {req_h:02d}:{req_m:02d} - NOT SCHEDULED")

        # Check ordering constraints
        task_positions = {st.task: i for i, st in enumerate(daily_plan.schedule)}
        for before_task, after_task in constraint_set.ordering_constraints:
            before_pos = task_positions.get(before_task)
            after_pos = task_positions.get(after_task)

            if before_pos is None:
                unmet.append(f"'{after_task}' should come after '{before_task}' - '{before_task}' NOT SCHEDULED")
            elif after_pos is None:
                unmet.append(f"'{after_task}' should come after '{before_task}' - '{after_task}' NOT SCHEDULED")
            elif before_pos >= after_pos:
                unmet.append(
                    f"'{after_task}' should come after '{before_task}' - "
                    f"ORDER VIOLATED ('{after_task}' is at position {after_pos + 1}, "
                    f"'{before_task}' is at position {before_pos + 1})"
                )

        # Check time range constraints
        for constraint in constraint_set.constraints:
            if isinstance(constraint, TimeRangeConstraint):
                task_name = constraint.task_name
                if task_name in schedule_dict:
                    scheduled_task = schedule_dict[task_name]
                    # Parse scheduled start time
                    h, m = map(int, scheduled_task.start_time.split(":"))
                    actual_time_minutes = h * 60 + m

                    if constraint.after_time is not None and actual_time_minutes < constraint.after_time:
                        after_h, after_m = divmod(constraint.after_time, 60)
                        unmet.append(
                            f"'{task_name}' should be after {after_h:02d}:{after_m:02d} - "
                            f"SCHEDULED AT {scheduled_task.start_time}"
                        )
                    if constraint.before_time is not None and actual_time_minutes > constraint.before_time:
                        before_h, before_m = divmod(constraint.before_time, 60)
                        unmet.append(
                            f"'{task_name}' should be before {before_h:02d}:{before_m:02d} - "
                            f"SCHEDULED AT {scheduled_task.start_time}"
                        )
                else:
                    # Task not scheduled
                    range_desc = []
                    if constraint.after_time is not None:
                        after_h, after_m = divmod(constraint.after_time, 60)
                        range_desc.append(f"after {after_h:02d}:{after_m:02d}")
                    if constraint.before_time is not None:
                        before_h, before_m = divmod(constraint.before_time, 60)
                        range_desc.append(f"before {before_h:02d}:{before_m:02d}")
                    unmet.append(f"'{task_name}' should be {' and '.join(range_desc)} - NOT SCHEDULED")

        return unmet

    def _explain_unmet_constraints(self, unmet_constraints: list[str], constraint_set: ConstraintSet) -> str:
        """Explain which constraints were not satisfied by the optimizer."""
        explanation = "⚠️ **Constraints Not Met**\n\n"
        explanation += "The optimizer did not satisfy the following constraints:\n\n"

        for i, constraint in enumerate(unmet_constraints, 1):
            explanation += f"{i}. {constraint}\n"

        explanation += "\n**This indicates:**\n"
        explanation += "- The constraint parser may have misunderstood your request, OR\n"
        explanation += "- The optimizer couldn't satisfy all constraints simultaneously\n\n"
        explanation += "**Suggestions:**\n"
        explanation += "- Try rephrasing your constraints, OR\n"
        explanation += "- Extend your available time window, OR\n"
        explanation += "- Reduce the number of constraints"

        return explanation


# Singleton instance
_results_service: ResultsService | None = None


def get_results_service() -> ResultsService:
    """Get or create the singleton ResultsService instance."""
    global _results_service
    if _results_service is None:
        _results_service = ResultsService()
    return _results_service
