import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.api.schemas import (
    ChatMessage,
    ChatResponse,
    CategorizeRequest,
    CategorizeResponse,
    CategorizedTask,
    WorkflowStartResponse,
    WorkflowMessageRequest,
    ConstraintsSubmission,
    ConstraintSelectionRequest,
)
from app.chat import get_chat_service
from app.categorize import get_categorize_service
from app.orchestrator import get_or_create_orchestrator, get_orchestrator

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(message: ChatMessage):
    """Chat endpoint for LLM interactions."""
    try:
        service = get_chat_service()

        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in message.conversation_history
        ]
        messages.append({"role": "user", "content": message.content})

        response = service.chat(
            messages=messages,
            system_prompt=message.system_prompt,
        )

        return ChatResponse(message=response, done=True)

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat service error: {str(e)}")


@router.post("/categorize", response_model=CategorizeResponse)
def categorize(request: CategorizeRequest):
    """Categorize tasks into work, health, or personal."""
    try:
        service = get_categorize_service()
        result = service.categorize(request.tasks)
        categorized = [CategorizedTask(**item) for item in result]
        return CategorizeResponse(categorized_tasks=categorized)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categorize service error: {str(e)}")


@router.post("/workflow/start", response_model=WorkflowStartResponse)
def workflow_start():
    """Start a new planning workflow session."""
    session_id = str(uuid.uuid4())
    orchestrator = get_or_create_orchestrator(session_id)
    initial_message = orchestrator.start()

    return WorkflowStartResponse(
        session_id=session_id,
        message=initial_message,
        phase=orchestrator.get_phase().value,
    )


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

    orchestrator = get_orchestrator(request.session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update tasks with duration and time_slot
    for task_input in request.tasks:
        for task in orchestrator.state.tasks:
            if task.name == task_input.name:
                task.duration = task_input.duration
                if task_input.time_slot:
                    # Convert "HH:MM" to minutes from midnight
                    h, m = map(int, task_input.time_slot.split(":"))
                    task.time_slot = h * 60 + m
                break

    # Set time window
    orchestrator.state.time_window = TimeWindow(
        start_time=request.time_window_start,
        end_time=request.time_window_end,
    )

    # Build constraint clarification with current tasks for dynamic options
    from app.constraints import ConstraintClarification
    orchestrator.constraint_clarification = ConstraintClarification(tasks=orchestrator.state.tasks)

    # Advance to constraint clarification phase
    from app.orchestrator import WorkflowPhase
    orchestrator.phase = WorkflowPhase.CONSTRAINT_CLARIFICATION
    orchestrator._persist_state()

    return {
        "success": True,
        "phase": orchestrator.phase.value,
        "message": "Constraints saved. Please select an optimization preference.",
    }


@router.get("/constraints/options/{session_id}")
def get_constraint_options(session_id: str):
    """Get available constraint options for UI based on session tasks.

    Returns:
        - options: List of task constraint buttons
        - supports_custom_text: True (user can type custom constraints)
    """
    from app.constraints import ConstraintClarification

    orchestrator = get_orchestrator(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build clarification with current tasks for dynamic options
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
    """
    from app.constraints import ConstraintClarification, get_constraint_matcher
    from app.state import CustomConstraint

    orchestrator = get_orchestrator(request.session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build clarification to parse constraint IDs
    clarification = ConstraintClarification(tasks=orchestrator.state.tasks)
    router = orchestrator.optimizer_service.router

    output_chunks = []

    if request.custom_constraint:
        # Handle custom text constraint via semantic matching
        custom = CustomConstraint(raw_text=request.custom_constraint)
        matcher = get_constraint_matcher(orchestrator.state.tasks)
        matched = matcher.match(custom)

        if matched.is_matched:
            output_chunks.append(f"Understood: \"{custom.raw_text}\"\n")
            output_chunks.append(f"{matched.match_explanation}\n\n")

            # Apply matched constraints
            router.mandatory_tasks = set(matched.matched_tasks) if matched.matched_tasks else None
            router.mandatory_categories = set(matched.matched_categories) if matched.matched_categories else None

            # Store for display
            from app.state import Constraint
            orchestrator.state.constraints = [Constraint(
                id="CUSTOM",
                name="Custom Constraint",
                description=custom.raw_text,
                button_label=matched.match_explanation,
            )]
        else:
            output_chunks.append(f"Could not match: \"{custom.raw_text}\"\n")
            output_chunks.append("Optimizing for maximum utility...\n\n")
            router.mandatory_tasks = None
            router.mandatory_categories = None
            orchestrator.state.constraints = []

    elif request.constraint_ids:
        # Handle button-selected task constraints
        constraints = []
        for constraint_id in request.constraint_ids:
            constraint = clarification.parse_response(constraint_id)
            if constraint and not isinstance(constraint, CustomConstraint):
                constraints.append(constraint)

        if constraints:
            orchestrator.apply_constraints(constraints)
        else:
            # No valid constraints - optimize without
            router.mandatory_tasks = None
            router.mandatory_categories = None
            orchestrator.state.constraints = []

    else:
        # No constraints specified - optimize without
        router.mandatory_tasks = None
        router.mandatory_categories = None
        orchestrator.state.constraints = []

    # Run optimization
    for chunk in orchestrator.run_optimization():
        output_chunks.append(chunk)

    return {
        "success": True,
        "phase": orchestrator.phase.value,
        "message": "".join(output_chunks),
    }


@router.get("/workflow/{session_id}/state")
def workflow_state(session_id: str):
    """Get the current state of a workflow session."""
    orchestrator = get_orchestrator(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    state = orchestrator.get_state()

    # Get questionnaire progress if in that phase
    questionnaire_progress = None
    if orchestrator.questionnaire:
        questionnaire_progress = {
            "current": orchestrator.questionnaire.get_question_number(),
            "total": orchestrator.questionnaire.get_total_questions(),
            "is_complete": orchestrator.questionnaire.is_complete(),
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
        "constraints": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
            }
            for c in state.constraints
        ],
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
