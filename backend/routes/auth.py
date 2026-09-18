from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import pandas as pd
import uuid

from backend.data_loader import load_students


router = APIRouter()


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


def get_student_csv_path():

    possible_files = [
        "student.csv",
        "students.csv",
        "student_data.csv",
        "students_data.csv",
        "user.csv",
        "users.csv"
    ]

    for filename in possible_files:

        path = DATA_DIR / filename

        if path.exists():
            return path

    raise HTTPException(
        status_code=500,
        detail="Student CSV file not found"
    )


# ============================================================
# LOGIN MODEL
# ============================================================

class LoginRequest(BaseModel):
    gmail_id: str
    pin: str


# ============================================================
# SIGNUP MODEL
# ============================================================

class SignupRequest(BaseModel):
    name: str
    gmail_id: str
    username: str
    pin: str
    grade: str
    exam_goal: str
    available_minutes_per_day: int


# ============================================================
# LOGIN
# ============================================================

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
        "student_id": str(student["student_id"]),
        "name": str(student["name"]),
        "grade": int(student["grade"]),
        "exam_goal": str(student["exam_goal"]),
        "available_minutes_per_day":
            int(student["available_minutes_per_day"])
    }


# ============================================================
# SIGNUP
# ============================================================

@router.post("/auth/signup")
def signup(request: SignupRequest):

    students = load_students()

    if students.empty:
        raise HTTPException(
            status_code=500,
            detail="Student data not available"
        )

    email = request.gmail_id.strip().lower()
    username = request.username.strip()

    # --------------------------------------------------------
    # CHECK EMAIL
    # --------------------------------------------------------

    existing_emails = (
        students["gmail_id"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    if email in existing_emails.values:

        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )

    # --------------------------------------------------------
    # CHECK USERNAME IF COLUMN EXISTS
    # --------------------------------------------------------

    if "username" in students.columns:

        existing_usernames = (
            students["username"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        if username.lower() in existing_usernames.values:

            raise HTTPException(
                status_code=409,
                detail="Username already exists"
            )

    # --------------------------------------------------------
    # GENERATE STUDENT ID
    # --------------------------------------------------------

    student_id = "S" + str(uuid.uuid4().int)[:6]

    # --------------------------------------------------------
    # CREATE STUDENT
    # --------------------------------------------------------

    new_student = {}

    # Fill every existing CSV column
    for column in students.columns:
        new_student[column] = ""

    # Required student information
    new_student["student_id"] = student_id
    new_student["name"] = request.name.strip()
    new_student["gmail_id"] = email
    new_student["PIN"] = request.pin.strip()
    new_student["grade"] = request.grade
    new_student["exam_goal"] = request.exam_goal.strip()
    new_student["available_minutes_per_day"] = (
        request.available_minutes_per_day
    )

    if "username" in students.columns:
        new_student["username"] = username

    # --------------------------------------------------------
    # ADD TO DATAFRAME
    # --------------------------------------------------------

    new_row = pd.DataFrame([new_student])

    updated_students = pd.concat(
        [students, new_row],
        ignore_index=True
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    csv_path = get_student_csv_path()

    updated_students.to_csv(
        csv_path,
        index=False
    )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": "Student registered successfully",
        "student": {
            "student_id": student_id,
            "name": request.name.strip(),
            "gmail_id": email,
            "username": username,
            "grade": request.grade,
            "exam_goal": request.exam_goal.strip(),
            "available_minutes_per_day":
                request.available_minutes_per_day
        }
    }