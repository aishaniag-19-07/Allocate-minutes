/* ============================================================
   A.M. DASHBOARD
   Real backend-connected dashboard

   APIs used:
   GET /student/{id}/mastery
   GET /student/{id}/weaknesses
   GET /student/{id}/plan
   GET /student/{id}/quiz?topic=...

   auth.js must load before this file.
   ============================================================ */


const DASHBOARD_API_BASE = API_BASE_URL;

let dashboardFocusTopic = null;
let dashboardWeaknessMap = {};
let dashboardPlanMap = {};


// ============================================================
// START DASHBOARD
// ============================================================

document.addEventListener("DOMContentLoaded", async () => {

    const user =
        typeof requireAuthentication === "function"
            ? requireAuthentication()
            : getLoggedInUser();

    if (!user) {
        return;
    }

    updateStudentName(user);
    updateTodayDate();

    await loadDashboard(user);

});


// ============================================================
// LOAD ALL DASHBOARD DATA
// ============================================================

async function loadDashboard(user) {

    try {

        const studentId =
            encodeURIComponent(user.student_id);


        const [
            masteryResponse,
            weaknessResponse,
            planResponse
        ] = await Promise.all([

            fetch(
                `${DASHBOARD_API_BASE}/student/${studentId}/mastery`
            ),

            fetch(
                `${DASHBOARD_API_BASE}/student/${studentId}/weaknesses`
            ),

            fetch(
                `${DASHBOARD_API_BASE}/student/${studentId}/plan`
            )

        ]);


        if (
            !masteryResponse.ok ||
            !weaknessResponse.ok ||
            !planResponse.ok
        ) {

            throw new Error(
                "One or more dashboard APIs failed."
            );

        }


        const masteryData =
            await masteryResponse.json();

        const weaknessData =
            await weaknessResponse.json();

        const planData =
            await planResponse.json();


        console.log(
            "Mastery:",
            masteryData
        );

        console.log(
            "Weaknesses:",
            weaknessData
        );

        console.log(
            "Plan:",
            planData
        );


        updateAvailableTime(
            planData.available_minutes ??
            user.available_minutes_per_day ??
            0
        );


        prepareWeaknessMap(
            weaknessData
        );


        preparePlanMap(
            planData
        );


        renderStudyPlan(
            planData
        );


        renderPriorityAreas(
            weaknessData
        );


        // Choose strongest priority / weakest topic
        const weaknesses =
            weaknessData.weaknesses || [];


        dashboardFocusTopic =
            weaknesses.length > 0
                ? weaknesses[0].topic
                : getFirstPlanTopic(planData);


        if (dashboardFocusTopic) {

            const weakness =
                dashboardWeaknessMap[
                    dashboardFocusTopic
                ];

            renderReasonSection(
                weakness ||
                dashboardPlanMap[
                    dashboardFocusTopic
                ]
            );

            updateConceptMapFocus(
                dashboardFocusTopic,
                weakness?.mastery_score ?? weakness?.mastery ?? null
            );


            await updateQuizPreview(
                user.student_id,
                dashboardFocusTopic
            );

        }


        /*
           Backend currently does not provide genuine
           weekly-history data.

           Hide the old demo-only sections instead of
           showing fake Recursion / weekly progress.
        */

        hideUnsupportedDemoSections();


    } catch (error) {

        console.error(
            "Dashboard loading error:",
            error
        );

        showDashboardError();

    }

}


// ============================================================
// STUDENT NAME
// ============================================================

function updateStudentName(user) {

    const firstName =
        (user.name || "Student")
            .split(" ")[0];


    const welcomeHeading =
        document.querySelector(
            ".welcome h1"
        );


    if (welcomeHeading) {

        welcomeHeading.innerHTML =
            `Good morning, <em>${escapeHtml(firstName)}.</em>`;

    }

}


// ============================================================
// TODAY DATE
// ============================================================

function updateTodayDate() {

    const dateElement =
        document.querySelector(
            ".topbar .date strong"
        );


    if (!dateElement) {
        return;
    }


    const today =
        new Date();


    const day =
        String(
            today.getDate()
        ).padStart(2, "0");


    const month =
        today
            .toLocaleString(
                "en-US",
                {
                    month: "short"
                }
            )
            .toUpperCase();


    const weekday =
        today
            .toLocaleString(
                "en-US",
                {
                    weekday: "long"
                }
            )
            .toUpperCase();


    dateElement.textContent =
        `${day} ${month} · ${weekday}`;

}


// ============================================================
// AVAILABLE STUDY TIME
// ============================================================

function updateAvailableTime(minutes) {

    const safeMinutes =
        Number(minutes) || 0;


    // Welcome text
    const welcomeText =
        document.querySelector(
            ".welcome p"
        );


    if (welcomeText) {

        welcomeText.innerHTML =
            `You have <strong>${safeMinutes} minutes</strong> today.
             Here's where they can make the most difference.`;

    }


    // Large time display
    const timeNumber =
        document.querySelector(
            ".today-time strong"
        );


    if (timeNumber) {

        timeNumber.textContent =
            safeMinutes;

    }


    // Plan heading
    const planHeading =
        document.querySelector(
            ".plan-panel .panel-heading h2"
        );


    if (planHeading) {

        planHeading.textContent =
            `Your ${safeMinutes} minutes.`;

    }


    // Estimated completion time
    const doneBy =
        document.querySelector(
            ".plan-end strong"
        );


    if (doneBy) {

        const finish =
            new Date(
                Date.now() +
                safeMinutes * 60000
            );


        doneBy.textContent =
            finish.toLocaleTimeString(
                [],
                {
                    hour: "2-digit",
                    minute: "2-digit"
                }
            );

    }

}


// ============================================================
// PREPARE WEAKNESS LOOKUP
// ============================================================

function prepareWeaknessMap(
    weaknessData
) {

    dashboardWeaknessMap = {};


    const weaknesses =
        weaknessData.weaknesses || [];


    weaknesses.forEach(
        weakness => {

            dashboardWeaknessMap[
                weakness.topic
            ] = weakness;

        }
    );

}


// ============================================================
// PREPARE PLAN LOOKUP
// ============================================================

function preparePlanMap(
    planData
) {

    dashboardPlanMap = {};


    const plan =
        planData.plan || [];


    plan.forEach(
        item => {

            dashboardPlanMap[
                item.topic
            ] = item;

        }
    );

}


// ============================================================
// STUDY PLAN TIMELINE
// ============================================================

function renderStudyPlan(
    planData
) {

    const timeline =
        document.querySelector(
            ".timeline"
        );


    if (!timeline) {
        return;
    }


    const plan =
        planData.plan || [];


    const summaries =
        planData.weak_topics_summary || [];


    if (!plan.length) {

        timeline.innerHTML = `
            <p>
                No study plan is available yet.
            </p>
        `;

        return;

    }


    let currentTime =
        roundTimeToFiveMinutes(
            new Date()
        );


    timeline.innerHTML =
        plan.map(
            (item, index) => {

                const summary =
                    summaries.find(
                        topic =>
                            topic.topic ===
                            item.topic
                    );


                const mastery =
                    summary &&
                    summary.mastery !== null &&
                    summary.mastery !== undefined
                        ? Number(
                            summary.mastery
                        )
                        : null;


                const masteryText =
                    mastery !== null
                        ? `${Math.round(mastery)}%`
                        : "—";


                const masteryWidth =
                    mastery !== null
                        ? clamp(
                            mastery,
                            0,
                            100
                        )
                        : 0;


                const startTime =
                    formatTime(
                        currentTime
                    );


                currentTime =
                    new Date(
                        currentTime.getTime() +
                        Number(item.minutes || 0)
                            * 60000
                    );


                const style =
                    getTimelineStyle(
                        index,
                        item.topic
                    );


                return `
                    <div
                        class="timeline-item ${index === 0 ? "active" : ""}"
                        data-topic="${escapeHtml(item.topic)}"
                    >

                        <div class="timeline-time">

                            <strong>
                                ${startTime}
                            </strong>

                            <span>
                                ${Number(item.minutes || 0)} min
                            </span>

                        </div>


                        <div class="timeline-track ${index === plan.length - 1 ? "last" : ""}">

                            <i class="dot ${style.dotClass}"></i>

                        </div>


                        <div class="timeline-info">

                            <div class="topic-heading">

                                <div>

                                    <span>
                                        ADAPTIVE PLAN
                                    </span>

                                    <h3>
                                        ${formatTopic(item.topic)}
                                    </h3>

                                </div>


                                <span class="tag ${style.tagClass}">
                                    ${style.tagText}
                                </span>

                            </div>


                            <p>
                                ${escapeHtml(item.reason || "Recommended study block")}
                            </p>


                            <div class="mastery">

                                <div>

                                    <span
                                        style="width:${masteryWidth}%"
                                    ></span>

                                </div>

                                <strong>
                                    ${masteryText}
                                </strong>

                            </div>

                        </div>

                    </div>
                `;

            }
        ).join("");


    addTimelineClickEvents();

}


// ============================================================
// TIMELINE CLICK
// ============================================================

function addTimelineClickEvents() {

    const items =
        document.querySelectorAll(
            ".timeline-item"
        );


    items.forEach(
        item => {

            item.addEventListener(
                "click",
                async () => {

                    items.forEach(
                        other => {

                            other.classList.remove(
                                "active"
                            );

                        }
                    );


                    item.classList.add(
                        "active"
                    );


                    const topic =
                        item.dataset.topic;


                    dashboardFocusTopic =
                        topic;


                    const data =
                        dashboardWeaknessMap[
                            topic
                        ] ||
                        dashboardPlanMap[
                            topic
                        ];


                    renderReasonSection(
                        data
                    );


                    const user =
                        getLoggedInUser();


                    if (
                        user &&
                        topic !== "Revision"
                    ) {

                        await updateQuizPreview(
                            user.student_id,
                            topic
                        );

                    }

                }
            );

        }
    );

}


// ============================================================
// PRIORITY AREAS
// ============================================================

function renderPriorityAreas(
    weaknessData
) {

    const priorityList =
        document.querySelector(
            ".priority-list"
        );


    const count =
        document.querySelector(
            ".attention-panel .count"
        );


    if (!priorityList) {
        return;
    }


    const weaknesses =
        weaknessData.weaknesses || [];


    const topWeaknesses =
        weaknesses.slice(0, 3);


    if (count) {

        count.textContent =
            topWeaknesses.length;

    }


    if (!topWeaknesses.length) {

        priorityList.innerHTML = `
            <p>
                No major weak topics detected.
            </p>
        `;

        return;

    }


    priorityList.innerHTML =
        topWeaknesses.map(
            (item, index) => {

                const reason =
                    item.reasons &&
                    item.reasons.length
                        ? item.reasons[0]
                        : "Needs more practice";


                return `
                    <div class="priority-item">

                        <span class="number">
                            ${String(index + 1).padStart(2, "0")}
                        </span>


                        <div>

                            <strong>
                                ${formatTopic(item.topic)}
                            </strong>

                            <small>
                                ${escapeHtml(reason)}
                            </small>

                        </div>


                        <strong class="score">
                            ${Math.round(Number(item.mastery || 0))}%
                        </strong>

                    </div>
                `;

            }
        ).join("");

}


// ============================================================
// WHY THIS PLAN?
// ============================================================

function renderReasonSection(
    data
) {

    if (!data) {
        return;
    }


    const topic =
        data.topic || "Topic";


    const title =
        document.getElementById(
            "reasonTitle"
        );


    const text =
        document.getElementById(
            "reasonText"
        );


    const mastery =
        document.getElementById(
            "reasonMastery"
        );


    const accuracy =
        document.getElementById(
            "reasonAccuracy"
        );


    const errors =
        document.getElementById(
            "reasonErrors"
        );


    if (title) {

        title.textContent =
            `${formatTopic(topic)} needs attention.`;

    }


    if (text) {

        if (
            data.reasons &&
            data.reasons.length
        ) {

            text.textContent =
                data.reasons
                    .map(formatReason)
                    .join(". ") + ".";

        } else {

            text.textContent =
                data.reason ||
                "This topic is included based on your current learning profile.";

        }

    }


    if (mastery) {

        mastery.textContent =
            data.mastery !== undefined
                ? `${Math.round(Number(data.mastery))}%`
                : "—";

    }


    if (accuracy) {

        if (
            data.accuracy !== undefined
        ) {

            accuracy.textContent =
                `${Math.round(
                    Number(data.accuracy) * 100
                )}%`;

        } else {

            accuracy.textContent =
                "—";

        }

    }


    if (errors) {

        errors.textContent =
            data.repeated_question_errors !== undefined
                ? data.repeated_question_errors
                : "—";

    }


    updateConceptPath(
        data
    );

}


// ============================================================
// CONCEPT / DEPENDENCY PATH
// ============================================================

function updateConceptPath(
    data
) {

    const conceptPath =
        document.querySelector(
            ".concept-path"
        );


    if (!conceptPath) {
        return;
    }


    const weakPrerequisites =
        data.weak_prerequisites || [];


    const prerequisites =
        data.prerequisites || [];


    const source =
        weakPrerequisites[0] ||
        prerequisites[0];


    if (!source) {

        conceptPath.style.display =
            "none";

        return;

    }


    conceptPath.style.display =
        "";


    const container =
        conceptPath.querySelector(
            "div"
        );


    if (!container) {
        return;
    }


    container.innerHTML = `

        <span>
            ${formatTopic(source)}
        </span>

        <i></i>

        <strong>
            ${formatTopic(data.topic)}
        </strong>

    `;

}


// ============================================================
// QUIZ PREVIEW
// ============================================================

async function updateQuizPreview(
    studentId,
    topic
) {

    if (
        !studentId ||
        !topic ||
        topic === "Revision"
    ) {
        return;
    }


    try {

        const response =
            await fetch(
                `${DASHBOARD_API_BASE}/student/${encodeURIComponent(studentId)}/quiz?topic=${encodeURIComponent(topic)}`
            );


        if (!response.ok) {

            throw new Error(
                "Quiz preview API failed."
            );

        }


        const quiz =
            await response.json();


        const values =
            document.querySelectorAll(
                ".quiz-meta strong"
            );


        // Current quiz.js has 7 questions
        if (values[0]) {
            values[0].textContent =
                "7";
        }


        if (values[1]) {
            values[1].textContent =
                formatTopic(
                    quiz.topic
                );
        }


        if (values[2]) {
            values[2].textContent =
                capitalize(
                    quiz.difficulty_label ||
                    "adaptive"
                );
        }


        const button =
            document.getElementById(
                "adaptiveQuizButton"
            );


        if (button) {

            button.onclick = () => {

                window.location.href =
                    `quiz.html?topic=${encodeURIComponent(quiz.topic)}`;

            };

        }


    } catch (error) {

        console.error(
            "Quiz preview error:",
            error
        );

    }

}


// ============================================================
// FIRST PLAN TOPIC
// ============================================================

function getFirstPlanTopic(
    planData
) {

    const plan =
        planData.plan || [];


    const first =
        plan.find(
            item =>
                item.topic &&
                item.topic !== "Revision"
        );


    return first
        ? first.topic
        : null;

}


// ============================================================
// HIDE DEMO-ONLY SECTIONS
// ============================================================

function hideUnsupportedDemoSections() {

    /*
       These sections currently contain fake historical
       Recursion/week values.

       We do NOT have a weekly-history API yet, so hiding
       them is safer than displaying fake information.
    */

    const progressGrid =
        document.querySelector(
            ".progress-grid"
        );


    if (progressGrid) {

        progressGrid.style.display =
            "none";

    }


    const adaptiveNote =
        document.querySelector(
            ".adaptive-note"
        );


    if (adaptiveNote) {

        adaptiveNote.style.display =
            "none";

    }

}


// ============================================================
// DASHBOARD ERROR MESSAGE
// ============================================================

function showDashboardError() {

    const timeline =
        document.querySelector(
            ".timeline"
        );


    if (timeline) {

        timeline.innerHTML = `

            <div style="
                padding:20px;
                line-height:1.6;
            ">

                Could not load your study data.

                <br>

                Make sure the FastAPI backend is running on:

                <br>

                <strong>
                    http://127.0.0.1:8000
                </strong>

            </div>

        `;

    }

}


// ============================================================
// TIMELINE STYLE
// ============================================================

function getTimelineStyle(
    index,
    topic
) {

    if (
        topic === "Revision"
    ) {

        return {
            dotClass: "navy",
            tagClass: "review",
            tagText: "REVIEW"
        };

    }


    if (index === 0) {

        return {
            dotClass: "coral",
            tagClass: "focus",
            tagText: "FOCUS FIRST"
        };

    }


    if (index === 1) {

        return {
            dotClass: "amber",
            tagClass: "next",
            tagText: "BUILDS NEXT"
        };

    }


    return {
        dotClass: "green",
        tagClass: "steady",
        tagText: "KEEP GOING"
    };

}


// ============================================================
// HELPERS
// ============================================================

function formatTopic(
    topic
) {

    if (!topic) {
        return "";
    }


    return String(topic)
        .replaceAll("_", " ");

}


function formatReason(
    reason
) {

    if (!reason) {
        return "";
    }


    const text =
        String(reason);


    return (
        text.charAt(0).toUpperCase() +
        text.slice(1)
    );

}


function capitalize(
    value
) {

    if (!value) {
        return "";
    }


    const text =
        String(value);


    return (
        text.charAt(0).toUpperCase() +
        text.slice(1)
    );

}


function clamp(
    value,
    min,
    max
) {

    return Math.min(
        max,
        Math.max(
            min,
            Number(value) || 0
        )
    );

}


function roundTimeToFiveMinutes(
    date
) {

    const result =
        new Date(date);


    const minutes =
        result.getMinutes();


    const rounded =
        Math.ceil(
            minutes / 5
        ) * 5;


    result.setMinutes(
        rounded,
        0,
        0
    );


    return result;

}


function formatTime(
    date
) {

    return date.toLocaleTimeString(
        [],
        {
            hour: "2-digit",
            minute: "2-digit"
        }
    );

}


function escapeHtml(
    value
) {

    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}
// ============================================================
// CONCEPT MAP + STUDY ASSISTANT
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
    setupStudyAssistant();
});

function setupStudyAssistant() {
    const launcher = document.getElementById("chatLauncher");
    const windowEl = document.getElementById("chatWindow");
    const close = document.getElementById("closeChat");
    const form = document.getElementById("chatForm");
    const input = document.getElementById("chatInput");

    if (!launcher || !windowEl || !form || !input) return;

    const setOpen = (open) => {
        windowEl.classList.toggle("open", open);
        windowEl.setAttribute("aria-hidden", String(!open));
        if (open) setTimeout(() => input.focus(), 80);
    };

    launcher.addEventListener("click", () => setOpen(!windowEl.classList.contains("open")));
    close?.addEventListener("click", () => setOpen(false));

    document.querySelectorAll("[data-chat-prompt]").forEach(button => {
        button.addEventListener("click", () => submitStudyQuestion(button.dataset.chatPrompt));
    });

    form.addEventListener("submit", event => {
        event.preventDefault();
        const question = input.value.trim();
        if (!question) return;
        input.value = "";
        submitStudyQuestion(question);
    });
}

function submitStudyQuestion(question) {
    addChatMessage(question, "user");
    const topic = dashboardFocusTopic || "your current focus topic";
    const weakness = dashboardWeaknessMap[topic] || {};
    const q = question.toLowerCase();
    let answer;

    if (q.includes("why") || q.includes("important")) {
        answer = `${topic} is prioritized because your recent performance marks it as a weak area. Strengthening it now also protects the concepts that depend on it, so your study time has more downstream impact.`;
    } else if (q.includes("next")) {
        answer = `Start with ${topic}, then move to the next connected concept in your plan. Use the concept map to see the dependency path, and take the adaptive quiz afterward so tomorrow's allocation can update from fresh evidence.`;
    } else if (q.includes("simple") || q.includes("explain")) {
        answer = `${topic} is your focus block right now. Break it into one small idea, solve a few targeted questions, then check whether the same mistake repeats. That is more useful than rereading the whole chapter.`;
    } else if (q.includes("mastery") || q.includes("score")) {
        const score = weakness.mastery_score ?? weakness.mastery ?? null;
        answer = score !== null ? `Your current ${topic} mastery is about ${Math.round(Number(score) * (Number(score) <= 1 ? 100 : 1))}%. The planner combines performance signals to decide its priority.` : `Your dashboard uses mastery and recent error signals to rank ${topic}. Check the priority card for the latest score from the backend.`;
    } else {
        answer = `For ${topic}, I would keep today's plan narrow: understand the exact mistake pattern, practice a small targeted set, then use the adaptive quiz to measure whether it improved. Ask me “why this topic?”, “explain simply”, or “what next?” for a focused answer.`;
    }

    setTimeout(() => addChatMessage(answer, "bot"), 180);
}

function addChatMessage(text, type) {
    const messages = document.getElementById("chatMessages");
    if (!messages) return;
    const bubble = document.createElement("div");
    bubble.className = `chat-message ${type}`;
    const p = document.createElement("p");
    p.textContent = text;
    bubble.appendChild(p);
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
}

function updateConceptMapFocus(topic, mastery) {
    const topicEl = document.getElementById("mapFocusTopic");
    const masteryEl = document.getElementById("mapFocusMastery");
    if (topicEl && topic) topicEl.textContent = topic;
    if (masteryEl && mastery !== undefined && mastery !== null) {
        let value = Number(mastery);
        if (value <= 1) value *= 100;
        masteryEl.textContent = `${Math.round(value)}% mastery`;
    }
}
