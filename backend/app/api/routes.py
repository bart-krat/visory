"""API routes for the Visory planning workflow."""
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.state import ConstraintSet
from app.api.schemas import (
    WorkflowStartResponse,
    WorkflowMessageRequest,
    ConstraintsSubmission,
    ConstraintSelectionRequest,
    UtilityMessageRequest,
)
from app.orchestrator import get_or_create_orchestrator, get_orchestrator
from app.utility import UtilityQuestionnaire

router = APIRouter()

# Session storage for utility questionnaires (separate from orchestrator)
_utility_sessions: dict[str, UtilityQuestionnaire] = {}


@router.post("/workflow/start", response_model=WorkflowStartResponse)
def workflow_start():
    """Start a new session and return welcome message."""
    session_id = str(uuid.uuid4())
    orchestrator = get_or_create_orchestrator(session_id)
    initial_message = orchestrator.start()

    return WorkflowStartResponse(
        session_id=session_id,
        message=initial_message,
        phase=orchestrator.get_phase().value,
    )


@router.post("/utility/start")
def utility_start(session_id: str):
    """Start the utility questionnaire for a session.

    This is a separate flow from the main planning workflow.
    Results are saved to the session state for use in planning.
    """
    # Ensure orchestrator exists for this session
    orchestrator = get_orchestrator(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    # Create questionnaire for this session
    questionnaire = UtilityQuestionnaire()
    _utility_sessions[session_id] = questionnaire

    first_question = questionnaire.get_current_question()
    q_num = questionnaire.get_question_number()
    total = questionnaire.get_total_questions()

    return {
        "session_id": session_id,
        "message": f"Question {q_num}/{total}: {first_question}",
        "phase": "questionnaire",
        "progress": {"current": q_num, "total": total},
    }


@router.post("/utility/message")
def utility_message(request: UtilityMessageRequest):
    """Submit an answer to the utility questionnaire.

    Returns the next question or evaluation results when complete.
    """
    questionnaire = _utility_sessions.get(request.session_id)
    if not questionnaire:
        raise HTTPException(status_code=404, detail="Questionnaire session not found")

    orchestrator = get_orchestrator(request.session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    # Record the Q&A
    current_q = questionnaire.get_current_question()
    orchestrator.state.questionnaire_answers.append({
        "question": current_q,
        "answer": request.message,
    })

    # Submit answer and get next question
    next_question = questionnaire.submit_answer(request.message)

    if next_question:
        q_num = questionnaire.get_question_number()
        total = questionnaire.get_total_questions()
        return {
            "message": f"Question {q_num}/{total}: {next_question}",
            "phase": "questionnaire",
            "progress": {"current": q_num, "total": total},
            "is_complete": False,
        }
    else:
        # Questionnaire complete - evaluate and save to state
        try:
            weights = questionnaire.evaluate()
            orchestrator.state.utility_weights = {
                "work": weights.work,
                "health": weights.health,
                "personal": weights.personal,
            }
            orchestrator._persist_state()

            # Clean up questionnaire session
            del _utility_sessions[request.session_id]

            return {
                "message": f"""Thank you! Based on your answers, here's how I understand your priorities:

  Work:     {weights.work:.0f}/300
  Health:   {weights.health:.0f}/300
  Personal: {weights.personal:.0f}/300

_{weights.reasoning}_

Your preferences have been saved. You can now plan your day!""",
                "phase": "evaluation_complete",
                "is_complete": True,
                "weights": weights.to_dict(),
            }
        except Exception as e:
            # Use default weights on error
            orchestrator.state.utility_weights = {"work": 100, "health": 100, "personal": 100}
            orchestrator._persist_state()
            del _utility_sessions[request.session_id]

            return {
                "message": "I had trouble analyzing your responses. Using balanced weights. You can now plan your day!",
                "phase": "evaluation_complete",
                "is_complete": True,
                "weights": {"work": 100, "health": 100, "personal": 100},
            }


@router.post("/planning/start")
def planning_start(session_id: str):
    """Start the planning workflow for a session.

    Uses utility weights from questionnaire if completed, otherwise defaults.
    """
    orchestrator = get_orchestrator(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    message = orchestrator.start_planning()

    return {
        "session_id": session_id,
        "message": message,
        "phase": orchestrator.get_phase().value,
        "utility_weights": orchestrator.state.utility_weights,
    }


@router.post("/workflow/message")
def workflow_message(request: WorkflowMessageRequest):
    """Send a message to the workflow and get streaming response."""
    orchestrator = get_orchestrator(request.session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    def generate():
        try:
            for chunk in orchestrator.process_message(request.message):
                yield chunk
        except Exception as e:
            yield f"\n\n[Error: {str(e)}]"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "X-Workflow-Phase": orchestrator.get_phase().value,
        },
    )


@router.post("/workflow/constraints")
def submit_constraints(request: ConstraintsSubmission):
    """Submit task constraints (duration, time slots, time window)."""
    from app.state import TimeWindow
    from app.constraints import ConstraintClarification
    from app.orchestrator import WorkflowPhase

    orchestrator = get_orchestrator(request.session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update tasks with duration and time_slot
    for task_input in request.tasks:
        for task in orchestrator.state.tasks:
            if task.name == task_input.name:
                task.duration = task_input.duration
                if task_input.time_slot:
                    h, m = map(int, task_input.time_slot.split(":"))
                    task.time_slot = h * 60 + m
                break

    # Set time window
    orchestrator.state.time_window = TimeWindow(
        start_time=request.time_window_start,
        end_time=request.time_window_end,
    )

    # Build constraint clarification for button options
    orchestrator.constraint_clarification = ConstraintClarification(tasks=orchestrator.state.tasks)

    # Advance to constraint clarification phase
    orchestrator.phase = WorkflowPhase.CONSTRAINT_CLARIFICATION
    orchestrator._persist_state()

    return {
        "success": True,
        "phase": orchestrator.phase.value,
        "message": "Constraints saved. Please select an optimization preference.",
    }


@router.get("/constraints/options/{session_id}")
def get_constraint_options(session_id: str):
    """Get available constraint options for UI.

    Returns:
        - options: List of task constraint buttons
        - supports_custom_text: True (user can type custom constraints)
    """
    from app.constraints import ConstraintClarification

    orchestrator = get_orchestrator(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    clarification = ConstraintClarification(tasks=orchestrator.state.tasks)
    return {
        "options": clarification.get_options_for_ui(),
        "supports_custom_text": True,
    }


@router.post("/constraints/submit")
def submit_constraint_selection(request: ConstraintSelectionRequest):
    """Submit selected constraints and run optimization.

    Accepts either:
    - constraint_ids: List of task constraint IDs (button selections)
    - custom_constraint: Free-form text describing constraints

    Returns constraint matching details so user can see what was understood.
    """
    orchestrator = get_orchestrator(request.session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    output_chunks = []
    matched_constraints = []

    if request.custom_constraint:
        # Handle custom text constraint via semantic matching
        constraint_set = orchestrator.apply_constraints_from_text(request.custom_constraint)

        if not constraint_set.is_empty():
            output_chunks.append(f"Understood from \"{request.custom_constraint}\":\n")
            for c in constraint_set.constraints:
                output_chunks.append(f"  - {c}\n")
            output_chunks.append("\n")
            matched_constraints = constraint_set.to_dict()
        else:
            # Parsing failed - add as UndefinedConstraint so LLM optimizer handles it
            from app.state import UndefinedConstraint
            constraint_set.add(UndefinedConstraint(description=request.custom_constraint))
            orchestrator.constraint_set = constraint_set
            orchestrator.state.constraint_set = constraint_set

            output_chunks.append(f"Interpreting constraint: \"{request.custom_constraint}\"\n")
            output_chunks.append("Using AI reasoning to create your schedule...\n\n")
            matched_constraints = constraint_set.to_dict()

    elif request.constraint_ids:
        # Handle button-selected task constraints
        orchestrator.apply_constraints_from_ids(request.constraint_ids)

        if not orchestrator.constraint_set.is_empty():
            output_chunks.append(f"Applying: {orchestrator.constraint_set.describe()}\n\n")
            matched_constraints = orchestrator.constraint_set.to_dict()

    else:
        # No custom constraints selected - but still need to add fixed time slots from task table
        from app.state import FixedTimeSlot
        orchestrator.constraint_set = ConstraintSet()

        # Add fixed time slots from task.time_slot (set in the constraints table)
        for task in orchestrator.state.tasks:
            if task.time_slot is not None:
                orchestrator.constraint_set.add(FixedTimeSlot(
                    task_name=task.name,
                    start_time=task.time_slot,
                ))

        orchestrator.state.constraint_set = orchestrator.constraint_set

        if orchestrator.constraint_set.is_empty():
            output_chunks.append("No constraints. Optimizing for maximum utility...\n\n")
        else:
            output_chunks.append(f"Applying: {orchestrator.constraint_set.describe()}\n\n")
            matched_constraints = orchestrator.constraint_set.to_dict()

    # Run optimization
    for chunk in orchestrator.run_optimization():
        output_chunks.append(chunk)

    return {
        "success": True,
        "phase": orchestrator.phase.value,
        "message": "".join(output_chunks),
        "matched_constraints": matched_constraints,
    }


@router.get("/workflow/{session_id}/state")
def workflow_state(session_id: str):
    """Get the current state of a workflow session."""
    orchestrator = get_orchestrator(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    state = orchestrator.get_state()

    # Get questionnaire progress from utility session if active
    questionnaire_progress = None
    questionnaire = _utility_sessions.get(session_id)
    if questionnaire:
        questionnaire_progress = {
            "current": questionnaire.get_question_number(),
            "total": questionnaire.get_total_questions(),
            "is_complete": questionnaire.is_complete(),
        }

    return {
        "phase": orchestrator.get_phase().value,
        "utility_weights": state.utility_weights,
        "questionnaire_progress": questionnaire_progress,
        "questionnaire_answers": state.questionnaire_answers,
        "raw_tasks": state.raw_tasks,
        "tasks": [
            {
                "name": t.name,
                "category": t.category,
                "utility": t.utility,
                "duration": t.duration,
                "time_slot": t.time_slot,
            }
            for t in state.tasks
        ],
        "time_window": {
            "start_time": state.time_window.start_time,
            "end_time": state.time_window.end_time,
        } if state.time_window else None,
        "constraints": {
            "raw": orchestrator.constraint_set.to_dict(),
            "description": orchestrator.constraint_set.describe(),
            "mandatory_tasks": list(orchestrator.constraint_set.mandatory_tasks),
            "mandatory_categories": list(orchestrator.constraint_set.mandatory_categories),
            "fixed_slots": orchestrator.constraint_set.fixed_slots,
            "ordering": orchestrator.constraint_set.ordering_constraints,
        },
        "optimizer_type": state.optimizer_type,
        "daily_plan": {
            "schedule": [
                {
                    "task": t.task,
                    "category": t.category,
                    "start_time": t.start_time,
                    "end_time": t.end_time,
                    "duration_minutes": t.duration_minutes,
                }
                for t in state.daily_plan.schedule
            ],
            "time_window": {
                "start_time": state.daily_plan.time_window.start_time,
                "end_time": state.daily_plan.time_window.end_time,
            } if state.daily_plan.time_window else None,
        } if state.daily_plan else None,
    }


@router.post("/workflow/navigate")
def navigate_to_phase(session_id: str, target_phase: str):
    """Navigate back to a specific phase.

    Valid target_phase values:
    - "questionnaire": Return to AI Personalizer
    - "collect_tasks": Edit tasks
    - "constraints": Edit durations and time slots
    - "constraint_clarification": Edit custom constraints
    """
    orchestrator = get_orchestrator(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    if target_phase == "questionnaire":
        # Create/restart questionnaire for this session
        questionnaire = UtilityQuestionnaire()
        _utility_sessions[session_id] = questionnaire

        first_question = questionnaire.get_current_question()
        q_num = questionnaire.get_question_number()
        total = questionnaire.get_total_questions()

        return {
            "success": True,
            "phase": "questionnaire",
            "message": f"Let's personalize your schedule. Question {q_num}/{total}: {first_question}",
            "progress": {"current": q_num, "total": total},
        }
    elif target_phase == "collect_tasks":
        message = orchestrator.return_to_tasks()
        return {
            "success": True,
            "phase": orchestrator.phase.value,
            "message": message,
        }
    elif target_phase == "constraints":
        message = orchestrator.return_to_constraints()
        return {
            "success": True,
            "phase": orchestrator.phase.value,
            "message": message,
        }
    elif target_phase == "constraint_clarification":
        message = orchestrator.return_to_constraint_clarification()
        return {
            "success": True,
            "phase": orchestrator.phase.value,
            "message": message,
        }
    else:
        raise HTTPException(status_code=400, detail=f"Invalid target phase: {target_phase}")

