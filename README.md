# Visory - Daily Planner

AI-powered daily planning assistant.

The purpose of this application is given a set of tasks you want to get done for the day plan the optimal combination - given some constraints.

There are several different components to this application :

UTILITY - 10 Questions to understand what the user values. This utility score will be used for later optimisation.

CATEGORIZATION - given the tasks the user wants to do, use an llm to categorize them in to either health, work or personal

TIME CONSTRAINTS - find out the duration of each activity along with any specific time

OTHER CUSTOM CONSRAINTS - allow user to describe other constraints

OPTIMISE/ROUTER - given the tasks and constraints optimise to the most appropriate optimizer

OPTIMIZER - a range of optimisation algorithms designed to maximise the utility of the user.

## Run Locally

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Backend runs at http://localhost:8000

### Frontend
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

  Overview

  API Routes (routes.py) → Orchestrator (orchestrator.py) → Services (categorize, constraints, optimize)

  The Workflow Phases

  The Orchestrator manages a state machine with these phases:
  QUESTIONNAIRE → EVALUATION → COLLECT_TASKS → CONSTRAINTS → CONSTRAINT_CLARIFICATION → OPTIMIZE →
  COMPLETE

  Key Interaction Points

  1. Starting a Workflow (POST /workflow/start)

  routes.py:63-74
      ↓
  get_or_create_orchestrator(session_id)  → Creates new Orchestrator instance
      ↓
  orchestrator.start()  → Returns welcome message + first questionnaire question

  2. Processing Messages (POST /workflow/message)

  routes.py:77-97
      ↓
  orchestrator.process_message(message)  → Generator that yields streaming chunks
      ↓
  Based on orchestrator.phase, calls one of:
    - _handle_questionnaire()  → Uses UtilityQuestionnaire
    - _handle_evaluation()     → Calculates utility weights
    - _handle_collect_tasks()  → Uses categorize_service
    - _handle_constraints()    → Uses constraints_service
    - _handle_optimize()       → Uses optimizer_service

  3. Services Called by Orchestrator
  Phase: QUESTIONNAIRE
  Service: UtilityQuestionnaire
  Purpose: Asks priority questions
  ────────────────────────────────────────
  Phase: COLLECT_TASKS
  Service: categorize_service
  Purpose: Categorizes tasks (work/health/personal)
  ────────────────────────────────────────
  Phase: CONSTRAINTS
  Service: constraints_service
  Purpose: Parses time/duration constraints
  ────────────────────────────────────────
  Phase: CONSTRAINT_CLARIFICATION
  Service: ConstraintClarification + get_constraint_matcher
  Purpose: Matches user constraints to tasks
  ────────────────────────────────────────
  Phase: OPTIMIZE
  Service: optimizer_service.router
  Purpose: Selects optimizer type and generates schedule
  4. Constraint Submission (POST /constraints/submit)

  routes.py:162-216
      ↓
  Either:
    - orchestrator.apply_constraints_from_text()  → Uses semantic matcher (LLM)
    - orchestrator.apply_constraints_from_ids()   → Uses button IDs directly
      ↓
  orchestrator.run_optimization()  → Calls optimizer_service

  State Flow

  PlannerState (state.py)
    ├── questionnaire_answers  ← filled by _handle_questionnaire
    ├── utility_weights        ← filled by _handle_evaluation
    ├── raw_tasks / tasks      ← filled by _handle_collect_tasks
    ├── time_window            ← filled by _handle_constraints
    ├── constraint_set         ← filled by _handle_constraint_clarification
    └── daily_plan             ← filled by _handle_optimize

  Session Management

  The orchestrator instances are stored in a module-level dict (_sessions) at orchestrator.py:338:
  - get_or_create_orchestrator() - creates new session
  - get_orchestrator() - retrieves existing session

  Each API call looks up the orchestrator by session_id and delegates to the appropriate method based on
   the current phase.



