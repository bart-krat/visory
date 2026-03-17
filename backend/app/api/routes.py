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
    """Categorize tasks into work, health, or leisure."""
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


@router.get("/workflow/{session_id}/state")
def workflow_state(session_id: str):
    """Get the current state of a workflow session."""
    orchestrator = get_orchestrator(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")

    state = orchestrator.get_state()
    return {
        "phase": orchestrator.get_phase().value,
        "raw_tasks": state.raw_tasks,
        "categorized_tasks": [
            {"task": t.task, "category": t.category}
            for t in state.categorized_tasks
        ],
        "tasks_with_duration": [
            {"task": t.task, "category": t.category, "duration_minutes": t.duration_minutes}
            for t in state.tasks_with_duration
        ] if state.tasks_with_duration else [],
        "time_window": {
            "start_time": state.time_window.start_time,
            "end_time": state.time_window.end_time,
        } if state.time_window else None,
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
