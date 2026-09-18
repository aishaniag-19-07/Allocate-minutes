// ============================================================
// A.M. - ALLOCATE MINUTES
// Interactive landing page
// ============================================================


// -----------------------------
// DOM
// -----------------------------

const navbar = document.querySelector(".navbar");
const menuButton = document.getElementById("menuButton");

const navLinks = document.querySelectorAll(".nav-link");

const seeHowButton = document.getElementById("seeHowButton");
const scrollHint = document.getElementById("scrollHint");

const planRows = document.querySelectorAll(".plan-row");

const reasonBox = document.getElementById("reasonBox");
const reasonTitle = document.getElementById("reasonTitle");
const reasonText = document.getElementById("reasonText");
const closeReason = document.getElementById("closeReason");

const progressCircle = document.getElementById("progressCircle");
const progressNumber = document.getElementById("progressNumber");

const adaptButton = document.getElementById("adaptButton");

const modalOverlay = document.getElementById("modalOverlay");
const modalClose = document.getElementById("modalClose");

const startButtons = document.querySelectorAll("[data-start]");

const timeButtons = document.querySelectorAll("[data-time]");


// ============================================================
// MOBILE NAVIGATION
// ============================================================

menuButton.addEventListener("click", () => {
    navbar.classList.toggle("menu-open");
});

navLinks.forEach(link => {
    link.addEventListener("click", () => {
        navbar.classList.remove("menu-open");
    });
});


// ============================================================
// SMOOTH SCROLL
// ============================================================

seeHowButton.addEventListener("click", () => {
    document
        .getElementById("how")
        .scrollIntoView({
            behavior: "smooth"
        });
});


scrollHint.addEventListener("click", () => {
    document
        .getElementById("how")
        .scrollIntoView({
            behavior: "smooth"
        });
});


// ============================================================
// ACTIVE NAVIGATION
// ============================================================

const sections = document.querySelectorAll("main section[id]");

const sectionObserver = new IntersectionObserver(
    entries => {

        entries.forEach(entry => {

            if (!entry.isIntersecting) {
                return;
            }

            navLinks.forEach(link => {
                link.classList.remove("active");
            });

            const activeLink = document.querySelector(
                `.nav-link[href="#${entry.target.id}"]`
            );

            if (activeLink) {
                activeLink.classList.add("active");
            }

        });

    },
    {
        threshold: 0.35
    }
);

sections.forEach(section => {
    sectionObserver.observe(section);
});


// ============================================================
// PLAN EXPLANATIONS
// ============================================================

planRows.forEach(row => {

    row.addEventListener("click", () => {

        planRows.forEach(item => {
            item.classList.remove("active-plan");
        });

        row.classList.add("active-plan");

        const topic = row.dataset.topic;
        const reason = row.dataset.reason;

        reasonTitle.textContent = `${topic} is in your plan.`;
        reasonText.textContent = reason;

        reasonBox.classList.add("visible");

    });

});


closeReason.addEventListener("click", event => {

    event.stopPropagation();

    reasonBox.classList.remove("visible");

});


// ============================================================
// PROGRESS RING
// ============================================================

let progressAnimated = false;

function animateProgress(target) {

    if (progressAnimated) {
        return;
    }

    progressAnimated = true;

    let value = 0;

    const interval = setInterval(() => {

        value++;

        progressNumber.textContent = `${value}%`;

        const degrees = (value / 100) * 360;

        progressCircle.style.background =
            `conic-gradient(
                var(--coral) 0deg,
                var(--coral) ${degrees}deg,
                #eee8e3 ${degrees}deg
            )`;

        if (value >= target) {
            clearInterval(interval);
        }

    }, 18);

}


const progressObserver = new IntersectionObserver(
    entries => {

        if (entries[0].isIntersecting) {
            animateProgress(64);
        }

    },
    {
        threshold: 0.4
    }
);

progressObserver.observe(progressCircle);


// ============================================================
// ADAPTIVE PLAN DEMO
// ============================================================

let adapted = false;

const recursionBar =
    document.getElementById("recursionBar");

const treesBar =
    document.getElementById("treesBar");

const probabilityBar =
    document.getElementById("probabilityBar");

const pythonBar =
    document.getElementById("pythonBar");


const recursionMinutes =
    document.getElementById("recursionMinutes");

const treesMinutes =
    document.getElementById("treesMinutes");

const probabilityMinutes =
    document.getElementById("probabilityMinutes");

const pythonMinutes =
    document.getElementById("pythonMinutes");


const recursionReason =
    document.getElementById("recursionReason");

const comparisonLabel =
    document.getElementById("comparisonLabel");

const adaptMessage =
    document.getElementById("adaptMessage");


adaptButton.addEventListener("click", () => {

    adapted = !adapted;

    if (adapted) {

        // Updated allocation
        recursionBar.style.width = "38%";
        treesBar.style.width = "88%";
        probabilityBar.style.width = "62%";
        pythonBar.style.width = "38%";

        recursionMinutes.textContent = "15 min";
        treesMinutes.textContent = "35 min";
        probabilityMinutes.textContent = "25 min";
        pythonMinutes.textContent = "15 min";

        recursionReason.textContent =
            "Recent mastery improved";

        comparisonLabel.textContent =
            "UPDATED PLAN";

        adaptButton.innerHTML =
            `Reset plan <span>↺</span>`;

        adaptMessage.innerHTML = `
            <span>✓</span>

            <p>
                <strong>Your plan changed.</strong>
                Recursion improved from 31% to 46%,
                so more time has been moved toward Trees.
            </p>
        `;

    }

    else {

        // Original allocation
        recursionBar.style.width = "75%";
        treesBar.style.width = "62%";
        probabilityBar.style.width = "50%";
        pythonBar.style.width = "38%";

        recursionMinutes.textContent = "30 min";
        treesMinutes.textContent = "25 min";
        probabilityMinutes.textContent = "20 min";
        pythonMinutes.textContent = "15 min";

        recursionReason.textContent =
            "Needs attention";

        comparisonLabel.textContent =
            "CURRENT PLAN";

        adaptButton.innerHTML =
            `Simulate improvement <span>↗</span>`;

        adaptMessage.innerHTML = `
            <span>↗</span>

            <p>
                <strong>Your plan is ready.</strong>
                Complete a check-in and A.M. can
                redistribute your time.
            </p>
        `;

    }

});


// ============================================================
// GET STARTED MODAL
// ============================================================

function openModal() {

    modalOverlay.classList.add("visible");

    document.body.style.overflow = "hidden";

}


function closeModalWindow() {

    modalOverlay.classList.remove("visible");

    document.body.style.overflow = "";

}


startButtons.forEach(button => {

    button.addEventListener("click", openModal);

});


modalClose.addEventListener(
    "click",
    closeModalWindow
);


modalOverlay.addEventListener("click", event => {

    if (event.target === modalOverlay) {
        closeModalWindow();
    }

});


document.addEventListener("keydown", event => {

    if (
        event.key === "Escape" &&
        modalOverlay.classList.contains("visible")
    ) {
        closeModalWindow();
    }

});


// ============================================================
// TIME ALLOCATION DEMO
// ============================================================

const allocationRatios = {
    recursion: 30 / 90,
    trees: 25 / 90,
    probability: 20 / 90,
    python: 15 / 90
};


const modalRecursion =
    document.getElementById("modalRecursion");

const modalTrees =
    document.getElementById("modalTrees");

const modalProbability =
    document.getElementById("modalProbability");

const modalPython =
    document.getElementById("modalPython");


function calculateAllocation(totalMinutes) {

    let recursion =
        Math.round(
            totalMinutes *
            allocationRatios.recursion
        );

    let trees =
        Math.round(
            totalMinutes *
            allocationRatios.trees
        );

    let probability =
        Math.round(
            totalMinutes *
            allocationRatios.probability
        );

    let python =
        totalMinutes -
        recursion -
        trees -
        probability;


    modalRecursion.textContent =
        `${recursion} min`;

    modalTrees.textContent =
        `${trees} min`;

    modalProbability.textContent =
        `${probability} min`;

    modalPython.textContent =
        `${python} min`;

}


timeButtons.forEach(button => {

    button.addEventListener("click", () => {

        timeButtons.forEach(item => {
            item.classList.remove("selected");
        });

        button.classList.add("selected");

        const totalMinutes =
            Number(button.dataset.time);

        calculateAllocation(totalMinutes);

    });

});


// ============================================================
// START TODAY'S PLAN
// ============================================================

const startPlanButton =
    document.getElementById("startPlanButton");


startPlanButton.addEventListener("click", () => {

    const firstPlan =
        document.querySelector(".plan-row");

    firstPlan.classList.add("active-plan");

    reasonTitle.textContent =
        "Start with Recursion.";

    reasonText.textContent =
        "You have 30 minutes allocated here because it is currently your highest-priority concept.";

    reasonBox.classList.add("visible");

    startPlanButton.innerHTML =
        `Plan started <span>✓</span>`;

    startPlanButton.style.background =
        "#39704d";

});


// ============================================================
// SIGN IN PLACEHOLDER
// ============================================================

document
    .getElementById("signInButton")
    .addEventListener("click", () => {

        window.location.href = "login.html";

    });
