# Bootstrap Build

## Created

### Backend (`/backend`)
- `app/main.py` - FastAPI entry point with CORS
- `app/api/routes.py` - API endpoints
- `app/api/schemas.py` - Pydantic models
- `app/orchestrator.py` - Pipeline coordinator (placeholder)
- `app/categorize/` - Semantic categorization (placeholder)
- `app/constraints/` - LLM constraint clarification (placeholder)
- `app/optimize/` - Scheduling optimizer (placeholder)

### Frontend (`/frontend`)
- `src/App.tsx` - Main app
- `src/components/ChatView.tsx` - Chat interface
- Vite + React + TypeScript setup

## Run Commands

**Backend:**
```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend && npm install && npm run dev
```

## Status: READY TO RUN
