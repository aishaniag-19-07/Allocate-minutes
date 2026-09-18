from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd
import random


router = APIRouter()


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


# ============================================================
# FIND CSV FILE
# ============================================================

def find_csv(possible_names):

    for filename in possible_names:

        path = DATA_DIR / filename

        if path.exists():
            print(f"Using CSV: {path}")
            return path

    return None


# ============================================================
# LOAD CSV
# ============================================================

def safe_read_csv(path):

    if path is None:
        return pd.DataFrame()

    try:
        return pd.read_csv(path)

    except Exception as e:

        print(
            f"WARNING: Could not read {path}: {e}"
        )

        return pd.DataFrame()


# ============================================================
# STUDENTS
# ============================================================

def load_students():

    path = find_csv([
        "student.csv",
        "students.csv",
        "student_data.csv",
        "students_data.csv",
        "user.csv",
        "users.csv"
    ])

    if path is None:

        available = [
            file.name
            for file in DATA_DIR.glob("*.csv")
        ]

        print(
            "WARNING: Student CSV not found."
        )

        print(
            "Available CSV files:",
            available
        )

        return pd.DataFrame()

    return safe_read_csv(path)


# ============================================================
# QUESTIONS
# ============================================================

def load_questions():

    path = find_csv([
        "questions.csv",
        "question.csv",
        "quiz_questions.csv",
        "quiz.csv"
    ])

    if path is None:

        print(
            "WARNING: Questions CSV not found."
        )

        return pd.DataFrame()

    return safe_read_csv(path)


# ============================================================
# ATTEMPTS
# ============================================================

def load_attempts():

    path = find_csv([
        "attempts.csv",
        "student_attempts.csv",
        "quiz_attempts.csv",
        "attempt.csv"
    ])

    if path is None:

        # Attempts are optional.
        # Quiz can still work without history.
        return pd.DataFrame()

    return safe_read_csv(path)


# ============================================================
# COLUMN FINDER
# ============================================================

def find_column(df, possible_names):

    for name in possible_names:

        if name in df.columns:
            return name

    return None


# ============================================================
# DIFFICULTY LABEL
# ============================================================

def difficulty_label(value):

    try:

        value = int(float(value))

        if value <= 2:
            return "easy"

        elif value == 3:
            return "medium"

        return "hard"

    except Exception:

        return "medium"


# ============================================================
# NORMALIZE TOPIC
# ============================================================

def normalize_topic(value):

    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


# ============================================================
# ADAPTIVE QUIZ
# ============================================================

@router.get("/student/{student_id}/quiz")
def get_quiz_question(
    student_id: str,
    topic: str = None
):

    # ========================================================
    # STEP 1
    # LOAD STUDENTS
    # ========================================================

    students = load_students()


    if students.empty:

        available = [
            file.name
            for file in DATA_DIR.glob("*.csv")
        ]

        raise HTTPException(

            status_code=500,

            detail={
                "message":
                    "Student dataset could not be found.",

                "data_folder":
                    str(DATA_DIR),

                "available_csv_files":
                    available
            }
        )


    # ========================================================
    # STEP 2
    # FIND STUDENT ID COLUMN
    # ========================================================

    student_id_column = find_column(
        students,
        [
            "student_id",
            "Student_ID",
            "StudentID",
            "studentId",
            "id",
            "ID"
        ]
    )


    if student_id_column is None:

        raise HTTPException(

            status_code=500,

            detail={
                "message":
                    "Student ID column not found.",

                "available_columns":
                    students.columns.tolist()
            }
        )


    students[student_id_column] = (
        students[student_id_column]
        .astype(str)
        .str.strip()
    )


    student_id = str(
        student_id
    ).strip()


    if (
        student_id
        not in
        students[student_id_column].values
    ):

        raise HTTPException(

            status_code=404,

            detail=(
                f"Student {student_id} "
                "not found"
            )
        )


    # ========================================================
    # STEP 3
    # LOAD QUESTIONS
    # ========================================================

    questions = load_questions()


    if questions.empty:

        available = [
            file.name
            for file in DATA_DIR.glob("*.csv")
        ]

        raise HTTPException(

            status_code=500,

            detail={
                "message":
                    "Questions dataset could not be found.",

                "available_csv_files":
                    available
            }
        )


    # ========================================================
    # STEP 4
    # DETECT QUESTION COLUMNS
    # ========================================================

    question_id_col = find_column(
        questions,
        [
            "question_id",
            "Question_ID",
            "questionId",
            "id"
        ]
    )


    topic_col = find_column(
        questions,
        [
            "topic",
            "Topic",
            "subject",
            "Subject"
        ]
    )


    difficulty_col = find_column(
        questions,
        [
            "difficulty",
            "Difficulty",
            "difficulty_level",
            "level"
        ]
    )


    question_text_col = find_column(
        questions,
        [
            "question_text",
            "question",
            "Question",
            "text"
        ]
    )


    option_a_col = find_column(
        questions,
        [
            "option_a",
            "Option_A",
            "optionA",
            "A"
        ]
    )


    option_b_col = find_column(
        questions,
        [
            "option_b",
            "Option_B",
            "optionB",
            "B"
        ]
    )


    option_c_col = find_column(
        questions,
        [
            "option_c",
            "Option_C",
            "optionC",
            "C"
        ]
    )


    option_d_col = find_column(
        questions,
        [
            "option_d",
            "Option_D",
            "optionD",
            "D"
        ]
    )


    # ========================================================
    # STEP 5
    # VALIDATE IMPORTANT COLUMNS
    # ========================================================

    missing = []


    if question_id_col is None:
        missing.append("question_id")


    if topic_col is None:
        missing.append("topic")


    if question_text_col is None:
        missing.append("question_text")


    if option_a_col is None:
        missing.append("option_a")


    if option_b_col is None:
        missing.append("option_b")


    if option_c_col is None:
        missing.append("option_c")


    if option_d_col is None:
        missing.append("option_d")


    if missing:

        raise HTTPException(

            status_code=500,

            detail={
                "message":
                    "Required question columns missing.",

                "missing":
                    missing,

                "available_columns":
                    questions.columns.tolist()
            }
        )


    # ========================================================
    # STEP 6
    # NORMALIZE TOPICS
    # ========================================================

    questions["_normalized_topic"] = (
        questions[topic_col]
        .apply(normalize_topic)
    )


    # ========================================================
    # STEP 7
    # FILTER REQUESTED TOPIC
    # ========================================================

    filtered = questions.copy()


    if topic:

        requested_topic = normalize_topic(
            topic
        )


        filtered = questions[
            questions["_normalized_topic"]
            == requested_topic
        ].copy()


        if filtered.empty:

            available_topics = (
                questions[topic_col]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )


            raise HTTPException(

                status_code=404,

                detail={
                    "message":
                        f"No questions found for {topic}",

                    "available_topics":
                        available_topics
                }
            )


    # ========================================================
    # STEP 8
    # LOAD ATTEMPT HISTORY
    # ========================================================

    attempts = load_attempts()


    asked_ids = set()

    wrong_ids = set()


    if not attempts.empty:

        attempt_student_col = find_column(
            attempts,
            [
                "student_id",
                "Student_ID",
                "StudentID"
            ]
        )


        attempt_question_col = find_column(
            attempts,
            [
                "question_id",
                "Question_ID",
                "QuestionID"
            ]
        )


        correct_col = find_column(
            attempts,
            [
                "is_correct",
                "correct",
                "Is_Correct"
            ]
        )


        if (
            attempt_student_col
            and
            attempt_question_col
        ):

            attempts[attempt_student_col] = (
                attempts[attempt_student_col]
                .astype(str)
                .str.strip()
            )


            student_attempts = attempts[
                attempts[attempt_student_col]
                == student_id
            ].copy()


            asked_ids = set(

                student_attempts[
                    attempt_question_col
                ]
                .astype(str)
                .tolist()

            )


            if correct_col:

                incorrect_mask = (

                    student_attempts[
                        correct_col
                    ]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .isin([
                        "0",
                        "false",
                        "no",
                        "wrong"
                    ])

                )


                wrong_ids = set(

                    student_attempts.loc[
                        incorrect_mask,
                        attempt_question_col
                    ]
                    .astype(str)
                    .tolist()

                )


    # ========================================================
    # STEP 9
    # CONVERT QUESTIONS
    # ========================================================

    question_list = filtered.to_dict(
        orient="records"
    )


    # ========================================================
    # STEP 10
    # UNSEEN QUESTIONS
    # ========================================================

    unseen = [

        q

        for q in question_list

        if str(
            q.get(
                question_id_col
            )
        )
        not in asked_ids

    ]


    # ========================================================
    # STEP 11
    # PREVIOUSLY WRONG QUESTIONS
    # ========================================================

    wrong = [

        q

        for q in question_list

        if str(
            q.get(
                question_id_col
            )
        )
        in wrong_ids

    ]


    # ========================================================
    # STEP 12
    # ADAPTIVE SELECTION
    # ========================================================

    if unseen:

        question = random.choice(
            unseen
        )

        selection_reason = (
            "unseen_question"
        )


    elif wrong:

        question = random.choice(
            wrong
        )

        selection_reason = (
            "previously_wrong"
        )


    elif question_list:

        question = random.choice(
            question_list
        )

        selection_reason = (
            "review_question"
        )


    else:

        raise HTTPException(

            status_code=404,

            detail=(
                "No questions available"
            )
        )


    # ========================================================
    # STEP 13
    # DIFFICULTY
    # ========================================================

    if difficulty_col:

        try:

            difficulty = int(
                float(
                    question.get(
                        difficulty_col,
                        3
                    )
                )
            )

        except Exception:

            difficulty = 3

    else:

        difficulty = 3


    diff_label = difficulty_label(
        difficulty
    )


    # ========================================================
    # STEP 14
    # RESPONSE
    # ========================================================

    response = {

        "question_id":
            str(
                question.get(
                    question_id_col
                )
            ),

        "topic":
            str(
                question.get(
                    topic_col
                )
            ),

        "difficulty":
            difficulty,

        "difficulty_label":
            diff_label,

        "question_text":
            str(
                question.get(
                    question_text_col
                )
            ),

        "options": {

            "a":
                str(
                    question.get(
                        option_a_col,
                        ""
                    )
                ),

            "b":
                str(
                    question.get(
                        option_b_col,
                        ""
                    )
                ),

            "c":
                str(
                    question.get(
                        option_c_col,
                        ""
                    )
                ),

            "d":
                str(
                    question.get(
                        option_d_col,
                        ""
                    )
                )

        },

        "selection_reason":
            selection_reason
    }


    return response

# ============================================================
# SUBMIT QUIZ ANSWER
# ============================================================

from pydantic import BaseModel


class QuizSubmission(BaseModel):
    student_id: str
    question_id: str
    selected_option: str
    time_taken_seconds: int = 1


@router.post("/quiz/submit")
def submit_quiz_answer(submission: QuizSubmission):
    questions = load_questions()

    if questions.empty:
        raise HTTPException(
            status_code=500,
            detail="Questions dataset could not be loaded."
        )

    question_id_col = find_column(
        questions,
        ["question_id", "Question_ID", "questionId", "id"]
    )
    correct_col = find_column(
        questions,
        [
            "correct_option", "Correct_Option",
            "correct_answer", "Correct_Answer",
            "answer", "Answer"
        ]
    )
    topic_col = find_column(
        questions,
        ["topic", "Topic", "subject", "Subject"]
    )

    if question_id_col is None:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "question_id column not found",
                "available_columns": questions.columns.tolist()
            }
        )

    if correct_col is None:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Correct answer column not found",
                "available_columns": questions.columns.tolist()
            }
        )

    questions[question_id_col] = (
        questions[question_id_col].astype(str).str.strip()
    )
    question_id = str(submission.question_id).strip()
    matched = questions[questions[question_id_col] == question_id]

    if matched.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Question {question_id} not found"
        )

    question = matched.iloc[0]
    correct_option = (
        str(question[correct_col])
        .strip()
        .lower()
        .replace("option_", "")
        .replace("option ", "")
    )
    selected_option = str(submission.selected_option).strip().lower()
    is_correct = selected_option == correct_option
    topic = str(question[topic_col]) if topic_col else "Unknown"

    # Score the topic before saving this answer.
    from backend.data_loader import load_clean_attempts, save_attempt, refresh_clean_attempts
    from backend.mastery import calculate_mastery
    from backend.model_manager import get_model, get_time_fallback

    before_df = load_clean_attempts()
    before_mastery = calculate_mastery(before_df, submission.student_id)["mastery"].get(topic, 0.0)
    difficulty = question.get("difficulty", 1)
    try:
        difficulty = int(float(difficulty))
    except (ValueError, TypeError):
        difficulty = 1

    attempt_record = {
        "student_id": submission.student_id,
        "question_id": question_id,
        "topic": topic,
        "difficulty": difficulty,
        "selected_option": selected_option,
        "is_correct": int(is_correct),
        "time_taken_seconds": max(1, submission.time_taken_seconds),
    }

    try:
        attempt_id = save_attempt(attempt_record)
        after_df = refresh_clean_attempts()
        after_mastery = calculate_mastery(after_df, submission.student_id)["mastery"].get(topic, 0.0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not update quiz results: {e}") from e

    predicted_success = None
    model = get_model()
    if model is not None:
        try:
            from backend.predictor import build_features, apply_time_imputer, predict_for_candidate
            features = apply_time_imputer(build_features(after_df), get_time_fallback())
            predicted_success = predict_for_candidate(
                model, features, submission.student_id, topic, difficulty, get_time_fallback()
            )
        except Exception as e:
            print(f"WARNING: Could not calculate ML prediction: {e}")

    attempt_record["attempt_id"] = attempt_id

    # Response shape matches frontend/quiz.js.
    return {
        "correct": is_correct,
        "answer": {
            "selected": selected_option,
            "correct": correct_option
        },
        "before": {"mastery": before_mastery},
        "after": {
            "mastery": after_mastery,
            "predicted_success": predicted_success
        },
        "weakness": {
            "reasons": [] if is_correct else ["incorrect_answer"],
            "repeated_question_errors": 0,
            "wrong_streak": 0 if is_correct else 1
        },
        "attempt": attempt_record
    }
