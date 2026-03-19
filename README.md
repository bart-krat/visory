# Visory - Daily Planner

AI-powered daily planning assistant.

**OVERVIEW**

The purpose of this application is that most calendar app allow to schedule tasks, however there is either limited rigid optimisation and no personalisation. The aim here is that the user will first answer some questions so that the AI can understand where their values lay. Then once these values are weighted the user can start planning their day. The three value categories are Health, Work and Personal.

The first request is for the user to list all the tasks they want to get done in the day. 

Then the user will be asked for the various time constraints for these tasks : duration, whether there are fixed times and what window we have to play with.

Next the user will be asked if they have any other constraints to describe. The system is mainly designed to handle positioning and order constraints ie. Go to the beach after a run. Do work activities in afternoon etc. However being an AI powered app there is fall back to handle more ambiguous constraints it just may not guarantee an optimal plan!

Then the algorithm will run and the AI will return a schedule for the day. The user then has an option to go back and edit some of their constraints or change the tasks they want to get done.

## Run Locally

### Backend
FASTAPI
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Backend runs at http://localhost:8000

### Frontend
REACT
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at http://localhost:5173

## Health Check
```bash
curl http://localhost:8000/health
```

**OVERALL WORKFLOW BACKEND**

⏺ Orchestrator.py Walkthrough

  Overview

  The Orchestrator is the central controller that manages the planning workflow. It coordinates between
  4 sub-modules:

  ┌─────────────────────────────────────────────────────────────────┐
  │                        ORCHESTRATOR                              │
  │                                                                  │
  │  Manages workflow phases and calls sub-modules in sequence       │
  └─────────────────────────────────────────────────────────────────┘
           │              │                │              │
           ▼              ▼                ▼              ▼
     ┌──────────┐  ┌─────────────┐  ┌───────────┐  ┌──────────┐
     │CATEGORIZE│  │ CONSTRAINTS │  │  OPTIMIZE │  │ RESULTS  │
     │ SERVICE  │  │   MATCHER   │  │  SERVICE  │  │ SERVICE  │
     └──────────┘  └─────────────┘  └───────────┘  └──────────┘

  ---
  Workflow Phases

  WELCOME → COLLECT_TASKS → CONSTRAINTS → CONSTRAINT_CLARIFICATION → OPTIMIZE → COMPLETE
              │                                                          │
              └──── (optional QUESTIONNAIRE before COLLECT_TASKS) ───────┘

  ---
  Initialization (Lines 58-69)

  def __init__(self, session_id: str = ""):
      self.state = PlannerState(session_id=session_id)      # Holds all session data
      self.phase = WorkflowPhase.WELCOME                     # Current phase
      self.categorize_service = get_categorize_service()     # → app/categorize/
      self.optimizer_service = get_optimizer_service()       # → app/optimize/
      self.results_service = get_results_service()           # → app/results/
      self.constraint_set = ConstraintSet()                  # → app/state.py

  ---
  Phase 1: COLLECT_TASKS (Lines 126-146)

  User input: "gym, meeting, lunch, read book"

  def _handle_collect_tasks(self, user_message: str):
      # 1. Parse raw text into task list
      raw_tasks = self._parse_tasks_from_message(user_message)
      # → ["gym", "meeting", "lunch", "read book"]

      # 2. CALLS CATEGORIZE SERVICE
      self.state.tasks = self.categorize_service.categorize(
          raw_tasks,
          utility_weights=self.state.utility_weights,
      )
      # → Returns list of Task objects with category, utility, duration

      # 3. Transition to CONSTRAINTS phase
      self.phase = WorkflowPhase.CONSTRAINTS

  Module called: app/categorize/ → Uses LLM to classify tasks into health/work/personal

  ---
  Phase 2: CONSTRAINTS (UI Phase)

  User sets durations and time window via the frontend UI. No orchestrator code runs here - it's handled
   by API routes that update self.state.tasks and self.state.time_window.

  ---
  Phase 3: CONSTRAINT_CLARIFICATION (Lines 149-168)

  User input: "gym before lunch, meeting at 2pm"

  def _handle_constraint_clarification(self, user_message: str):
      # 1. CALLS CONSTRAINT MATCHER (LLM-based)
      matcher = get_constraint_matcher(self.state.tasks)
      self.constraint_set = matcher.match(user_message)
      # → Returns ConstraintSet with:
      #   - OrderedAfter("lunch", after_task="gym")
      #   - FixedTimeSlot("meeting", start_time=840)

      # 2. Add any fixed times from the task table
      self._add_fixed_time_slots_to_constraints()

      # 3. Move to OPTIMIZE phase
      self.phase = WorkflowPhase.OPTIMIZE
      yield from self._handle_optimize()

  Module called: app/constraints/matcher.py → Uses LLM to parse natural language into typed constraints

  ---
  Phase 4: OPTIMIZE (Lines 234-283)

  def _handle_optimize(self):
      yield "Creating your optimized schedule...\n\n"

      # 1. CALLS OPTIMIZER SERVICE
      router = self.optimizer_service.router
      daily_plan, optimizer_type, fallback_used = router.optimize(
          self.state.tasks,           # List of Task objects
          self.state.time_window,     # TimeWindow (start/end)
          constraints=self.constraint_set,  # ConstraintSet
      )
      # → Router auto-selects optimizer:
      #   - SIMPLE: tasks fit, no constraints
      #   - GREEDY: tasks overflow, no constraints
      #   - KNAPSACK: mandatory tasks/categories
      #   - ENUMERATION: complex constraints (ordering, fixed times)
      #   - LLM: ambiguous constraints or fallback

      # 2. CALLS RESULTS SERVICE
      ai_summary = self.results_service.summarize_results(
          daily_plan=daily_plan,
          all_tasks=self.state.tasks,
          constraint_set=self.constraint_set,
          optimizer_type=self.state.optimizer_type,
          fallback_used=fallback_used,
      )
      # → Returns validation message:
      #   - "✅ All constraints satisfied"
      #   - "⚠️ Constraints Not Met: ..."
      #   - "📋 Tasks Not Scheduled: ..."

      # 3. Format and return schedule
      schedule_text = self._format_schedule(daily_plan)
      yield schedule_text

  Modules called:
  - app/optimize/router.py → Selects and runs the appropriate optimizer
  - app/results/service.py → Validates constraints and explains results

  ---
  Data Flow Summary

  User: "gym, meeting, lunch"
          │
          ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ _handle_collect_tasks()                                       │
  │   └── categorize_service.categorize()                        │
  │         └── Returns: [Task(gym, health), Task(meeting, work)]│
  └──────────────────────────────────────────────────────────────┘
          │
          ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ UI: User sets durations (30min, 60min) + time window (9-5)   │
  └──────────────────────────────────────────────────────────────┘
          │
          ▼
  User: "gym before lunch"
          │
          ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ _handle_constraint_clarification()                            │
  │   └── constraint_matcher.match()                             │
  │         └── Returns: ConstraintSet(OrderedAfter, ...)        │
  └──────────────────────────────────────────────────────────────┘
          │
          ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ _handle_optimize()                                            │
  │   ├── optimizer_service.router.optimize()                    │
  │   │     └── Returns: DailyPlan(schedule=[...])               │
  │   └── results_service.summarize_results()                    │
  │         └── Returns: "✅ All constraints satisfied"          │
  └──────────────────────────────────────────────────────────────┘
          │
          ▼
  Output: Formatted schedule with times

  ---
  Session Management (Lines 326-339)

  _sessions: dict[str, Orchestrator] = {}

  def get_or_create_orchestrator(session_id: str) -> Orchestrator:
      """Each user session gets its own Orchestrator instance."""
      if session_id not in _sessions:
          _sessions[session_id] = Orchestrator(session_id=session_id)
      return _sessions[session_id]

  API routes call get_or_create_orchestrator(session_id) to get the right instance for each user.


**ARCHITECTURE**

For scalability, maintainbility and independence I have gone for a microservice architecture in the backend with an orchestrator file to bring it all together. 


**TESTS**
As can be seen in the tests directory all services can be tested independently as well as an end to end test that uses playwrigt code to run through the full application.



**EVALS**
There are 4 different AI (LLM) components that have evals set run against in this system:

Utility Questionnaire - psychometric test to understand user values and provide weights 
Categorizer - Map the activities to the value categories ( Health, Work, Personal)
Matcher - Take user's custom constraint description and try to match to parameterized constraints for the optimizer algorithms
LLM_OPTIMIZER - Fall back optimizer when users constraints are ambiguous or constraints mean primary optimizer algorithms cant find solution

To ensure accuracy run evals sets against all of these including other Optimizer Algorithms ( programmatic)



