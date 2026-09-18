"""
dependencies.py
================
Person 2 - Core Intelligence / Diagnosis Engine.

Rule-based prerequisite / root-cause analysis, plus analyze_student() -
the single combined-diagnosis function Person 3 calls.

This is deliberately NOT machine learning. It's a deterministic graph
walk over a fixed prerequisite map, chosen because it's fast, transparent
and easy to explain and debug in a hackathon demo. It identifies
prerequisite-based *signals*, not proven causes - see get_weak_prerequisites
and find_root_cause_paths for the "candidate, not certainty" wording.
"""

import pandas as pd

from backend.mastery import calculate_mastery, ValidationError
from backend.mistakes import analyze_weaknesses, GOOD_MASTERY_THRESHOLD

# ---------------------------------------------------------------------------
# Fixed prerequisite graph (Person 1's structure - do not invent a new one)
# ---------------------------------------------------------------------------

TOPIC_DEPENDENCIES = {
    "Math_Basics": [],
    "Python": [],
    "Data_Structures": ["Python"],
    "Statistics": ["Math_Basics"],
    "AI_Basics": ["Python", "Math_Basics"],
    "ML": ["AI_Basics", "Statistics"],
    "Neural_Networks": ["ML"],
    "CNN": ["Neural_Networks"],
    "RNN": ["Neural_Networks"],
    "LSTM": ["RNN"],
    "NLP": ["LSTM"],
}


def get_prerequisites(topic):
    """Direct prerequisites of a topic (empty list if none / unknown topic)."""
    return list(TOPIC_DEPENDENCIES.get(topic, []))


def get_weak_prerequisites(topic, mastery_dict, threshold=GOOD_MASTERY_THRESHOLD):
    """
    Split a topic's direct prerequisites into weak vs. no-data.

    A prerequisite the student has never attempted has no mastery score,
    so we can't honestly call it "weak" - we surface it separately
    instead of silently assuming it's fine (or assuming it's broken).
    """
    prereqs = get_prerequisites(topic)
    weak = [p for p in prereqs if p in mastery_dict and mastery_dict[p] < threshold]
    no_data = [p for p in prereqs if p not in mastery_dict]
    return weak, no_data


def find_root_cause_paths(topic, mastery_dict, threshold=GOOD_MASTERY_THRESHOLD, _visited=None):
    """
    DFS from `topic` down through its weak prerequisites.

    A node terminates a path (becomes a root-cause candidate) either
    because it has no prerequisites at all, or because none of its
    prerequisites are weak - i.e. going deeper doesn't find further
    evidence of a prerequisite gap, so this is as far back as the
    weakness signal traces.

    Returns a list of paths, each path a list of topics from `topic`
    down to a root-cause candidate, e.g. ["NLP", "LSTM", "RNN"].
    """
    if _visited is None:
        _visited = set()
    if topic in _visited:
        return [[topic]]  # cycle guard - the graph should be acyclic, but be defensive
    visited = _visited | {topic}

    weak_prereqs, _ = get_weak_prerequisites(topic, mastery_dict, threshold)
    if not weak_prereqs:
        return [[topic]]

    paths = []
    for prereq in weak_prereqs:
        for sub_path in find_root_cause_paths(prereq, mastery_dict, threshold, visited):
            paths.append([topic] + sub_path)
    return paths


def _paths_to_root_causes(paths):
    causes = []
    for path in paths:
        candidate = path[-1]
        if candidate not in causes:
            causes.append(candidate)
    return causes


def _paths_to_explanations(paths):
    explanations = []
    for path in paths:
        if len(path) == 1:
            explanations.append(f"{path[0]} is a root-cause candidate (no weak prerequisite found).")
            continue
        chain = " -> ".join(f"{t} is weak" for t in path[:-1])
        explanations.append(
            f"{chain} -> {path[-1]} is weak -> {path[-1]} is a root-cause candidate."
        )
    return explanations


def analyze_dependencies(topic, mastery_dict, threshold=GOOD_MASTERY_THRESHOLD):
    """
    Full prerequisite analysis for one topic.

    Returns
    -------
    dict with: topic, prerequisites, weak_prerequisites,
               prerequisites_without_data, root_causes,
               root_cause_explanation
    """
    prereqs = get_prerequisites(topic)
    weak_prereqs, no_data_prereqs = get_weak_prerequisites(topic, mastery_dict, threshold)
    paths = find_root_cause_paths(topic, mastery_dict, threshold)

    return {
        "topic": topic,
        "prerequisites": prereqs,
        "weak_prerequisites": weak_prereqs,
        "prerequisites_without_data": no_data_prereqs,
        "root_causes": _paths_to_root_causes(paths),
        "root_cause_explanation": _paths_to_explanations(paths),
    }


# ---------------------------------------------------------------------------
# Final combined diagnosis - this is what Person 3 imports and calls
# ---------------------------------------------------------------------------

def analyze_student(df, student_id):
    """
    Run the full mastery -> weakness -> dependency pipeline for one student.

    Parameters
    ----------
    df : pd.DataFrame
        Full clean_attempts dataset (all students).
    student_id : str

    Returns
    -------
    dict with:
        student_id  : str
        mastery     : {topic: score}
        weak_topics : list of dicts (see mistakes.analyze_weaknesses),
                      each additionally carrying prerequisites,
                      weak_prerequisites, prerequisites_without_data,
                      root_causes, root_cause_explanation
        warning     : str, present only if there's nothing to diagnose
                      (e.g. unknown student, no attempts)
    """
    mastery_result = calculate_mastery(df, student_id)
    mastery_dict = mastery_result.get("mastery", {})

    if not mastery_dict:
        return {
            "student_id": student_id,
            "mastery": {},
            "weak_topics": [],
            "warning": mastery_result.get(
                "warning", f"No usable data available for student '{student_id}'."
            ),
        }

    weak_topics = analyze_weaknesses(df, student_id, mastery_result)

    for weak in weak_topics:
        dep_info = analyze_dependencies(weak["topic"], mastery_dict)
        weak["prerequisites"] = dep_info["prerequisites"]
        weak["weak_prerequisites"] = dep_info["weak_prerequisites"]
        weak["prerequisites_without_data"] = dep_info["prerequisites_without_data"]
        weak["root_causes"] = dep_info["root_causes"]
        weak["root_cause_explanation"] = dep_info["root_cause_explanation"]

    result = {
        "student_id": student_id,
        "mastery": mastery_dict,
        "weak_topics": weak_topics,
    }
    if "warning" in mastery_result:
        result["warning"] = mastery_result["warning"]
    return result


# ---------------------------------------------------------------------------
# Quick CLI demo: python dependencies.py clean_attempts.csv S001
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "clean_attempts.csv"
    student = sys.argv[2] if len(sys.argv) > 2 else "S001"

    attempts_df = pd.read_csv(csv_path)
    diagnosis = analyze_student(attempts_df, student)
    print(json.dumps(diagnosis, indent=2))
