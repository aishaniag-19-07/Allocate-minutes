# Data Dictionary — Person 1 (Data + Dataset)

Use this to answer judge questions. Everything here maps to a design
decision you should be able to explain in one sentence.

## Files produced

| File | Produced by | Purpose |
|---|---|---|
| `students.csv` | `generate_data.py` | One row per student |
| `questions.csv` | `generate_data.py` | One row per quiz question, tagged with topic + prerequisites |
| `attempts.csv` | `generate_data.py` | One row per quiz attempt (RAW, intentionally a bit messy) |
| `clean_attempts.csv` | `preprocessing.py` | Cleaned + merged + feature-engineered — **this is what Person 2/3 should use** |

## students.csv
| Column | Meaning |
|---|---|
| student_id | Unique ID, e.g. `S001` |
| name | Display name |
| grade | 9–12 |
| exam_goal | What the student is preparing for (affects how Person 3 prioritizes topics) |
| available_minutes_per_day | Self-reported study time — feeds directly into Person 3's planner |
| join_date | When they joined the platform |

## questions.csv
| Column | Meaning |
|---|---|
| question_id | Unique ID, e.g. `Q0001` |
| topic | Which of the 11 topics this question tests |
| prerequisite_topics | Semicolon-separated list of topics this topic depends on (used by Person 2's dependency logic) |
| difficulty | 1 (easy) – 5 (hard) |
| question_text / option_a-d / correct_option | Standard MCQ fields |

**Topic dependency graph used (same one Person 2 should reference):**
```
Python ─────┐
Math_Basics ─┼─> AI_Basics ──> ML ──> Neural_Networks ──> RNN ──> LSTM ──> NLP
             │                              │
             └─> Statistics ─────────────────┴──> CNN
Python ──> Data_Structures
```
This mirrors the brief's example (Python → AI → ML → RNN → LSTM) so weakness
in a downstream topic can be traced to a weak prerequisite.

## attempts.csv (RAW — do not feed this directly to ML/mastery logic)
| Column | Meaning |
|---|---|
| attempt_id | Unique attempt ID |
| student_id / question_id | Foreign keys |
| topic / difficulty | Denormalized from questions.csv for convenience |
| timestamp | When the attempt happened |
| selected_option | What the student picked |
| is_correct | 0/1 |
| time_taken_seconds | How long they took |

**Why it's intentionally messy:** real quiz logs are never perfectly clean.
About 3% of rows have a missing timestamp, a missing/negative
`time_taken_seconds`, and a handful of exact duplicate rows are injected.
This gives the preprocessing step real work to do and gives you something
concrete to demo/explain ("here's what we found wrong with the raw data and
how we fixed it").

## clean_attempts.csv (THE OUTPUT — hand this to Person 2 & 3)
Everything from attempts.csv, cleaned, plus:

| New column | Meaning | Why it exists |
|---|---|---|
| prerequisite_topics, correct_option | Merged in from questions.csv | So downstream code doesn't need a second join |
| grade, exam_goal, available_minutes_per_day | Merged in from students.csv | Same reason |
| days_since_attempt | How many days ago this attempt happened | Input to recency weighting |
| recency_weight | Exponential decay weight, half-life = 10 days | Recent attempts should count more toward *current* mastery than old ones — a student who struggled with a topic a month ago but has since improved shouldn't be flagged as still weak |
| time_taken_bucket | `fast` / `normal` / `slow`, computed **relative to that difficulty level** (via quantiles) | A flat time cutoff is meaningless across difficulty 1 vs 5, so buckets are computed within each difficulty group |
| attempt_order_in_topic | 1st, 2nd, 3rd... attempt by that student on that topic | Needed to detect *repeated* errors (Person 2), not just isolated mistakes |

## Cleaning steps performed (in order) — be ready to explain each
1. **Parse timestamps** (`pd.to_datetime(..., errors="coerce")`) — unparseable/blank timestamps become `NaT` and those rows are dropped, since you can't compute recency without a valid time.
2. **Fix bad `time_taken_seconds`** — negative values are physically impossible, so they're treated as missing, then imputed with the **median for that difficulty level** (not a global median, since harder questions naturally take longer).
3. **Drop exact duplicates** — same student + question + timestamp appearing twice is a logging glitch, not two real attempts.
4. **Merge** attempts + questions + students into one table so downstream code does a single `pd.read_csv` instead of three joins.
5. **Feature engineer** recency weight, time bucket, and attempt order (see table above).

## Why Pandas (in case asked)
- Need to join 3 relational tables and it's built for exactly that (`.merge`)
- Vectorized operations (`groupby`, `transform`, `qcut`) instead of manual loops over rows — much faster and less error-prone at ~3,300 rows, and scales the same way at 300,000
- It's the format scikit-learn (Person 3's Random Forest) expects data in — no extra conversion step

## How to regenerate
```bash
python3 generate_data.py      # -> students.csv, questions.csv, attempts.csv
python3 preprocessing.py      # -> clean_attempts.csv
```
Both use a fixed random seed (`SEED = 42`), so the output is identical every
time you run it — useful when debugging with Person 2/3 ("regenerate and
you'll see the same numbers I do").
