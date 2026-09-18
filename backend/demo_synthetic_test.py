"""
Illustrative synthetic test - NOT real data from the user's dataset.
Purpose: verify mastery.py / mistakes.py / dependencies.py run correctly
end-to-end and behave sensibly on edge cases, before the real
clean_attempts.csv is available.
"""
import json
import numpy as np
import pandas as pd

from dependencies import analyze_student, TOPIC_DEPENDENCIES

rows = []


def add(student, topic, q, difficulty, correct, order, bucket="normal", recency=0.8):
    rows.append({
        "attempt_id": f"{student}-{topic}-{order}",
        "student_id": student,
        "question_id": q,
        "topic": topic,
        "difficulty": difficulty,
        "is_correct": correct,
        "time_taken_bucket": bucket,
        "attempt_order_in_topic": order,
        "recency_weight": recency,
    })


# ---- Student S001: designed to exercise the full NLP -> LSTM -> RNN chain ----
# Math_Basics: strong
for i in range(1, 7):
    add("S001", "Math_Basics", f"MB{i}", difficulty=2, correct=1, order=i, bucket="fast", recency=0.9)

# Python: strong
for i in range(1, 7):
    add("S001", "Python", f"PY{i}", difficulty=2, correct=1, order=i, bucket="normal", recency=0.9)

# AI_Basics: weak (mixed, low accuracy)
ai_correct = [1, 0, 0, 1, 0, 0]
for i, c in enumerate(ai_correct, start=1):
    add("S001", "AI_Basics", f"AI{i}", difficulty=3, correct=c, order=i, bucket="normal", recency=0.6)

# Statistics: strong (so ML's weakness should NOT trace to Statistics)
for i in range(1, 6):
    add("S001", "Statistics", f"ST{i}", difficulty=3, correct=1, order=i, bucket="fast", recency=0.85)

# ML: weak, depends on AI_Basics (weak) + Statistics (strong)
ml_correct = [0, 0, 1, 0]
for i, c in enumerate(ml_correct, start=1):
    add("S001", "ML", f"ML{i}", difficulty=4, correct=c, order=i, bucket="slow", recency=0.5)

# Neural_Networks: strong (so RNN's weakness should NOT trace past RNN)
for i in range(1, 6):
    add("S001", "Neural_Networks", f"NN{i}", difficulty=3, correct=1, order=i, bucket="normal", recency=0.8)

# RNN: weak, 8 attempts / 6 incorrect (matches the brief's own example), repeated
# errors on the same question, and a wrong streak at the end.
rnn_pattern = [1, 0, 0, 0, 1, 0, 0, 0]  # 6 wrong / 8 total, ends on a streak of 3 wrong
for i, c in enumerate(rnn_pattern, start=1):
    q = "RNNQ_HARD" if i in (2, 3) else f"RNN{i}"  # RNNQ_HARD missed twice -> repeated error
    add("S001", "RNN", q, difficulty=4, correct=c, order=i, bucket="slow", recency=0.4)

# LSTM: weak, depends on RNN (weak)
lstm_correct = [0, 0, 1, 0, 0]
for i, c in enumerate(lstm_correct, start=1):
    add("S001", "LSTM", f"LSTM{i}", difficulty=4, correct=c, order=i, bucket="slow", recency=0.3)

# NLP: weak, depends on LSTM (weak) -> full chain NLP -> LSTM -> RNN
nlp_correct = [0, 0, 0, 1]
for i, c in enumerate(nlp_correct, start=1):
    add("S001", "NLP", f"NLP{i}", difficulty=5, correct=c, order=i, bucket="slow", recency=0.2)

# ---- Edge-case student S_EDGE: one attempt, missing bucket, invalid is_correct ----
add("S_EDGE", "Data_Structures", "DS1", difficulty=3, correct=1, order=1, bucket=None, recency=0.7)
rows.append({
    "attempt_id": "S_EDGE-Python-1", "student_id": "S_EDGE", "question_id": "PYX",
    "topic": "Python", "difficulty": 2, "is_correct": "not_a_bool",
    "time_taken_bucket": "normal", "attempt_order_in_topic": 1, "recency_weight": 0.0,
})

df = pd.DataFrame(rows)

print("=" * 70)
print("SCHEMA CHECK")
print("=" * 70)
print(df.dtypes)
print(df.head(3))

print("\n" + "=" * 70)
print("PIPELINE RUN: S001 (illustrative synthetic data)")
print("=" * 70)
diagnosis = analyze_student(df, "S001")
print(json.dumps(diagnosis, indent=2))

print("\n" + "=" * 70)
print("EDGE CASE: S_EDGE (one attempt, missing bucket, invalid is_correct)")
print("=" * 70)
print(json.dumps(analyze_student(df, "S_EDGE"), indent=2))

print("\n" + "=" * 70)
print("EDGE CASE: student does not exist")
print("=" * 70)
print(json.dumps(analyze_student(df, "S_NOPE"), indent=2))

print("\n" + "=" * 70)
print("EDGE CASE: missing required column")
print("=" * 70)
try:
    from mastery import calculate_mastery
    calculate_mastery(df.drop(columns=["recency_weight"]), "S001")
except Exception as e:
    print(f"{type(e).__name__}: {e}")
