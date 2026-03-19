"""Test TimeRangeConstraint in enumeration optimizer."""
from app.state import Task, TimeWindow, ConstraintSet, TimeRangeConstraint, MustIncludeTask
from app.optimize.router import get_optimizer_router


def test_time_range_afternoon():
    """Test 'gym in the afternoon' constraint."""
    print("Testing: gym in the afternoon\n")

    # Create tasks
    tasks = [
        Task(name="swim", category="health", utility=100.0, duration=30),
        Task(name="gym", category="health", utility=150.0, duration=30),
        Task(name="work", category="work", utility=120.0, duration=30),
    ]

    # Time window: 9am to 5pm
    time_window = TimeWindow(start_time="09:00", end_time="17:00")

    # Constraint: gym in the afternoon (12pm-5pm)
    constraint_set = ConstraintSet()
    constraint_set.add(TimeRangeConstraint(
        task_name="gym",
        after_time=12 * 60,   # 12:00 (noon)
        before_time=17 * 60,  # 17:00 (5pm)
    ))
    constraint_set.add(MustIncludeTask(task_name="gym"))

    # Run optimizer
    router = get_optimizer_router()
    optimizer_type = router._select_optimizer(tasks, time_window, constraint_set)
    print(f"Selected optimizer: {optimizer_type.value}")

    daily_plan = router.optimize(tasks, time_window, constraints=constraint_set)

    # Display results
    print(f"\nSchedule ({len(daily_plan.schedule)} tasks):")
    for st in daily_plan.schedule:
        print(f"  {st.start_time} - {st.end_time}: {st.task} ({st.category})")

    # Check if gym is scheduled in the afternoon
    gym_task = next((st for st in daily_plan.schedule if st.task == "gym"), None)
    if gym_task:
        h, m = map(int, gym_task.start_time.split(":"))
        actual_minutes = h * 60 + m
        if actual_minutes >= 12 * 60 and actual_minutes < 17 * 60:
            print(f"\n✅ SUCCESS: Gym scheduled at {gym_task.start_time} (in afternoon)")
        else:
            print(f"\n❌ FAIL: Gym scheduled at {gym_task.start_time} (NOT in afternoon)")
    else:
        print("\n❌ FAIL: Gym not scheduled")


def test_time_range_before_noon():
    """Test 'workout before noon' constraint."""
    print("\n" + "="*60)
    print("Testing: workout before noon\n")

    # Create tasks
    tasks = [
        Task(name="workout", category="health", utility=150.0, duration=45),
        Task(name="lunch", category="personal", utility=100.0, duration=60),
        Task(name="meeting", category="work", utility=120.0, duration=30),
    ]

    # Time window: 9am to 3pm
    time_window = TimeWindow(start_time="09:00", end_time="15:00")

    # Constraint: workout before noon
    constraint_set = ConstraintSet()
    constraint_set.add(TimeRangeConstraint(
        task_name="workout",
        after_time=None,      # No lower bound
        before_time=12 * 60,  # Before 12:00 (noon)
    ))
    constraint_set.add(MustIncludeTask(task_name="workout"))

    # Run optimizer
    router = get_optimizer_router()
    daily_plan = router.optimize(tasks, time_window, constraints=constraint_set)

    # Display results
    print(f"\nSchedule ({len(daily_plan.schedule)} tasks):")
    for st in daily_plan.schedule:
        print(f"  {st.start_time} - {st.end_time}: {st.task} ({st.category})")

    # Check if workout is scheduled before noon
    workout_task = next((st for st in daily_plan.schedule if st.task == "workout"), None)
    if workout_task:
        h, m = map(int, workout_task.start_time.split(":"))
        actual_minutes = h * 60 + m
        if actual_minutes < 12 * 60:
            print(f"\n✅ SUCCESS: Workout scheduled at {workout_task.start_time} (before noon)")
        else:
            print(f"\n❌ FAIL: Workout scheduled at {workout_task.start_time} (NOT before noon)")
    else:
        print("\n❌ FAIL: Workout not scheduled")


def test_time_range_with_fixed_slot():
    """Test time range constraint combined with fixed time slot."""
    print("\n" + "="*60)
    print("Testing: time range + fixed slot\n")

    # Create tasks
    tasks = [
        Task(name="gym", category="health", utility=150.0, duration=30),
        Task(name="lunch", category="personal", utility=100.0, duration=60),
        Task(name="meeting", category="work", utility=120.0, duration=30),
    ]

    # Time window: 9am to 5pm
    time_window = TimeWindow(start_time="09:00", end_time="17:00")

    # Constraints:
    # - gym in afternoon
    # - meeting fixed at 10am
    constraint_set = ConstraintSet()
    from app.state import FixedTimeSlot
    constraint_set.add(FixedTimeSlot(task_name="meeting", start_time=10 * 60))  # 10:00am
    constraint_set.add(TimeRangeConstraint(
        task_name="gym",
        after_time=12 * 60,   # After noon
        before_time=None,
    ))
    constraint_set.add(MustIncludeTask(task_name="gym"))
    constraint_set.add(MustIncludeTask(task_name="meeting"))

    # Run optimizer
    router = get_optimizer_router()
    daily_plan = router.optimize(tasks, time_window, constraints=constraint_set)

    # Display results
    print(f"\nSchedule ({len(daily_plan.schedule)} tasks):")
    for st in daily_plan.schedule:
        print(f"  {st.start_time} - {st.end_time}: {st.task} ({st.category})")

    # Validate
    gym_task = next((st for st in daily_plan.schedule if st.task == "gym"), None)
    meeting_task = next((st for st in daily_plan.schedule if st.task == "meeting"), None)

    success = True
    if meeting_task:
        if meeting_task.start_time == "10:00":
            print(f"\n✅ Meeting at 10:00 (correct)")
        else:
            print(f"\n❌ Meeting at {meeting_task.start_time} (should be 10:00)")
            success = False
    else:
        print("\n❌ Meeting not scheduled")
        success = False

    if gym_task:
        h, m = map(int, gym_task.start_time.split(":"))
        actual_minutes = h * 60 + m
        if actual_minutes >= 12 * 60:
            print(f"✅ Gym at {gym_task.start_time} (after noon)")
        else:
            print(f"❌ Gym at {gym_task.start_time} (should be after noon)")
            success = False
    else:
        print("❌ Gym not scheduled")
        success = False

    if success:
        print("\n✅ All constraints satisfied!")


if __name__ == "__main__":
    test_time_range_afternoon()
    test_time_range_before_noon()
    test_time_range_with_fixed_slot()
    print("\n" + "="*60)
    print("✅ All tests completed!")
