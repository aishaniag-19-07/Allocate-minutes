"""
adaptive.py
Owner: Person 3

REAL-DATA VERSION
-----------------
Chooses the next quiz question using:
    1. the previous answer (correct / incorrect)
    2. the real 1-5 difficulty scale from Person 1
    3. Person 2's weak-topic output
    4. the real questions.csv question bank

Person 2's dependency/prerequisite analysis is NOT duplicated here.
The weak_topics objects are accepted as-is so the module can plug into
analyze_student() later.
"""

import pandas as pd

DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 5


# ---------------------------------------------------------------------------
# Difficulty logic
# ---------------------------------------------------------------------------

def get_difficulty_index(difficulty):
    """Return the zero-based index of a real numeric difficulty 1-5."""
    try:
        difficulty = int(difficulty)
    except (TypeError, ValueError):
        difficulty = 3

    difficulty = max(DIFFICULTY_MIN, min(DIFFICULTY_MAX, difficulty))
    return difficulty - DIFFICULTY_MIN


def adjust_difficulty(current_difficulty, correct):
    """
    Move one level harder after a correct answer and one level easier after
    an incorrect answer, while clamping to the real 1-5 range.
    """
    current_index = get_difficulty_index(current_difficulty)

    if bool(correct):
        next_index = min(current_index + 1, DIFFICULTY_MAX - DIFFICULTY_MIN)
    else:
        next_index = max(current_index - 1, 0)

    return next_index + DIFFICULTY_MIN


# ---------------------------------------------------------------------------
# Weak-topic + question selection
# ---------------------------------------------------------------------------

def _topic_name(weak_topic):
    """Accept both Person 2 dicts and simple topic strings."""
    if isinstance(weak_topic, dict):
        return weak_topic.get("topic")
    return weak_topic


def _question_to_dict(question):
    """Normalize a Pandas row/dict/list entry to a plain dict."""
    if isinstance(question, dict):
        return question
    if isinstance(question, pd.Series):
        return question.to_dict()
    return dict(question)


def select_next_question(questions, weak_topics, difficulty, asked_question_ids=None):
    """
    Select one question at the target difficulty.

    Search order:
        1. weak topics in Person 2's priority order
        2. any topic at the target difficulty
        3. None if unavailable

    `asked_question_ids` is optional so repeats can be prevented when the
    frontend/session layer starts passing the IDs already shown.
    """
    asked_question_ids = set(asked_question_ids or set())
    normalized_questions = [_question_to_dict(q) for q in questions]
    target_difficulty = int(difficulty)

    # Search weak topics in their existing priority order.
    for weak_topic in weak_topics or []:
        topic = _topic_name(weak_topic)
        if not topic:
            continue

        for question in normalized_questions:
            try:
                question_difficulty = int(question.get("difficulty"))
            except (TypeError, ValueError):
                continue

            if (
                question.get("topic") == topic
                and question_difficulty == target_difficulty
                and str(question.get("question_id")) not in asked_question_ids
            ):
                return question

    # Safe fallback: any topic at the target difficulty.
    for question in normalized_questions:
        try:
            question_difficulty = int(question.get("difficulty"))
        except (TypeError, ValueError):
            continue

        if (
            question_difficulty == target_difficulty
            and str(question.get("question_id")) not in asked_question_ids
        ):
            return question

    return None


def get_next_question(
    questions,
    weak_topics,
    current_difficulty,
    correct,
    asked_question_ids=None,
):
    """
    Main adaptive entry point.

    Returns:
        (next_question, next_difficulty)
    """
    next_difficulty = adjust_difficulty(current_difficulty, correct)
    next_question = select_next_question(
        questions,
        weak_topics,
        next_difficulty,
        asked_question_ids=asked_question_ids,
    )
    return next_question, next_difficulty


def load_questions(csv_path):
    """Load Person 1's real questions.csv and return plain dictionaries."""
    questions_df = pd.read_csv(csv_path)
    required = {"question_id", "topic", "difficulty", "question_text"}
    missing = required - set(questions_df.columns)
    if missing:
        raise ValueError(f"questions.csv is missing required columns: {sorted(missing)}")
    return questions_df.to_dict(orient="records")


# ---------------------------------------------------------------------------
# REAL-DATA DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    questions_path = "person1_package/questions.csv"
    attempts_path = "person1_package/clean_attempts.csv"

    clean_attempts = pd.read_csv(attempts_path)
    questions = load_questions(questions_path)

    # Use Person 2's real diagnosis for one real student.
    from dependencies import analyze_student

    student_id = str(clean_attempts.iloc[0]["student_id"])
    diagnosis = analyze_student(clean_attempts, student_id)
    weak_topics = diagnosis.get("weak_topics", [])

    # Use that student's latest attempt as the previous quiz interaction.
    student_attempts = clean_attempts[clean_attempts["student_id"].astype(str) == student_id].copy()
    student_attempts["timestamp"] = pd.to_datetime(student_attempts["timestamp"], errors="coerce")
    student_attempts = student_attempts.sort_values("timestamp")
    latest = student_attempts.iloc[-1]

    current_difficulty = int(latest["difficulty"])
    correct = bool(int(latest["is_correct"]))
    asked_ids = set(student_attempts["question_id"].astype(str))

    # For demonstration, allow a new question from the real bank rather than
    # accidentally returning something already attempted by this student.
    next_question, next_difficulty = get_next_question(
        questions,
        weak_topics,
        current_difficulty,
        correct,
        asked_question_ids=asked_ids,
    )

    print(f"=== Adaptive quiz demo for {student_id} ===")
    print(f"Previous difficulty: {current_difficulty}")
    print(f"Previous answer: {'Correct' if correct else 'Incorrect'}")
    print(f"Next difficulty: {next_difficulty}")

    if weak_topics:
        print("Top weak topic:", weak_topics[0]["topic"])
    else:
        print("Top weak topic: none")

    if next_question:
        print(f"Selected question: {next_question['question_id']}")
        print(f"Topic: {next_question['topic']}")
        print(f"Difficulty: {next_question['difficulty']}")
        print(f"Question: {next_question['question_text']}")
    else:
        print("No unseen question is available at the target difficulty.")
