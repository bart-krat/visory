"""Simple test for the results service."""
from app.state import Task, TimeWindow, DailyPlan, ScheduledTask, ConstraintSet, MustIncludeTask
from app.results import get_results_service


def test_successful_schedule():
    """Test results summary with a successful schedule."""
    print("Testing successful schedule...")

    # Create some tasks
    tasks = [
        Task(name="Morning workout", category="health", utility=150.0, duration=60),
        Task(name="Team meeting", category="work", utility=200.0, duration=90),
        Task(name="Code review", category="work", utility=180.0, duration=45),
        Task(name="Lunch with friend", category="personal", utility=120.0, duration=60),
    ]

    # Create a daily plan with some scheduled tasks
    time_window = TimeWindow(start_time="09:00", end_time="17:00")
    daily_plan = DailyPlan(
        schedule=[
            ScheduledTask(
                task="Morning workout",
                category="health",
                start_time="09:00",
                end_time="10:00",
                duration_minutes=60,
            ),
            ScheduledTask(
                task="Team meeting",
                category="work",
                start_time="10:05",
                end_time="11:35",
                duration_minutes=90,
            ),
            ScheduledTask(
                task="Code review",
                category="work",
                start_time="11:40",
                end_time="12:25",
                duration_minutes=45,
            ),
        ],
        time_window=time_window,
    )

    # Create constraints
    constraint_set = ConstraintSet()
    constraint_set.add(MustIncludeTask(task_name="Team meeting"))

    # Get results service and generate summary
    results_service = get_results_service()
    summary = results_service.summarize_results(
        daily_plan=daily_plan,
        all_tasks=tasks,
        constraint_set=constraint_set,
        optimizer_type="greedy",
    )

    print("\n" + "="*60)
    print("AI SUMMARY:")
    print("="*60)
    print(summary)
    print("="*60)


def test_empty_schedule():
    """Test results summary with an empty schedule (constraints couldn't be satisfied)."""
    print("\n\nTesting empty schedule...")

    # Create some tasks
    tasks = [
        Task(name="Long project", category="work", utility=200.0, duration=480),  # 8 hours
        Task(name="Another long task", category="work", utility=150.0, duration=360),  # 6 hours
    ]

    # Create an empty daily plan
    time_window = TimeWindow(start_time="09:00", end_time="10:00")  # Only 1 hour available
    daily_plan = DailyPlan(schedule=[], time_window=time_window)

    # Create strict constraints that can't be satisfied
    constraint_set = ConstraintSet()
    constraint_set.add(MustIncludeTask(task_name="Long project"))
    constraint_set.add(MustIncludeTask(task_name="Another long task"))

    # Get results service and generate summary
    results_service = get_results_service()
    summary = results_service.summarize_results(
        daily_plan=daily_plan,
        all_tasks=tasks,
        constraint_set=constraint_set,
        optimizer_type="enumeration",
    )

    print("\n" + "="*60)
    print("AI SUMMARY:")
    print("="*60)
    print(summary)
    print("="*60)


if __name__ == "__main__":
    test_successful_schedule()
    test_empty_schedule()
    print("\n✅ Tests completed!")
