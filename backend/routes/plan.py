"""
backend/routes/plan.py — Study Plan API endpoint
==================================================
OWNER: Person 6 (Backend + Integration)

ENDPOINTS:
  GET /student/{student_id}/plan — Personalized study plan (Person 3's planner)

INTEGRATION STATUS:
  ✅ Person 3's planner.py — build_student_plan() connected
  ✅ Person 2's mastery/weakness used internally by planner
"""

from fastapi import APIRouter, HTTPException
from backend.data_loader import load_students, load_clean_attempts
from backend.planner import build_student_plan

router = APIRouter()


# ============================================================
# GET /student/{student_id}/plan
# ============================================================
# INPUT:   student_id
# PROCESS:
#   Calls Person 3's build_student_plan() which:
#     1. Gets student's available_minutes from students.csv
#     2. Calls Person 2's analyze_student() for mastery + weak topics
#     3. Runs Person 3's generate_study_plan() to allocate time
# OUTPUT:  {student_id, available_minutes, plan: [...]}

@router.get("/student/{student_id}/plan")
def get_study_plan(student_id: str):
    students = load_students()
    if students.empty or student_id not in students["student_id"].values:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    clean_df = load_clean_attempts()
    if clean_df.empty:
        return {
            "student_id": student_id,
            "available_minutes": 0,
            "plan": [],
            "message": "clean_attempts.csv is missing — no history to plan from",
        }

    try:
        # Person 3's full planner — handles everything internally
        result = build_student_plan(clean_df, students, student_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Planner error: {str(e)}"
        )

    return {
        "student_id": result["student_id"],
        "name": result.get("name", ""),
        "available_minutes": result.get("available_minutes", 0),
        "plan": result.get("plan", []),
        "weak_topics_summary": [
            {
                "topic": t["topic"],
                "mastery": t.get("mastery"),
                "priority": t.get("priority"),
                "severity": t.get("severity"),
                "reasons": t.get("reasons", []),
            }
            for t in result.get("weak_topics", [])
        ],
        "warning": result.get("warning"),
    }
