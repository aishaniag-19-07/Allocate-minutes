/* ============================================================
   plan.js — Real Backend Connected Study Plan

   API:
   GET /student/{student_id}/plan

   Backend response structure used:

   {
     student_id: "S001",
     available_minutes: 45,

     plan: [
       {
         topic: "ML",
         minutes: 10,
         reason: "..."
       }
     ],

     weak_topics_summary: [
       {
         topic: "ML",
         mastery: 48.5,
         priority: 60.2,
         severity: "high"
       }
     ]
   }

   auth.js must be loaded before this file.
   ============================================================ */


// ============================================================
// CONFIG
// ============================================================

const API_BASE = "http://127.0.0.1:8000";


// ============================================================
// CURRENT LOGGED-IN STUDENT
// ============================================================

const sessionUser =
  typeof getLoggedInUser === "function"
    ? getLoggedInUser()
    : null;


if (!sessionUser) {

  window.location.href = "login.html";

}


const CURRENT_STUDENT = sessionUser
  ? {
      student_id: sessionUser.student_id,
      name: sessionUser.name || "Student"
    }
  : {
      student_id: "",
      name: "Student"
    };


// ============================================================
// LOAD STUDY PLAN
// ============================================================

async function loadStudyPlan(studentId) {

  if (!studentId) {

    showWarning(
      "Student information is missing. Please log in again."
    );

    return;

  }


  try {

    const studentName =
      document.getElementById("student-name");


    if (studentName) {

      studentName.textContent =
        CURRENT_STUDENT.name.split(" ")[0];

    }


    showPlanLoading(true);


    const response = await fetch(
      `${API_BASE}/student/${encodeURIComponent(studentId)}/plan`
    );


    let data = {};


    try {

      data = await response.json();

    } catch (error) {

      console.error(
        "Could not parse plan response:",
        error
      );

    }


    if (!response.ok) {

      throw new Error(
        data.detail ||
        "Failed to load study plan"
      );

    }


    console.log(
      "Study plan API response:",
      data
    );


    showPlanLoading(false);


    renderSummary(data);


    renderPlanItems(
      data.plan || [],
      data.weak_topics_summary || []
    );


    if (data.warning) {

      showWarning(
        data.warning
      );

    }


  } catch (error) {

    console.error(
      "Study plan error:",
      error
    );


    showPlanLoading(false);


    showWarning(
      "Could not load plan: " +
      error.message
    );

  }

}


// ============================================================
// SUMMARY CARDS
// ============================================================

function renderSummary(data) {

  const plan =
    Array.isArray(data.plan)
      ? data.plan
      : [];


  // Calculate actual total time using backend field: minutes
  const totalTime =
    plan.reduce(
      (sum, item) => {

        return (
          sum +
          Number(item.minutes || 0)
        );

      },
      0
    );


  const totalTimeEl =
    document.getElementById(
      "total-time"
    );


  const topicCountEl =
    document.getElementById(
      "topic-count"
    );


  const doneCountEl =
    document.getElementById(
      "done-count"
    );


  if (totalTimeEl) {

    totalTimeEl.textContent =
      `${totalTime} min`;

  }


  /*
     Do not count "Revision" as a weak topic.
     It is a general revision block.
  */

  const actualTopics =
    plan.filter(
      item =>
        item.topic &&
        item.topic !== "Revision"
    );


  if (topicCountEl) {

    topicCountEl.textContent =
      actualTopics.length;

  }


  // Completion tracking is not implemented yet.
  if (doneCountEl) {

    doneCountEl.textContent =
      `0/${plan.length}`;

  }

}


// ============================================================
// RENDER STUDY PLAN
// ============================================================

function renderPlanItems(
  plan,
  weakTopicsSummary
) {

  const container =
    document.getElementById(
      "plan-list"
    );


  if (!container) {

    console.error(
      "plan-list element not found."
    );

    return;

  }


  container.innerHTML = "";


  if (
    !Array.isArray(plan) ||
    plan.length === 0
  ) {

    container.innerHTML = `
      <div
        class="card"
        style="
          text-align:center;
          padding:2rem;
        "
      >

        <p>
          No study plan available yet.
        </p>

        <p
          style="
            opacity:0.7;
            font-size:0.9em;
          "
        >
          Complete some quiz questions first
          to generate your personalized plan.
        </p>

        <a
          href="quiz.html"
          class="btn btn-accent"
          style="
            margin-top:1rem;
            display:inline-flex;
          "
        >
          Take a Quiz
        </a>

      </div>
    `;

    return;

  }


  plan.forEach(
    (item) => {

      /*
         Person 3 planner gives:
         topic
         minutes
         reason

         Person 2 summary gives:
         mastery
         priority
         severity

         Match both using topic.
      */

      const summary =
        weakTopicsSummary.find(
          weak =>
            weak.topic ===
            item.topic
        );


      const card =
        document.createElement(
          "div"
        );


      card.className =
        "card";


      // ======================================================
      // MINUTES
      // ======================================================

      const minutes =
        Number(
          item.minutes || 0
        );


      // ======================================================
      // MASTERY
      // ======================================================

      const hasMastery =
        summary &&
        summary.mastery !== null &&
        summary.mastery !== undefined;


      const mastery =
        hasMastery
          ? Number(summary.mastery)
          : null;


      const safeMastery =
        mastery !== null
          ? Math.max(
              0,
              Math.min(
                100,
                mastery
              )
            )
          : 0;


      const masteryText =
        mastery !== null
          ? `${Math.round(mastery)}%`
          : "—";


      const masteryColor =
        mastery === null
          ? "#94a3b8"
          : mastery >= 70
            ? "#22c55e"
            : mastery >= 40
              ? "#f59e0b"
              : "#ef4444";


      // ======================================================
      // PRIORITY
      // ======================================================

      const priority =
        summary &&
        summary.priority !== undefined &&
        summary.priority !== null
          ? Number(summary.priority)
          : null;


      const severity =
        summary &&
        summary.severity
          ? String(
              summary.severity
            ).toLowerCase()
          : null;


      const priorityInfo =
        getPriorityInfo(
          severity,
          priority,
          item.topic
        );


      // ======================================================
      // REVISION CHECK
      // ======================================================

      const isRevision =
        item.topic === "Revision";


      // ======================================================
      // CARD HTML
      // ======================================================

      card.innerHTML = `

        <div class="plan-item-header">

          <div>

            <div class="plan-item-topic">
              ${escapeHtml(
                formatTopic(
                  item.topic
                )
              )}
            </div>


            <div class="plan-item-duration">

              ${minutes} min recommended

            </div>

          </div>


          <span
            class="badge ${priorityInfo.className}"
          >
            ${priorityInfo.label}
          </span>

        </div>


        ${
          !isRevision
            ? `
              <div
                style="
                  margin:0.5rem 0;
                  display:flex;
                  align-items:center;
                  gap:0.75rem;
                  font-size:0.85em;
                  opacity:0.85;
                "
              >

                <span>
                  Mastery:

                  <strong
                    style="
                      color:${masteryColor};
                    "
                  >
                    ${masteryText}
                  </strong>

                </span>


                <div
                  style="
                    flex:1;
                    height:6px;
                    background:#e5e7eb;
                    border-radius:3px;
                    overflow:hidden;
                  "
                >

                  <div
                    style="
                      width:${safeMastery}%;
                      height:100%;
                      background:${masteryColor};
                      border-radius:3px;
                      transition:width 0.6s;
                    "
                  ></div>

                </div>

              </div>
            `
            : ""
        }


        <div class="plan-item-reason">

          <strong>
            Why:
          </strong>

          ${escapeHtml(
            item.reason ||
            (
              isRevision
                ? "General revision session"
                : "Recommended based on your learning profile"
            )
          )}

        </div>


        ${
          !isRevision &&
          priority !== null
            ? `
              <div
                style="
                  margin-top:0.5rem;
                  font-size:0.82em;
                  opacity:0.75;
                "
              >
                Priority score:
                <strong>
                  ${priority.toFixed(1)}
                </strong>
              </div>
            `
            : ""
        }


        <div class="plan-item-footer">

          <span></span>

          ${
            isRevision

              ? `
                <span
                  style="
                    font-size:0.85em;
                    opacity:0.7;
                  "
                >
                  Review session
                </span>
              `

              : `
                <button
                  class="btn btn-accent start-quiz-btn"
                  data-topic="${escapeHtml(
                    item.topic
                  )}"
                >
                  Start Quiz
                </button>
              `
          }

        </div>

      `;


      // ======================================================
      // QUIZ BUTTON
      // ======================================================

      if (!isRevision) {

        const quizButton =
          card.querySelector(
            ".start-quiz-btn"
          );


        if (quizButton) {

          quizButton.addEventListener(
            "click",
            () => {

              startQuiz(
                item.topic
              );

            }
          );

        }

      }


      container.appendChild(
        card
      );

    }
  );

}


// ============================================================
// PRIORITY DISPLAY
// ============================================================

function getPriorityInfo(
  severity,
  priority,
  topic
) {

  if (topic === "Revision") {

    return {
      label: "Review",
      className:
        "badge-priority-low"
    };

  }


  // Prefer Person 2's severity
  if (severity === "high") {

    return {
      label: "High Priority",
      className:
        "badge-priority-high"
    };

  }


  if (
    severity === "moderate" ||
    severity === "medium"
  ) {

    return {
      label: "Medium Priority",
      className:
        "badge-priority-medium"
    };

  }


  if (severity === "low") {

    return {
      label: "Low Priority",
      className:
        "badge-priority-low"
    };

  }


  /*
     Fallback only if severity is unavailable.
     Person 2's priority is a score,
     not a ranking number.
  */

  if (priority !== null) {

    if (priority >= 60) {

      return {
        label: "High Priority",
        className:
          "badge-priority-high"
      };

    }


    if (priority >= 35) {

      return {
        label: "Medium Priority",
        className:
          "badge-priority-medium"
      };

    }

  }


  return {
    label: "Low Priority",
    className:
      "badge-priority-low"
  };

}


// ============================================================
// START QUIZ
// ============================================================

function startQuiz(topic) {

  if (!topic) {

    window.location.href =
      "quiz.html";

    return;

  }


  window.location.href =
    `quiz.html?topic=${encodeURIComponent(topic)}`;

}


// ============================================================
// LOADING STATE
// ============================================================

function showPlanLoading(on) {

  const container =
    document.getElementById(
      "plan-list"
    );


  if (!container) {
    return;
  }


  if (on) {

    container.innerHTML = `

      <div
        class="card"
        style="
          text-align:center;
          padding:2rem;
          opacity:0.7;
        "
      >

        ⏳ Loading your personalized study plan...

      </div>

    `;

  }

}


// ============================================================
// WARNING / ERROR
// ============================================================

function showWarning(message) {

  const container =
    document.getElementById(
      "plan-list"
    );


  if (!container) {
    return;
  }


  const warning =
    document.createElement(
      "div"
    );


  warning.className =
    "card";


  warning.style.cssText = `
    border-left:3px solid #f59e0b;
    padding:1rem;
    opacity:0.85;
    margin-bottom:1rem;
  `;


  warning.textContent =
    "⚠ " + message;


  container.prepend(
    warning
  );

}


// ============================================================
// FORMAT TOPIC NAME
// ============================================================

function formatTopic(topic) {

  if (!topic) {
    return "Topic";
  }


  return String(topic)
    .replaceAll("_", " ");

}


// ============================================================
// SAFE HTML
// ============================================================

function escapeHtml(value) {

  return String(
    value ?? ""
  )
    .replaceAll(
      "&",
      "&amp;"
    )
    .replaceAll(
      "<",
      "&lt;"
    )
    .replaceAll(
      ">",
      "&gt;"
    )
    .replaceAll(
      '"',
      "&quot;"
    )
    .replaceAll(
      "'",
      "&#039;"
    );

}


// ============================================================
// BOOT
// ============================================================

document.addEventListener(
  "DOMContentLoaded",
  () => {

    if (
      CURRENT_STUDENT.student_id
    ) {

      loadStudyPlan(
        CURRENT_STUDENT.student_id
      );

    }

  }
);