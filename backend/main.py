"""
backend/main.py — FastAPI Application Entry Point
===================================================
OWNER: Person 6 (Backend + Integration)

WHAT THIS FILE DOES:
  1. Creates the FastAPI application
  2. Configures CORS so the frontend (running on localhost) can call our API
  3. Includes the 3 route files (student, quiz, plan)
  4. Provides a /health endpoint for quick "is the server alive?" checks

HOW TO RUN:
  From the project root (adaptive-study-planner/):
    uvicorn backend.main:app --reload --port 8000

HOW TO TEST:
  Browser:  http://127.0.0.1:8000/health
  Swagger:  http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our route files
from backend.routes import student, quiz, plan


from backend.routes import auth

# ============================================================
# CREATE THE APP
# ============================================================
# FastAPI() creates our web application.
# title/description/version appear in the Swagger docs page.

app = FastAPI(
    title="Adaptive Study Planner API",
    description="Backend for the Adaptive Study Planner & Weakness Recommender. "
                "Connects mastery analysis, weakness detection, study planning, "
                "and adaptive quiz modules.",
    version="1.0.0",
)


# ============================================================
# STARTUP EVENT: Train ML Model
# ============================================================
# Runs ONCE when the server starts.
# Trains Person 3's RandomForest and caches it in memory.
# All subsequent requests use the cached model (fast).
# If training fails, the server still starts — just returns null predictions.

@app.on_event("startup")
async def startup_event():
    print("🚀 Server starting — training ML model...")
    from backend.model_manager import initialize_model
    initialize_model()
    print("✅ Startup complete")


# ============================================================
# CORS CONFIGURATION
# ============================================================
# CORS = Cross-Origin Resource Sharing
#
# WHY WE NEED THIS:
#   The frontend (HTML/JS) runs on one address (e.g. http://127.0.0.1:5500)
#   The backend (FastAPI) runs on another (http://127.0.0.1:8000)
#   Browsers block requests between different origins by default.
#   CORS tells the browser: "these origins are allowed to call my API."
#
# WHAT EACH SETTING MEANS:
#   allow_origins  — which frontend addresses can call us
#   allow_methods  — which HTTP methods (GET, POST, etc.) are allowed
#   allow_headers  — which HTTP headers the frontend can send
#
# NOTE: We list specific origins instead of "*" (wildcard).
#   Using "*" with credentials can cause security issues.
#   For a hackathon demo, these local origins are sufficient.
#   Add more origins to this list if your frontend uses a different port.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",       # VS Code Live Server default
        "http://127.0.0.1:5500",       # Same, but IP form
        "http://localhost:3000",        # Alternative dev server
        "http://127.0.0.1:3000",
        "http://localhost:5173",        # Vite default
        "http://127.0.0.1:5173",
        "http://localhost:8080",        # Another common port
        "http://127.0.0.1:8080",
        "http://localhost:4000",        # Extra
        "http://127.0.0.1:4000",
        "null",                         # Allows fetch() from file:// (direct open)
    ],
    allow_methods=["*"],               # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],               # Allow any headers (Content-Type, etc.)
    allow_credentials=True,
)


# ============================================================
# HEALTH CHECK
# ============================================================
# INPUT:  Nothing (just a GET request)
# PROCESS: Returns a simple JSON message
# OUTPUT:  {"status": "ok", "message": "..."}
# WHY:    Quick way to verify the server is running.
#         Useful during hackathon debugging — if /health works,
#         the server is alive and the problem is elsewhere.

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "message": "Adaptive Study Planner API is running",
    }


# ============================================================
# MODEL METRICS
# ============================================================
# INPUT:  Nothing
# PROCESS: Return cached ML model evaluation metrics
# OUTPUT:  {model, accuracy, precision, recall, f1, confusion_matrix, features}
# WHY:    Judges can see the ML evaluation directly from the API.

@app.get("/model/metrics", tags=["System"])
def get_model_metrics():
    from backend.model_manager import get_model_metrics
    metrics = get_model_metrics()
    if metrics is None:
        return {
            "status": "not_ready",
            "message": "Model not trained yet or training failed",
        }
    return metrics


# ============================================================
# INCLUDE ROUTERS
# ============================================================
# Each router handles a group of related endpoints.
# This keeps main.py small and each route file focused.
#
# prefix = the URL prefix for all routes in that file
# tags   = groups endpoints in Swagger docs for readability

app.include_router(student.router, prefix="", tags=["Students"])
app.include_router(quiz.router,   prefix="", tags=["Quiz"])
app.include_router(plan.router,   prefix="", tags=["Study Plan"])
app.include_router(auth.router,   prefix="", tags=["Authentication"]
)
