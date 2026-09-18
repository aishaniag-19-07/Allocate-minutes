"""
fix_attempts_consistency.py
-----------------------------
After populate_real_questions.py changes correct_option in questions.csv,
the OLD selected_option values in attempts.csv (chosen based on the old
answer key) can contradict the stored is_correct flag.

Rule preserved: is_correct is ground truth (it came from the skill
simulation in generate_data.py and drives all downstream mastery/weakness
logic -- we do NOT want to change it). What we fix is selected_option:
    - if is_correct == 1  -> selected_option must equal the (new) correct_option
    - if is_correct == 0  -> selected_option must be any option OTHER than
                              the (new) correct_option (chosen deterministically
                              via the same seed for reproducibility)
"""

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

questions = pd.read_csv("questions.csv")[["question_id", "correct_option"]]
attempts = pd.read_csv("attempts.csv")

merged = attempts.merge(questions, on="question_id", how="left")

new_selected = []
for _, row in merged.iterrows():
    correct = row["correct_option"]
    if row["is_correct"] == 1:
        new_selected.append(correct)
    else:
        wrong_options = [o for o in ["a", "b", "c", "d"] if o != correct]
        new_selected.append(rng.choice(wrong_options))

attempts["selected_option"] = new_selected
attempts.to_csv("attempts.csv", index=False)

# verify
check = attempts.merge(questions, on="question_id", how="left")
mismatch = ((check["is_correct"] == 1) & (check["selected_option"] != check["correct_option"])).sum()
print(f"Remaining inconsistent rows: {mismatch}")
print("attempts.csv updated and saved.")
