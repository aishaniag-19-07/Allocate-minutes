"""
backend/routes/student.py — Student-related API endpoints
==========================================================
OWNER: Person 6 (Backend + Integration)

ENDPOINTS:
  GET /students                        — List all students from CSV
  GET /student/{student_id}/mastery    — Topic mastery (Person 2's engine)
  GET /student/{student_id}/weaknesses — Weak topics with reasons (Person 2's engine)

INTEGRATION STATUS:
  ✅ Person 2's mastery.py connected
  ✅ Person 2's mistakes.py connected (via dependencies.analyze_student)
  ✅ Person 2's dependencies.py connected
"""

from fastapi import APIRouter, HTTPException
from backend.data_loader import load_students, load_clean_attempts
from backend.dependencies import analyze_student

router = APIRouter()


# ============================================================
# GET /students
# ============================================================
# INPUT:   Nothing
# PROCESS: Reads data/students.csv, returns id + name + exam_goal
# OUTPUT:  List of student objects
# WHY:     Frontend needs a student selector dropdown

@router.get("/students")
def get_all_students():
    students = load_students()

    if students.empty:
        raise HTTPException(status_code=500, detail="students.csv is missing or empty")

    return [
        {
            "student_id": row["student_id"],
            "name": row["name"],
            "grade": int(row["grade"]),
            "exam_goal": row["exam_goal"],
            "available_minutes_per_day": int(row["available_minutes_per_day"]),
        }
        for _, row in students.iterrows()
    ]


# ============================================================
# HELPER: Run Person 2's full diagnosis pipeline
# ============================================================
# INPUT:   student_id
# PROCESS:
#   1. Load clean_attempts.csv (Person 1's preprocessed data)
#   2. Call dependencies.analyze_student() which internally calls:
#      - mastery.calculate_mastery()   → weighted mastery scores
#      - mistakes.analyze_weaknesses() → weak topics with reasons
#      - dependencies.analyze_dependencies() → prerequisite analysis
#   3. Return the combined result
# OUTPUT:  dict with {student_id, mastery, weak_topics, warning?}
#
# WHY ONE HELPER?
#   Person 2 designed analyze_student() as the single entry point.
#   Calling it once gives us mastery + weaknesses + dependencies together,
#   avoiding redundant CSV loads and duplicate calculations.

def _run_diagnosis(student_id: str) -> dict:
    """Run Person 2's full mastery → weakness → dependency pipeline."""
    clean_df = load_clean_attempts()
    if clean_df.empty:
        return {
            "student_id": student_id,
            "mastery": {},
            "weak_topics": [],
            "warning": "clean_attempts.csv is missing or empty",
        }
    return analyze_student(clean_df, student_id)


# ============================================================
# GET /student/{student_id}/mastery
# ============================================================
# INPUT:   student_id from URL
# PROCESS: Verify student exists → run Person 2's mastery engine
# OUTPUT:  {student_id, overall_mastery, topics: [...]}

@router.get("/student/{student_id}/mastery")
def get_student_mastery(student_id: str):
    # Verify student exists
    students = load_students()
    if students.empty or student_id not in students["student_id"].values:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    diagnosis = _run_diagnosis(student_id)
    mastery_dict = diagnosis.get("mastery", {})

    # Convert Person 2's {topic: score} dict to list format for frontend
    topics = []
    for topic, score in mastery_dict.items():
        if score >= 70:
            status = "strong"
        elif score >= 40:
            status = "developing"
        else:
            status = "weak"

        topics.append({
            "topic": topic,
            "mastery": score,
            "status": status,
        })

    # Sort: weakest first
    topics.sort(key=lambda t: t["mastery"])

    # Overall mastery = average
    overall = round(sum(t["mastery"] for t in topics) / len(topics), 1) if topics else 0

    result = {
        "student_id": student_id,
        "overall_mastery": overall,
        "topics": topics,
    }
    if "warning" in diagnosis:
        result["warning"] = diagnosis["warning"]

    return result


# ============================================================
# GET /student/{student_id}/weaknesses
# ============================================================
# INPUT:   student_id
# PROCESS: Run Person 2's full pipeline → return weak topics with
#          reasons, mistake patterns, prerequisites, root causes
# OUTPUT:  {student_id, weaknesses: [...]}

@router.get("/student/{student_id}/weaknesses")
def get_student_weaknesses(student_id: str):
    students = load_students()
    if students.empty or student_id not in students["student_id"].values:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    diagnosis = _run_diagnosis(student_id)
    weak_topics = diagnosis.get("weak_topics", [])

    result = {
        "student_id": student_id,
        "weaknesses": weak_topics,
    }
    if "warning" in diagnosis:
        result["warning"] = diagnosis["warning"]

    return result
