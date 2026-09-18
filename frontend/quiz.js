/* ============================================================
   quiz.js — Real Backend Connected Adaptive Quiz

   APIs:
   GET  /student/{student_id}/quiz
   GET  /student/{student_id}/quiz?topic=ML
   POST /quiz/submit

   Flow:
   Study Plan
      ↓
   quiz.html?topic=ML
      ↓
   Read topic from URL
      ↓
   Fetch ML question
      ↓
   Submit answer
      ↓
   Backend updates mastery / weakness / prediction / plan
      ↓
   Next ML question

   auth.js must be loaded before this file.
   ============================================================ */


// ============================================================
// CONFIG
// ============================================================

// const QUIZ_API_BASE = "http://127.0.0.1:8000";
const API_BASE_URL = "https://allocate-minutes-api.vercel.app"


// ============================================================
// CURRENT LOGGED-IN STUDENT
// ============================================================

const quizSessionUser =
  typeof getLoggedInUser === "function"
    ? getLoggedInUser()
    : null;


if (!quizSessionUser) {
  window.location.href = "login.html";
}


const CURRENT_STUDENT = quizSessionUser
  ? {
      student_id: quizSessionUser.student_id,
      name: quizSessionUser.name || "Student"
    }
  : {
      student_id: "",
      name: "Student"
    };


// ============================================================
// READ TOPIC FROM URL
// Example:
// quiz.html?topic=ML
// ============================================================

const quizUrlParams =
  new URLSearchParams(
    window.location.search
  );


const requestedTopic =
  quizUrlParams.get("topic");


// ============================================================
// QUIZ STATE
// ============================================================

let quizState = {

  currentQuestion: null,

  selectedOption: null,

  answered: false,

  answers: [],

  questionCount: 0,

  totalQuestions: 7,

  questionStartTime: null,

  /*
     If user came from:

     plan.html
        ↓
     quiz.html?topic=ML

     activeTopic = "ML"

     Otherwise:
     activeTopic = null

     In that case backend itself selects
     the most appropriate weak topic.
  */

  activeTopic:
    requestedTopic || null

};


// ============================================================
// LOAD / RESET QUIZ
// ============================================================

async function loadQuiz(
  studentId,
  topic = null
) {

  if (!studentId) {

    showError(
      "Student information is missing. Please log in again."
    );

    return;

  }


  const studentName =
    document.getElementById(
      "student-name"
    );


  if (studentName) {

    studentName.textContent =
      CURRENT_STUDENT.name
        .split(" ")[0];

  }


  // Reset quiz
  quizState.answers = [];

  quizState.questionCount = 0;

  quizState.currentQuestion = null;

  quizState.selectedOption = null;

  quizState.answered = false;

  quizState.questionStartTime = null;


  /*
     Preserve explicit topic.

     If topic is null, backend can select
     the adaptive weak topic itself.
  */

  quizState.activeTopic =
    topic || null;


  await fetchNextQuestion(
    studentId,
    quizState.activeTopic
  );

}


// ============================================================
// FETCH NEXT QUESTION
// ============================================================

async function fetchNextQuestion(
  studentId,
  topic = null
) {

  try {

    showLoading(true);


    let url =
      `${QUIZ_API_BASE}/student/${encodeURIComponent(studentId)}/quiz`;


    if (topic) {

      url +=
        `?topic=${encodeURIComponent(topic)}`;

    }


    console.log(
      "Fetching quiz question:",
      url
    );


    const response =
      await fetch(url);


    let data = {};


    try {

      data =
        await response.json();

    } catch (error) {

      console.error(
        "Could not parse quiz response:",
        error
      );

    }


    if (!response.ok) {

      throw new Error(
        data.detail ||
        "Failed to load question"
      );

    }


    quizState.currentQuestion =
      data;


    quizState.questionCount += 1;


    quizState.selectedOption =
      null;


    quizState.answered =
      false;


    /*
       If no topic was explicitly selected,
       remember whichever topic the adaptive
       backend selected.

       This keeps the remaining quiz focused
       on the same topic.
    */

    if (!quizState.activeTopic) {

      quizState.activeTopic =
        data.topic || null;

    }


    showQuestion(data);


    /*
       Start timer AFTER the question
       has actually loaded.
    */

    quizState.questionStartTime =
      Date.now();


    showLoading(false);


  } catch (error) {

    console.error(
      "Question loading error:",
      error
    );


    showLoading(false);


    /*
       If student already answered every available
       question in this topic, backend may return
       a no-question error.

       If we already completed some questions,
       finish the quiz gracefully.
    */

    if (
      quizState.answers.length > 0 &&
      String(error.message)
        .toLowerCase()
        .includes("question")
    ) {

      showCompletion();

      return;

    }


    showError(
      "Could not load question: " +
      error.message
    );

  }

}


// ============================================================
// SHOW QUESTION
// ============================================================

function showQuestion(question) {

  const activeSection =
    document.getElementById(
      "quiz-active"
    );


  const completionSection =
    document.getElementById(
      "quiz-completion"
    );


  if (activeSection) {

    activeSection.style.display =
      "block";

  }


  if (completionSection) {

    completionSection.style.display =
      "none";

  }


  const total =
    quizState.totalQuestions;


  const current =
    quizState.questionCount;


  // ==========================================================
  // QUESTION NUMBER
  // ==========================================================

  const questionNumber =
    document.getElementById(
      "question-number"
    );


  if (questionNumber) {

    questionNumber.textContent =
      `Question ${current} of ${total}`;

  }


  // ==========================================================
  // PROGRESS
  // ==========================================================

  const progressFill =
    document.getElementById(
      "progress-fill"
    );


  if (progressFill) {

    progressFill.style.width =
      `${((current - 1) / total) * 100}%`;

  }


  // ==========================================================
  // TOPIC
  // ==========================================================

  const topicElement =
    document.getElementById(
      "question-topic"
    );


  if (topicElement) {

    topicElement.textContent =
      formatQuizTopic(
        question.topic
      );

  }


  // ==========================================================
  // DIFFICULTY
  // ==========================================================

  const difficultyLabel =
    question.difficulty_label ||
    (
      question.difficulty <= 2
        ? "easy"
        : question.difficulty <= 3
          ? "medium"
          : "hard"
    );


  const difficultyBadge =
    document.getElementById(
      "difficulty-badge"
    );


  if (difficultyBadge) {

    difficultyBadge.textContent =
      capitalizeQuizText(
        difficultyLabel
      );


    difficultyBadge.className =
      `badge badge-difficulty-${String(
        difficultyLabel
      ).toLowerCase()}`;

  }


  // ==========================================================
  // QUESTION TEXT
  // ==========================================================

  const questionText =
    document.getElementById(
      "question-text"
    );


  if (questionText) {

    questionText.textContent =
      question.question_text;


    /*
       Useful during hackathon demo:
       Hover question to see ML probability.

       It remains hidden from normal UI.
    */

    if (
      question.predicted_success !== null &&
      question.predicted_success !== undefined
    ) {

      questionText.title =
        `ML predicted success: ${
          Math.round(
            Number(
              question.predicted_success
            ) * 100
          )
        }%`;

    } else {

      questionText.removeAttribute(
        "title"
      );

    }

  }


  // ==========================================================
  // OPTIONS
  // ==========================================================

  const optionsContainer =
    document.getElementById(
      "quiz-options"
    );


  if (optionsContainer) {

    optionsContainer.innerHTML = "";


    const optionKeys =
      ["a", "b", "c", "d"];


    const letters =
      ["A", "B", "C", "D"];


    optionKeys.forEach(
      (key, index) => {

        const optionText =
          question.options?.[key];


        if (!optionText) {
          return;
        }


        const button =
          document.createElement(
            "button"
          );


        button.className =
          "quiz-option";


        button.dataset.key =
          key;


        const letterSpan =
          document.createElement(
            "span"
          );


        letterSpan.className =
          "quiz-option__letter";


        letterSpan.textContent =
          letters[index];


        const textSpan =
          document.createElement(
            "span"
          );


        textSpan.textContent =
          optionText;


        button.appendChild(
          letterSpan
        );


        button.appendChild(
          textSpan
        );


        button.addEventListener(
          "click",
          () => {

            selectOption(
              key,
              index
            );

          }
        );


        optionsContainer.appendChild(
          button
        );

      }
    );

  }


  // ==========================================================
  // RESET BUTTONS
  // ==========================================================

  const submitButton =
    document.getElementById(
      "submit-btn"
    );


  const nextButton =
    document.getElementById(
      "next-btn"
    );


  if (submitButton) {

    submitButton.disabled =
      true;


    submitButton.style.display =
      "inline-flex";


    submitButton.textContent =
      "Submit Answer";

  }


  if (nextButton) {

    nextButton.style.display =
      "none";

  }


  const feedbackArea =
    document.getElementById(
      "feedback-area"
    );


  if (feedbackArea) {

    feedbackArea.innerHTML =
      "";

  }

}


// ============================================================
// SELECT OPTION
// ============================================================

function selectOption(
  key,
  index
) {

  if (
    quizState.answered
  ) {
    return;
  }


  quizState.selectedOption =
    key;


  document
    .querySelectorAll(
      ".quiz-option"
    )
    .forEach(
      (element, i) => {

        element.classList.toggle(
          "selected",
          i === index
        );

      }
    );


  const submitButton =
    document.getElementById(
      "submit-btn"
    );


  if (submitButton) {

    submitButton.disabled =
      false;

  }

}


// ============================================================
// SUBMIT ANSWER
// ============================================================

async function submitAnswer() {

  if (
    quizState.selectedOption === null ||
    quizState.answered
  ) {
    return;
  }


  const question =
    quizState.currentQuestion;


  if (!question) {

    showError(
      "Question data is missing."
    );

    return;

  }


  const startTime =
    quizState.questionStartTime ||
    Date.now();


  const timeTaken =
    Math.max(
      1,
      Math.round(
        (
          Date.now() -
          startTime
        ) / 1000
      )
    );


  const submitButton =
    document.getElementById(
      "submit-btn"
    );


  if (submitButton) {

    submitButton.disabled =
      true;


    submitButton.textContent =
      "Submitting…";

  }


  try {

    /*
       IMPORTANT:

       Backend contract contains ONLY:

       student_id
       question_id
       selected_option
       time_taken_seconds

       We do NOT send current_difficulty.
    */

    const response =
      await fetch(
        `${QUIZ_API_BASE}/quiz/submit`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body:
            JSON.stringify({
              student_id:
                CURRENT_STUDENT.student_id,

              question_id:
                question.question_id,

              selected_option:
                quizState.selectedOption,

              time_taken_seconds:
                timeTaken
            })
        }
      );


    let result = {};


    try {

      result =
        await response.json();

    } catch (error) {

      console.error(
        "Could not parse submit response:",
        error
      );

    }


    if (!response.ok) {

      throw new Error(
        result.detail ||
        "Submit failed"
      );

    }


    console.log(
      "Quiz submit response:",
      result
    );


    quizState.answered =
      true;


    quizState.answers.push({

      question_id:
        question.question_id,

      topic:
        question.topic,

      selected_option:
        quizState.selectedOption,

      is_correct:
        Boolean(
          result.correct
        )

    });


    showResult(
      result,
      question
    );


  } catch (error) {

    console.error(
      "Answer submission error:",
      error
    );


    if (submitButton) {

      submitButton.disabled =
        false;


      submitButton.textContent =
        "Submit Answer";

    }


    showError(
      "Could not submit answer: " +
      error.message
    );

  }

}


// ============================================================
// SHOW RESULT / PERSON 2 FEEDBACK
// ============================================================

function showResult(
  result,
  question
) {

  const optionElements =
    document.querySelectorAll(
      ".quiz-option"
    );


  optionElements.forEach(
    element => {

      element.disabled =
        true;


      const key =
        element.dataset.key;


      if (
        key ===
        result.answer?.correct
      ) {

        element.classList.add(
          "correct"
        );

      } else if (
        key ===
        quizState.selectedOption &&
        !result.correct
      ) {

        element.classList.add(
          "incorrect"
        );

      }

    }
  );


  const feedbackElement =
    document.getElementById(
      "feedback-area"
    );


  if (!feedbackElement) {
    return;
  }


  // ==========================================================
  // MASTERY
  // ==========================================================

  const beforeMastery =
    result.before?.mastery;


  const afterMastery =
    result.after?.mastery;


  const hasMasteryValues =
    typeof beforeMastery === "number" &&
    typeof afterMastery === "number";


  const masteryDelta =
    hasMasteryValues
      ? (
          afterMastery -
          beforeMastery
        ).toFixed(1)
      : null;


  const masteryDeltaHtml =
    masteryDelta !== null
      ? `
          <span
            style="
              font-size:0.85em;
              opacity:0.8;
            "
          >
            (
              ${
                Number(masteryDelta) > 0
                  ? "+"
                  : ""
              }${masteryDelta}%
            )
          </span>
        `
      : "";


  const afterMasteryText =
    typeof afterMastery === "number"
      ? `${afterMastery}%`
      : "—";


  // ==========================================================
  // PERSON 2 WEAKNESS REASONS
  // ==========================================================

  const reasons =
    Array.isArray(
      result.weakness?.reasons
    )
      ? result.weakness.reasons
      : [];


  const reasonsHtml =
    reasons.length
      ? `
          <div class="feedback-patterns">

            <strong>
              Analysis:
            </strong>

            ${reasons
              .map(
                reason =>
                  escapeQuizHtml(
                    formatQuizReason(
                      reason
                    )
                  )
              )
              .join(" · ")}

          </div>
        `
      : "";


  // ==========================================================
  // REPEATED ERROR INFO
  // ==========================================================

  const repeatedErrors =
    Number(
      result.weakness
        ?.repeated_question_errors ||
      0
    );


  const wrongStreak =
    Number(
      result.weakness
        ?.wrong_streak ||
      0
    );


  let errorStatsHtml = "";


  if (
    repeatedErrors > 0 ||
    wrongStreak > 0
  ) {

    const stats = [];


    if (repeatedErrors > 0) {

      stats.push(
        `${repeatedErrors} repeated error${
          repeatedErrors !== 1
            ? "s"
            : ""
        }`
      );

    }


    if (wrongStreak > 0) {

      stats.push(
        `wrong streak: ${wrongStreak}`
      );

    }


    errorStatsHtml = `
      <div
        style="
          margin-top:0.5rem;
          font-size:0.85em;
          opacity:0.8;
        "
      >
        ${stats.join(" · ")}
      </div>
    `;

  }


  // ==========================================================
  // PREDICTED SUCCESS
  // ==========================================================

  const predictedSuccess =
    result.after
      ?.predicted_success;


  const predictionHtml =
    typeof predictedSuccess ===
    "number"
      ? `
          <div
            style="
              margin-top:0.5rem;
              font-size:0.85em;
              opacity:0.8;
            "
          >
            ML predicted success:
            <strong>
              ${Math.round(
                predictedSuccess * 100
              )}%
            </strong>
          </div>
        `
      : "";


  // ==========================================================
  // FINAL FEEDBACK
  // ==========================================================

  feedbackElement.innerHTML = `

    <div
      class="feedback-banner ${
        result.correct
          ? "correct"
          : "incorrect"
      }"
    >

      ${
        result.correct

          ? "✓ Correct!"

          : `
              ✗ Not quite —
              the answer was
              <strong>
                ${
                  result.answer?.correct
                    ? String(
                        result.answer.correct
                      ).toUpperCase()
                    : "—"
                }
              </strong>
            `
      }

    </div>


    <div class="feedback-mastery">

      ${escapeQuizHtml(
        formatQuizTopic(
          question.topic
        )
      )}
      mastery:

      <strong>
        ${afterMasteryText}
      </strong>

      ${masteryDeltaHtml}

    </div>


    ${predictionHtml}

    ${reasonsHtml}

    ${errorStatsHtml}

  `;


  const submitButton =
    document.getElementById(
      "submit-btn"
    );


  const nextButton =
    document.getElementById(
      "next-btn"
    );


  if (submitButton) {

    submitButton.style.display =
      "none";

  }


  if (nextButton) {

    nextButton.style.display =
      "inline-flex";

  }

}


// ============================================================
// NEXT QUESTION
// ============================================================

async function nextQuestion() {

  if (
    quizState.questionCount >=
    quizState.totalQuestions
  ) {

    showCompletion();

    return;

  }


  /*
     VERY IMPORTANT:

     Keep passing activeTopic.

     Example:
     activeTopic = ML

     Q1 → ML
     Q2 → ML
     Q3 → ML
     ...
  */

  await fetchNextQuestion(
    CURRENT_STUDENT.student_id,
    quizState.activeTopic
  );

}


// ============================================================
// QUIZ COMPLETION
// ============================================================

function showCompletion() {

  const activeSection =
    document.getElementById(
      "quiz-active"
    );


  const completionSection =
    document.getElementById(
      "quiz-completion"
    );


  if (activeSection) {

    activeSection.style.display =
      "none";

  }


  if (completionSection) {

    completionSection.style.display =
      "block";

  }


  const progress =
    document.getElementById(
      "progress-fill"
    );


  if (progress) {

    progress.style.width =
      "100%";

  }


  const total =
    quizState.answers.length;


  const correct =
    quizState.answers.filter(
      answer =>
        answer.is_correct
    ).length;


  const percentage =
    total > 0
      ? Math.round(
          (
            correct /
            total
          ) * 100
        )
      : 0;


  const scoreElement =
    document.getElementById(
      "completion-score"
    );


  const percentageElement =
    document.getElementById(
      "completion-pct"
    );


  if (scoreElement) {

    scoreElement.textContent =
      `${correct}/${total}`;

  }


  if (percentageElement) {

    percentageElement.textContent =
      `${percentage}% correct`;

  }


  const requizButton =
    document.getElementById(
      "requiz-btn"
    );


  if (requizButton) {

    requizButton.style.display =
      percentage < 70
        ? "inline-flex"
        : "none";

  }

}


// ============================================================
// RE-QUIZ SAME TOPIC
// ============================================================

function restartQuiz() {

  /*
     If user was doing ML:
     re-quiz stays ML.

     If user was doing LSTM:
     re-quiz stays LSTM.
  */

  loadQuiz(
    CURRENT_STUDENT.student_id,
    quizState.activeTopic
  );

}


// ============================================================
// LOADING
// ============================================================

function showLoading(on) {

  const button =
    document.getElementById(
      "submit-btn"
    );


  if (!button) {
    return;
  }


  if (on) {

    button.disabled =
      true;


    button.textContent =
      "Loading…";

  } else {

    button.textContent =
      "Submit Answer";

  }

}


// ============================================================
// ERROR
// ============================================================

function showError(message) {

  const feedbackElement =
    document.getElementById(
      "feedback-area"
    );


  if (feedbackElement) {

    feedbackElement.innerHTML = `

      <div class="feedback-banner incorrect">

        ⚠ ${escapeQuizHtml(message)}

      </div>

    `;

  }

}


// ============================================================
// FORMAT TOPIC
// ============================================================

function formatQuizTopic(topic) {

  if (!topic) {
    return "Topic";
  }


  return String(topic)
    .replaceAll(
      "_",
      " "
    );

}


// ============================================================
// FORMAT REASON
// ============================================================

function formatQuizReason(reason) {

  if (!reason) {
    return "";
  }


  const text =
    String(reason)
      .replaceAll(
        "_",
        " "
      );


  return (
    text.charAt(0)
      .toUpperCase() +
    text.slice(1)
  );

}


// ============================================================
// CAPITALIZE
// ============================================================

function capitalizeQuizText(value) {

  if (!value) {
    return "";
  }


  const text =
    String(value);


  return (
    text.charAt(0)
      .toUpperCase() +
    text.slice(1)
  );

}


// ============================================================
// SAFE HTML
// ============================================================

function escapeQuizHtml(value) {

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
      !CURRENT_STUDENT.student_id
    ) {
      return;
    }


    /*
       Example:

       URL:
       quiz.html?topic=ML

       requestedTopic:
       ML
    */

    loadQuiz(
      CURRENT_STUDENT.student_id,
      requestedTopic
    );

  }
);