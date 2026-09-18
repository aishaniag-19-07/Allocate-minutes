"""
generate_data.py
-----------------
Generates the 3 raw CSVs for the Adaptive Study Planner project:

    students.csv
    questions.csv
    attempts.csv

WHY SYNTHETIC DATA:
    We don't have a real quiz platform, so we simulate one. Each student
    gets a hidden "true skill" per topic (0-1). Their probability of
    answering a question correctly is a function of that skill and the
    question's difficulty, PLUS respect for prerequisite topics (a student
    can't be great at LSTM if they're bad at RNN -- this is what makes the
    dependency/root-cause logic in Person 2's module meaningful).

    This is a logistic (IRT-style) model:
        P(correct) = sigmoid( skill_effective - difficulty_scaled )

    "skill_effective" is discounted if prerequisite topics are weak, so
    the generated data has REAL weakness chains baked in for the demo.

REPRODUCIBILITY:
    A fixed random seed is used so the same dataset is produced every run.
    This matters for debugging: if Person 2/3's numbers look wrong, you can
    regenerate the exact same data and compare.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
SEED = 42
N_STUDENTS = 40
N_QUESTIONS_PER_TOPIC = 12
N_DAYS_OF_HISTORY = 21          # attempts spread across ~3 weeks
AVG_ATTEMPTS_PER_STUDENT_PER_DAY = 4

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# TOPIC DEPENDENCY GRAPH
# ---------------------------------------------------------------------------
# Each topic lists its direct prerequisites. This mirrors the example in the
# brief: Python -> AI -> ML -> RNN -> LSTM
# Person 2 uses this same structure for root-cause / prerequisite analysis,
# so keep the topic names IDENTICAL across files.
TOPIC_DEPENDENCIES = {
    "Math_Basics":       [],
    "Python":            [],
    "Data_Structures":   ["Python"],
    "Statistics":        ["Math_Basics"],
    "AI_Basics":         ["Python", "Math_Basics"],
    "ML":                ["AI_Basics", "Statistics"],
    "Neural_Networks":   ["ML"],
    "CNN":               ["Neural_Networks"],
    "RNN":               ["Neural_Networks"],
    "LSTM":              ["RNN"],
    "NLP":               ["LSTM"],
}
TOPICS = list(TOPIC_DEPENDENCIES.keys())

FIRST_NAMES = ["Aarav","Vivaan","Aditya","Ishaan","Kabir","Arjun","Reyansh","Ayaan",
               "Diya","Ananya","Saanvi","Myra","Aadhya","Kiara","Anaya","Zara",
               "Rohan","Kavya","Neha","Yash","Priya","Karan","Meera","Dev",
               "Tara","Rahul","Sneha","Vikram","Isha","Aman"]

# ---------------------------------------------------------------------------
# 1) STUDENTS
# ---------------------------------------------------------------------------
def generate_students():
    student_ids = [f"S{str(i+1).zfill(3)}" for i in range(N_STUDENTS)]
    names = rng.choice(FIRST_NAMES, size=N_STUDENTS, replace=True)
    # disambiguate repeated first names
    names = [f"{n} {chr(65 + i % 26)}." for i, n in enumerate(names)]

    grades = rng.choice([9, 10, 11, 12], size=N_STUDENTS)
    exam_goals = rng.choice(
        ["Board_Exam", "Entrance_Exam", "Coding_Interview", "General_Practice"],
        size=N_STUDENTS
    )
    # minutes/day the student says they can study -- used later by Person 3's planner
    available_minutes = rng.choice([15, 30, 45, 60, 90], size=N_STUDENTS,
                                    p=[0.15, 0.30, 0.25, 0.20, 0.10])
    join_offset_days = rng.integers(30, 120, size=N_STUDENTS)
    today = datetime.now().date()
    join_dates = [today - timedelta(days=int(d)) for d in join_offset_days]

    # ---- HIDDEN ground-truth skill per topic (0=no skill, 1=mastery) ----
    # Not written to CSV (a real system wouldn't know this either) but used
    # to drive attempt correctness below. Kept in a dict for generate_attempts.
    hidden_skill = {}
    for sid in student_ids:
        base = rng.uniform(0.2, 0.85)               # overall aptitude
        skills = {}
        for topic in TOPICS:
            noise = rng.normal(0, 0.15)
            skills[topic] = float(np.clip(base + noise, 0.05, 0.98))
        hidden_skill[sid] = skills

    df = pd.DataFrame({
        "student_id": student_ids,
        "name": names,
        "grade": grades,
        "exam_goal": exam_goals,
        "available_minutes_per_day": available_minutes,
        "join_date": join_dates,
    })
    return df, hidden_skill


# ---------------------------------------------------------------------------
# 2) QUESTIONS
# ---------------------------------------------------------------------------
def generate_questions():
    rows = []
    qnum = 1
    for topic in TOPICS:
        for i in range(N_QUESTIONS_PER_TOPIC):
            difficulty = int(rng.integers(1, 6))  # 1 (easy) - 5 (hard)
            qid = f"Q{str(qnum).zfill(4)}"
            prereqs = ";".join(TOPIC_DEPENDENCIES[topic]) if TOPIC_DEPENDENCIES[topic] else ""
            rows.append({
                "question_id": qid,
                "topic": topic,
                "prerequisite_topics": prereqs,
                "difficulty": difficulty,
                "question_text": f"[{topic}] Practice question #{i+1} (difficulty {difficulty})",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "correct_option": rng.choice(["a", "b", "c", "d"]),
            })
            qnum += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3) ATTEMPTS
# ---------------------------------------------------------------------------
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def generate_attempts(students_df, questions_df, hidden_skill):
    rows = []
    attempt_num = 1
    now = datetime.now()

    for _, srow in students_df.iterrows():
        sid = srow["student_id"]
        n_attempts = rng.poisson(AVG_ATTEMPTS_PER_STUDENT_PER_DAY * N_DAYS_OF_HISTORY)
        n_attempts = max(n_attempts, 15)  # floor so every student has enough history

        # each student attempts a random subset of questions, weighted toward
        # topics they haven't done much of yet (mimics adaptive-ish history)
        chosen_questions = questions_df.sample(
            n=min(n_attempts, len(questions_df)), replace=True, random_state=int(rng.integers(0, 1e6))
        )

        # spread attempts across the last N_DAYS_OF_HISTORY, more recent = more attempts
        day_offsets = rng.choice(
            range(N_DAYS_OF_HISTORY), size=len(chosen_questions),
            p=np.linspace(0.5, 1.5, N_DAYS_OF_HISTORY) / np.linspace(0.5, 1.5, N_DAYS_OF_HISTORY).sum()
        )
        day_offsets = sorted(day_offsets, reverse=True)  # oldest first for realism

        # a few students get a "repeated misconception" on one random topic:
        # they reliably get a specific topic wrong even on easy questions.
        misconception_topic = None
        if rng.random() < 0.35:
            misconception_topic = rng.choice(TOPICS)

        for (_, qrow), day_off in zip(chosen_questions.iterrows(), day_offsets):
            topic = qrow["topic"]
            difficulty = qrow["difficulty"]

            # effective skill = own skill, discounted if prerequisites are weak
            prereqs = TOPIC_DEPENDENCIES[topic]
            skill = hidden_skill[sid][topic]
            if prereqs:
                prereq_avg = np.mean([hidden_skill[sid][p] for p in prereqs])
                # weak prerequisite drags down effective skill (this is the
                # root-cause signal Person 2's module is meant to detect)
                skill_effective = 0.6 * skill + 0.4 * prereq_avg
            else:
                skill_effective = skill

            if misconception_topic == topic:
                skill_effective *= 0.4  # consistently weak on this one topic

            # IRT-style logistic: higher difficulty -> lower P(correct)
            z = (skill_effective * 10 - 5) - (difficulty - 3) * 1.2
            p_correct = float(np.clip(sigmoid(z), 0.03, 0.97))
            is_correct = int(rng.random() < p_correct)

            # time taken: harder questions + lower skill -> more time, plus noise
            base_time = 15 + difficulty * 8
            time_taken = max(5, int(rng.normal(base_time * (1.6 - skill_effective), 6)))

            timestamp = now - timedelta(
                days=float(day_off),
                hours=float(rng.integers(0, 24)),
                minutes=float(rng.integers(0, 60)),
            )

            selected_option = qrow["correct_option"] if is_correct else rng.choice(
                [o for o in ["a", "b", "c", "d"] if o != qrow["correct_option"]]
            )

            rows.append({
                "attempt_id": f"A{str(attempt_num).zfill(6)}",
                "student_id": sid,
                "question_id": qrow["question_id"],
                "topic": topic,
                "difficulty": difficulty,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "selected_option": selected_option,
                "is_correct": is_correct,
                "time_taken_seconds": time_taken,
            })
            attempt_num += 1

    attempts_df = pd.DataFrame(rows)

    # ---- Inject a bit of realistic messiness on purpose ----
    # A real CSV from a hackathon quiz app will NOT be perfectly clean.
    # Injecting a few issues here lets Person 1's preprocessing step do real work
    # (and gives you something concrete to explain to judges).
    messy_idx = attempts_df.sample(frac=0.03, random_state=SEED).index
    for idx in messy_idx:
        choice = rng.integers(0, 3)
        if choice == 0:
            attempts_df.loc[idx, "time_taken_seconds"] = np.nan          # missing value
        elif choice == 1:
            attempts_df.loc[idx, "time_taken_seconds"] = -5              # bad/negative value
        else:
            attempts_df.loc[idx, "timestamp"] = ""                       # missing timestamp

    # a handful of exact duplicate rows (common in real logging systems)
    dup_rows = attempts_df.sample(n=8, random_state=SEED)
    attempts_df = pd.concat([attempts_df, dup_rows], ignore_index=True)

    attempts_df = attempts_df.sort_values("timestamp").reset_index(drop=True)
    return attempts_df


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    students_df, hidden_skill = generate_students()
    questions_df = generate_questions()
    attempts_df = generate_attempts(students_df, questions_df, hidden_skill)

    students_df.to_csv("students.csv", index=False)
    questions_df.to_csv("questions.csv", index=False)
    attempts_df.to_csv("attempts.csv", index=False)

    print(f"students.csv  -> {len(students_df)} rows")
    print(f"questions.csv -> {len(questions_df)} rows")
    print(f"attempts.csv  -> {len(attempts_df)} rows")
    print("\nSample of attempts.csv:")
    print(attempts_df.head())
