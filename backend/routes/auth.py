from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.data_loader import load_students


router = APIRouter()


class LoginRequest(BaseModel):
    gmail_id: str
    pin: str


@router.post("/auth/login")
def login(request: LoginRequest):

    students = load_students()

    if students.empty:
        raise HTTPException(
            status_code=500,
            detail="Student data not available"
        )

    email = request.gmail_id.strip().lower()
    pin = request.pin.strip()

    students["gmail_id"] = (
        students["gmail_id"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    students["PIN"] = (
        students["PIN"]
        .astype(str)
        .str.strip()
    )

    match = students[
        (students["gmail_id"] == email)
        & (students["PIN"] == pin)
    ]

    if match.empty:
        raise HTTPException(
            status_code=401,
            detail="Invalid Gmail ID or PIN"
        )

    student = match.iloc[0]

    return {
        "student_id": student["student_id"],
        "name": student["name"],
        "grade": int(student["grade"]),
        "exam_goal": student["exam_goal"],
        "available_minutes_per_day":
            int(student["available_minutes_per_day"])
    }