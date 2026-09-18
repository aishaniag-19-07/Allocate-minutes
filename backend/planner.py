"""
planner.py
Owner: Person 3

REAL-DATA VERSION
-----------------
Builds a personalized study plan from Person 2's real diagnosis output.

Flow:
    Person 1 clean_attempts.csv
            -> Person 2 analyze_student()
            -> weak_topics (topic + mastery + numeric priority)
            -> this planner
            -> timed study plan

The core planning rule remains explainable:
    need_score = weakness * priority_weight

Person 2's priority is a 0-100 score, so it is converted linearly to a
1-3 multiplier. This preserves the original planner's High/Medium/Low
idea without requiring a second priority calculation.
"""

import pandas as pd

MIN_BLOCK_MINUTES = 10
MAX_BLOCK_MINUTES = 45
REVISION_SHARE = 0.15
REVISION_MIN_MINUTES = 15
REVISION_MAX_MINUTES = 30


# ---------------------------------------------------------------------------
# Priority + scoring helpers
# ---------------------------------------------------------------------------

def priority_weight(priority):
    """
    Convert Person 2's numeric priority (0-100) to a 1-3 multiplier.

    Examples:
        0   -> 1.0
        50  -> 2.0
        100 -> 3.0

    Also accepts the old High/Medium/Low labels for compatibility.
    """
    if isinstance(priority, str):
        labels = {"High": 3.0, "Medium": 2.0, "Low": 1.0}
        return labels.get(priority, 2.0)

    try:
        value = float(priority)
    except (TypeError, ValueError):
        return 2.0

    value = max(0.0, min(100.0, value))
    return 1.0 + 2.0 * (value / 100.0)


def mastery_label(mastery):
    """Turn mastery into simple explanation text."""
    try:
        mastery = float(mastery)
    except (TypeError, ValueError):
        mastery = 50.0

    if mastery < 50:
        return "Low mastery"
    if mastery < 75:
        return "Medium mastery"
    return "High mastery"


def calculate_need_score(topic):
    """
    Core planner score:
        need_score = (100 - mastery) * priority_weight

    Lower mastery and higher Person 2 priority both increase study time.
    """
    try:
        mastery = float(topic.get("mastery", 50))
    except (TypeError, ValueError):
        mastery = 50.0

    mastery = max(0.0, min(100.0, mastery))
    weakness = 100.0 - mastery
    return weakness * priority_weight(topic.get("priority", 50))


# ---------------------------------------------------------------------------
# Real diagnosis -> plan adapter
# ---------------------------------------------------------------------------

def prepare_weak_topics(diagnosis):
    """
    Extract Person 2's weak_topics list from analyze_student() output.

    Person 2 already sorts weak topics by priority, but we sort again by
    need_score here because the planner's allocation is based on both
    priority and mastery.
    """
    if not isinstance(diagnosis, dict):
        return []

    weak_topics = diagnosis.get("weak_topics", [])
    if not isinstance(weak_topics, list):
        return []

    return [topic for topic in weak_topics if isinstance(topic, dict) and topic.get("topic")]


# ---------------------------------------------------------------------------
# Study-plan generation
# ---------------------------------------------------------------------------

def generate_study_plan(weak_topics, available_minutes):
    """
    Generate a time-boxed study plan.

    Returns a list like:
        {
            "topic": "LSTM",
            "minutes": 39,
            "reason": "Low mastery + priority 59.2"
        }
    """
    try:
        available_minutes = int(available_minutes)
    except (TypeError, ValueError):
        available_minutes = 0

    if available_minutes < MIN_BLOCK_MINUTES:
        return [{
            "topic": "N/A",
            "minutes": 0,
            "reason": f"Not enough time to build a plan (need at least {MIN_BLOCK_MINUTES} minutes).",
        }]

    if not weak_topics:
        return [{
            "topic": "Revision",
            "minutes": available_minutes,
            "reason": "No weak topics found -- use this time to review previous mistakes.",
        }]

    revision_minutes = 0
    if available_minutes >= REVISION_MIN_MINUTES + MIN_BLOCK_MINUTES:
        revision_minutes = int(available_minutes * REVISION_SHARE)
        revision_minutes = max(
            REVISION_MIN_MINUTES,
            min(REVISION_MAX_MINUTES, revision_minutes),
        )

    topics_budget = available_minutes - revision_minutes

    scored_topics = []
    for topic in weak_topics:
        try:
            mastery = float(topic.get("mastery", 50))
        except (TypeError, ValueError):
            mastery = 50.0

        priority = topic.get("priority", 50)
        score = calculate_need_score(topic)
        scored_topics.append({
            "topic": topic["topic"],
            "mastery": mastery,
            "priority": priority,
            "score": score,
            "source": topic,
        })

    scored_topics.sort(key=lambda item: item["score"], reverse=True)
    total_score = sum(item["score"] for item in scored_topics)

    if total_score <= 0:
        # Defensive fallback: divide time equally if every score is zero.
        for item in scored_topics:
            item["score"] = 1.0
        total_score = float(len(scored_topics))

    # First pass: proportional floor allocation.
    allocations = []
    remaining = topics_budget
    for item in scored_topics:
        exact = topics_budget * item["score"] / total_score
        minutes = max(MIN_BLOCK_MINUTES, min(MAX_BLOCK_MINUTES, int(exact)))
        minutes = min(minutes, remaining)
        if minutes >= MIN_BLOCK_MINUTES:
            allocations.append({
                "item": item,
                "minutes": minutes,
                "fraction": exact - int(exact),
            })
            remaining -= minutes
        if remaining < MIN_BLOCK_MINUTES:
            break

    # Second pass: distribute spare whole minutes by largest fractional part.
    # This removes the old 118/120-minute rounding leak whenever possible.
    while remaining > 0 and allocations:
        candidates = [a for a in allocations if a["minutes"] < MAX_BLOCK_MINUTES]
        if not candidates:
            break
        candidates.sort(key=lambda a: a["fraction"], reverse=True)
        changed = False
        for allocation in candidates:
            if remaining <= 0:
                break
            if allocation["minutes"] < MAX_BLOCK_MINUTES:
                allocation["minutes"] += 1
                remaining -= 1
                changed = True
        if not changed:
            break

    plan = []
    for allocation in allocations:
        item = allocation["item"]
        source = item["source"]

        try:
            priority_text = f"{float(item['priority']):.1f} priority"
        except (TypeError, ValueError):
            priority_text = f"{item['priority']} priority"

        reason_parts = [mastery_label(item["mastery"]), priority_text]

        weak_prereqs = source.get("weak_prerequisites", [])
        if weak_prereqs:
            reason_parts.append("weak prerequisite: " + ", ".join(map(str, weak_prereqs)))

        plan.append({
            "topic": item["topic"],
            "minutes": allocation["minutes"],
            "reason": " + ".join(reason_parts),
        })

    if revision_minutes >= MIN_BLOCK_MINUTES:
        plan.append({
            "topic": "Revision",
            "minutes": revision_minutes,
            "reason": "Review previous mistakes",
        })

    return plan


def build_student_plan(clean_attempts_df, students_df, student_id):
    """
    REAL integration entry point.

    Uses Person 2's analyze_student() to diagnose the student, then uses
    Person 1's students.csv for available study time and student metadata.

    Returns a dictionary containing student info, diagnosis summary and plan.
    """
    if student_id not in set(students_df["student_id"].astype(str)):
        return {
            "student_id": student_id,
            "warning": f"Student '{student_id}' was not found.",
            "plan": generate_study_plan([], 0),
        }

    student_row = students_df[students_df["student_id"].astype(str) == str(student_id)].iloc[0]
    available_minutes = int(student_row["available_minutes_per_day"])

    # Person 2's modules are expected to live beside this file in ml_engine/.
    from backend.dependencies import analyze_student

    diagnosis = analyze_student(clean_attempts_df, str(student_id))
    weak_topics = prepare_weak_topics(diagnosis)
    plan = generate_study_plan(weak_topics, available_minutes)

    return {
        "student_id": str(student_id),
        "name": student_row.get("name", ""),
        "grade": int(student_row["grade"]),
        "exam_goal": student_row.get("exam_goal", ""),
        "available_minutes": available_minutes,
        "weak_topics": weak_topics,
        "plan": plan,
        "warning": diagnosis.get("warning"),
    }


def print_plan(plan):
    """Pretty-print plan blocks."""
    for block in plan:
        print(f"{block['topic']} → {block['minutes']} min → {block['reason']}")


# ---------------------------------------------------------------------------
# REAL-DATA DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    attempts_path = "person1_package/clean_attempts.csv"
    students_path = "person1_package/students.csv"

    clean_attempts_df = pd.read_csv(attempts_path)
    students_df = pd.read_csv(students_path)

    student_id = str(students_df.iloc[0]["student_id"])
    result = build_student_plan(clean_attempts_df, students_df, student_id)

    print(f"=== Real study plan for {result['name']} ({student_id}) ===")
    print(f"Grade: {result['grade']}")
    print(f"Exam goal: {result['exam_goal']}")
    print(f"Available time: {result['available_minutes']} minutes/day\n")

    print("Weak topics:")
    for topic in result["weak_topics"]:
        print(
            f"  {topic['topic']} | mastery={topic['mastery']} | "
            f"priority={topic['priority']} | reasons={', '.join(topic['reasons'])}"
        )

    print("\n=== Personalized plan ===")
    print_plan(result["plan"])
    print(f"Total allocated: {sum(b['minutes'] for b in result['plan'])} / {result['available_minutes']} min")

    if result.get("warning"):
        print("Warning:", result["warning"])
