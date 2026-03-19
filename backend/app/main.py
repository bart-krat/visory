import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.routes import router

load_dotenv()

app = FastAPI(title="Visory Daily Planner")

# CORS: local dev + production deployment
origins = [
    "http://localhost:5173",  # Vite dev
    "http://localhost:3000",
]

# Add production URL if set (supports comma-separated list)
if prod_url := os.getenv("FRONTEND_URL"):
    for url in prod_url.split(","):
        url = url.strip()
        if url:
            origins.append(url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
