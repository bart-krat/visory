# Architecture - Visory Daily Planner

## What We're Building
A daily planning assistant where users input tasks, an LLM clarifies time constraints and task complexity through conversation, a semantic categorizer classifies tasks by type, then a heuristic optimizer generates an optimized time-blocked schedule for their day.

**Core Flow:** Tasks → Categorizer (semantic similarity) → LLM Chat (clarify time window + details) → Optimizer → Calendar View

## Tech Stack
**Frontend:** React + Vite + TypeScript
**Backend:** FastAPI (Python)
**LLM:** OpenAI GPT-4 (chat) + OpenAI Embeddings (categorization)
**Database:** Mock persistence layer (Neo4j-ready interface for future)
**Deployment:** Local development (Docker-ready structure)

**Rationale:** React/FastAPI gives rapid iteration. TypeScript catches errors early. OpenAI embeddings provide simple semantic similarity without custom ML. Mock DB layer lets us build optimizer learning later without refactoring.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Task Input  │→ │ Chat View   │→ │ Calendar View       │  │
│  │ (raw tasks) │  │ (clarify)   │  │ (time-blocked plan) │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────┐
│                        BACKEND                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Categorizer │→ │ Chat Service│→ │ Task Processor      │  │
│  │ (embeddings)│  │ (OpenAI)    │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────┬───────────┘  │
│                                              │               │
│                                    ┌─────────▼─────────┐    │
│                                    │ Optimizer         │    │
│                                    │ (heuristic sched) │    │
│                                    └─────────┬─────────┘    │
│                                              │               │
│                                    ┌─────────▼─────────┐    │
│                                    │ Mock DB Layer     │    │
│                                    │ (Neo4j interface) │    │
│                                    └───────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

- **Task Input:** User enters raw task list
- **Categorizer:** Semantic similarity using embeddings to classify task types
- **Chat Service:** LLM-powered conversation to clarify time window and task details
- **Task Processor:** Structures clarified data into optimizer-ready format
- **Optimizer:** Heuristic algorithm to schedule tasks into time blocks
- **Calendar View:** Visual time-blocked daily schedule
- **Mock DB:** Persistence interface (stores plans for future learning feature)

## File Structure
```
visory/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TaskInput.tsx        # Raw task entry
│   │   │   ├── ChatView.tsx         # LLM clarification chat
│   │   │   └── CalendarView.tsx     # Time-blocked schedule display
│   │   ├── hooks/
│   │   │   └── useApi.ts            # Backend communication
│   │   ├── types/
│   │   │   └── index.ts             # Shared types
│   │   ├── App.tsx                  # Main app with step flow
│   │   └── main.tsx                 # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── routers/
│   │   │   ├── chat.py              # Chat/clarification endpoints
│   │   │   ├── tasks.py             # Task processing endpoints
│   │   │   └── schedule.py          # Optimizer/schedule endpoints
│   │   ├── services/
│   │   │   ├── llm_service.py       # OpenAI chat integration
│   │   │   ├── categorizer.py       # Semantic similarity categorization
│   │   │   ├── task_processor.py    # Task structuring logic
│   │   │   └── optimizer.py         # Heuristic scheduling algorithm
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic models
│   │   └── db/
│   │       └── mock_db.py           # Mock persistence (Neo4j interface)
│   ├── requirements.txt
│   └── .env.example
│
├── _coordination/
│   └── ARCHITECTURE.md
└── README.md
```

## Feature Roadmap (Priority Order)

### Phase 1 - Bootstrap (Get it running)
1. **Basic task input UI** - Text area to enter tasks (one per line)
2. **Task categorizer** - Semantic similarity to classify task types (work, personal, health, errands, etc.)
3. **Chat endpoint + UI** - LLM clarifies time window and task durations
4. **Simple optimizer** - Greedy scheduling algorithm (fit tasks into time slots)
5. **Calendar display** - Show time-blocked schedule

### Phase 2 - Core Functionality (Rounds 2-4)
6. **Improved clarification flow** - Better prompts, handle edge cases
7. **Smarter optimizer** - Priority weighting, energy levels, break times
8. **Plan editing** - Drag/drop to adjust schedule manually
9. **Mock DB integration** - Store completed plans

### Phase 3 - Production Hardening (Rounds 5+)
10. **Neo4j integration** - Replace mock with real graph DB
11. **Optimizer learning** - Use historical data to improve suggestions
12. **Error handling & validation** - Robust input handling
13. **Authentication** - User accounts and plan history

## Production Considerations

**Security:** API key management via environment variables. Input sanitization on task text. Rate limiting on LLM calls.

**Error Handling:** Graceful degradation if LLM fails (manual time entry fallback). Validation on all inputs.

**Logging:** Log LLM interactions (for debugging prompts). Log optimizer decisions (for future learning).

**Performance:** Cache embeddings for common task phrases. Streaming for chat responses.

Note: Basic versions implemented early, enhanced as we go.

## Data Model

```python
# Core entities

class TaskCategory:
    name: str                  # "work", "personal", "health", "errands", "learning"
    embedding: list[float]     # Pre-computed category embedding

class Task:
    id: str
    raw_text: str              # Original user input
    clarified_name: str        # LLM-refined name
    duration_minutes: int      # Estimated time
    complexity: str            # "low", "medium", "high"
    category: TaskCategory     # Semantic similarity match
    confidence: float          # Category match confidence (0-1)

class TimeWindow:
    start_time: datetime       # Day start (e.g., 9:00 AM)
    end_time: datetime         # Day end (e.g., 6:00 PM)
    breaks: list[tuple]        # [(12:00, 13:00)] for lunch

class ScheduledTask:
    task: Task
    start_time: datetime
    end_time: datetime

class DayPlan:
    id: str
    created_at: datetime
    time_window: TimeWindow
    tasks: list[Task]
    schedule: list[ScheduledTask]
```

## API Design

```
POST /api/tasks/categorize
  Body: { tasks: string[] }
  Response: { categorized_tasks: [{raw_text, category, confidence}] }

POST /api/chat/start
  Body: { categorized_tasks: Task[] }
  Response: { session_id, message, needs_clarification: bool }

POST /api/chat/message
  Body: { session_id, user_message }
  Response: { message, clarification_complete: bool, clarified_tasks?: Task[] }

POST /api/schedule/generate
  Body: { session_id, time_window: TimeWindow }
  Response: { schedule: ScheduledTask[] }

POST /api/schedule/save
  Body: { plan: DayPlan }
  Response: { plan_id }

GET /api/schedule/{plan_id}
  Response: { plan: DayPlan }
```

## Categorizer Algorithm

```
Predefined categories with example phrases:
- work: ["meeting", "email", "report", "presentation", "call with client"]
- personal: ["call mom", "birthday gift", "plan weekend"]
- health: ["gym", "doctor", "medication", "walk", "yoga"]
- errands: ["groceries", "bank", "post office", "pick up"]
- learning: ["study", "read", "course", "practice", "tutorial"]

Algorithm:
1. Pre-compute embeddings for all category example phrases
2. For each user task:
   - Generate embedding using OpenAI text-embedding-3-small
   - Compute cosine similarity against all category embeddings
   - Assign category with highest similarity
   - Store confidence score
3. Return categorized tasks (user can override in UI if needed)
```

## Optimizer Algorithm (Initial Heuristic)

```
1. Group tasks by category
2. Sort within groups by: complexity (high first for morning energy), then duration
3. Interleave categories to provide variety (avoid 4 work tasks in a row)
4. Start at time_window.start_time
5. For each task:
   - If current_time + duration fits before next break/end: schedule it
   - Add 5-min buffer between tasks
   - Skip break periods
6. Return scheduled tasks (may have unscheduled tasks if time runs out)
```

Future: Learn from user adjustments to improve initial scheduling.
