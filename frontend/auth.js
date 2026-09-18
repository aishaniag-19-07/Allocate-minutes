/* ============================================================
   A.M. — Authentication Module

   Authentication flow:
   Login Page
      ↓
   POST /auth/login
      ↓
   FastAPI checks students.csv
      ↓
   Valid student returned
      ↓
   Student session saved in localStorage
      ↓
   Dashboard / Quiz / Plan use the same student_id

   NOTE:
   Signup is temporarily disabled because new users must be
   created in the backend/database, not only in localStorage.
   ============================================================ */


// ============================================================
// CONFIGURATION
// ============================================================

const API_BASE_URL = "http://127.0.0.1:8000";
const SESSION_KEY = "am_current_user";


// ============================================================
// AUTHENTICATE USER
// ============================================================

async function authenticateUser(gmailId, pin) {

  // Basic frontend validation
  if (!gmailId || !pin) {
    return {
      success: false,
      message: "Please enter Gmail ID and PIN."
    };
  }

  try {

    const response = await fetch(
      `${API_BASE_URL}/auth/login`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({
          gmail_id: gmailId.trim(),
          pin: String(pin).trim()
        })
      }
    );


    // Safely read backend response
    let data = {};

    try {
      data = await response.json();
    } catch (error) {
      console.error(
        "Could not parse login response:",
        error
      );
    }


    // Login failed
    if (!response.ok) {

      return {
        success: false,
        message:
          data.detail ||
          "Invalid Gmail ID or PIN."
      };

    }


    // Extra safety check
    if (!data.student_id || !data.name) {

      console.error(
        "Invalid login response:",
        data
      );

      return {
        success: false,
        message:
          "Invalid student information received from server."
      };

    }


    // Save real backend student
    setLoggedInUser(data);


    return {
      success: true,
      user: data
    };


  } catch (error) {

    console.error(
      "Login API error:",
      error
    );


    return {
      success: false,
      message:
        "Cannot connect to backend server. Please make sure FastAPI is running."
    };

  }
}


// ============================================================
// SIGNUP
// ============================================================

/*
   IMPORTANT:

   Previously signup created fake students only inside
   localStorage.

   Example:
   frontend creates S005
   but backend S005 may already belong to another student.

   That causes serious student-data mismatch.

   Therefore signup is disabled until we create a real
   backend registration API.
*/

async function registerUser({
  name,
  email,
  username,
  password,
  grade,
  exam_goal,
  available_minutes_per_day
}) {

  if (!name || !email || !username || !password || !grade) {
    return {
      success: false,
      message: "Please fill in all required fields."
    };
  }

  try {

    const response = await fetch(
      `${API_BASE_URL}/auth/signup`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

body: JSON.stringify({
  name: name.trim(),
  gmail_id: email.trim(),
  username: username.trim(),
  pin: password.trim(),
  grade: grade,
  exam_goal: exam_goal,
  available_minutes_per_day: available_minutes_per_day
})
      }
    );

    let data = {};

    try {
      data = await response.json();
    } catch (error) {
      console.error(
        "Could not parse signup response:",
        error
      );
    }

if (!response.ok) {

  console.error("Signup backend error:", data);

  let errorMessage = "Could not create account.";

  if (typeof data.detail === "string") {
    errorMessage = data.detail;
  }

  else if (Array.isArray(data.detail)) {
    errorMessage = data.detail
      .map(err => {
        const field = err.loc?.[err.loc.length - 1] || "field";
        return `${field}: ${err.msg}`;
      })
      .join(" | ");
  }

  else if (data.detail && typeof data.detail === "object") {
    errorMessage =
      data.detail.message ||
      JSON.stringify(data.detail);
  }

  return {
    success: false,
    message: errorMessage
  };
}

    const user = data.student || data;

    setLoggedInUser(user);

    return {
      success: true,
      user: user
    };

  } catch (error) {

    console.error(
      "Signup API error:",
      error
    );

    return {
      success: false,
      message:
        "Cannot connect to backend server."
    };

  }
}


// ============================================================
// SESSION MANAGEMENT
// ============================================================

function setLoggedInUser(user) {

  const safeUser = {

    student_id: String(
      user.student_id
    ),

    name:
      user.name || "Student",

    grade:
      user.grade ?? null,

    exam_goal:
      user.exam_goal || "",

    available_minutes_per_day:
      Number(
        user.available_minutes_per_day
      ) || 0,

    avatar:
      user.name
        ? user.name
            .charAt(0)
            .toUpperCase()
        : "S"

  };


  localStorage.setItem(
    SESSION_KEY,
    JSON.stringify(safeUser)
  );

}


// ============================================================
// GET CURRENT LOGGED-IN USER
// ============================================================

function getLoggedInUser() {

  try {

    const data =
      localStorage.getItem(
        SESSION_KEY
      );


    if (!data) {
      return null;
    }


    const user =
      JSON.parse(data);


    // Check minimum required fields
    if (
      !user.student_id ||
      !user.name
    ) {

      console.warn(
        "Invalid user session found."
      );

      localStorage.removeItem(
        SESSION_KEY
      );

      return null;
    }


    return user;


  } catch (error) {

    console.error(
      "Error reading current user session:",
      error
    );


    localStorage.removeItem(
      SESSION_KEY
    );


    return null;

  }

}


// ============================================================
// CHECK AUTHENTICATION
// ============================================================

function isAuthenticated() {

  return getLoggedInUser() !== null;

}


// ============================================================
// LOGOUT USER
// ============================================================

function logoutUser() {

  localStorage.removeItem(
    SESSION_KEY
  );


  window.location.href =
    "login.html";

}


// ============================================================
// FORMAT STUDENT GRADE
// ============================================================

function formatGrade(grade) {

  if (
    grade === null ||
    grade === undefined ||
    grade === ""
  ) {
    return "Student";
  }


  const gradeText =
    String(grade);


  // If already "Grade 9"
  if (
    gradeText
      .toLowerCase()
      .startsWith("grade")
  ) {
    return gradeText;
  }


  return `Grade ${gradeText}`;

}


// ============================================================
// SYNC NAVBAR / PROFILE INFORMATION
// ============================================================

function syncNavbarAuth() {

  const user =
    getLoggedInUser();


  const isAuth =
    user !== null;


  // ==========================================================
  // 1. LANDING PAGE NAVBAR
  // ==========================================================

  const signInBtn =
    document.getElementById(
      "signInButton"
    );


  if (signInBtn) {

    if (
      isAuth &&
      user
    ) {

      const firstName =
        user.name
          .split(" ")[0];


      signInBtn.textContent =
        firstName;


      signInBtn.title =
        `Logged in as ${user.name}. Click to log out.`;


      signInBtn.onclick = () => {

        const shouldLogout =
          confirm(
            `Logged in as ${user.name}. Would you like to log out?`
          );


        if (shouldLogout) {
          logoutUser();
        }

      };


    } else {

      signInBtn.textContent =
        "Sign in";


      signInBtn.title =
        "Sign in";


      signInBtn.onclick = () => {

        window.location.href =
          "login.html";

      };

    }

  }


  // ==========================================================
  // 2. DASHBOARD TOPBAR PROFILE
  // ==========================================================

  const profileEl =
    document.querySelector(
      ".topbar .profile"
    );


  if (
    profileEl &&
    isAuth &&
    user
  ) {

    const nameSpan =
      profileEl.querySelector(
        "span"
      );


    const avatarDiv =
      profileEl.querySelector(
        "div"
      );


    if (nameSpan) {

      nameSpan.textContent =
        user.name
          .split(" ")[0];

    }


    if (avatarDiv) {

      avatarDiv.textContent =
        user.avatar;

    }


    profileEl.title =
      `Logged in as ${user.name} · Click to log out`;


    profileEl.style.cursor =
      "pointer";


    profileEl.onclick = () => {

      const shouldLogout =
        confirm(
          `Logged in as ${user.name}. Log out?`
        );


      if (shouldLogout) {
        logoutUser();
      }

    };

  }


  // ==========================================================
  // 3. QUIZ / PLAN PAGE STUDENT NAV
  // ==========================================================

  const studentNav =
    document.querySelector(
      ".app-nav__student"
    );


  if (
    studentNav &&
    isAuth &&
    user
  ) {

    const nameEl =
      document.getElementById(
        "student-name"
      );


    const metaEl =
      studentNav.querySelector(
        ".app-nav__student-meta"
      );


    const avatarEl =
      studentNav.querySelector(
        ".app-nav__avatar"
      );


    if (nameEl) {

      nameEl.textContent =
        user.name
          .split(" ")[0];

    }


    if (metaEl) {

      metaEl.textContent =
        formatGrade(
          user.grade
        );

    }


    if (avatarEl) {

      avatarEl.textContent =
        user.avatar;

    }


    studentNav.title =
      `Logged in as ${user.name} · Click to log out`;


    studentNav.style.cursor =
      "pointer";


    studentNav.onclick = () => {

      const shouldLogout =
        confirm(
          `Logged in as ${user.name}. Log out?`
        );


      if (shouldLogout) {
        logoutUser();
      }

    };

  }

}


// ============================================================
// OPTIONAL PAGE PROTECTION
// ============================================================

/*
   Use this function on pages that should only be accessible
   after login.

   Example inside planner.js / quiz.js:

   requireAuthentication();

*/

function requireAuthentication() {

  const user =
    getLoggedInUser();


  if (!user) {

    window.location.href =
      "login.html";


    return null;

  }


  return user;

}


// ============================================================
// AUTO SYNC WHEN PAGE LOADS
// ============================================================

if (
  typeof document !==
  "undefined"
) {

  document.addEventListener(
    "DOMContentLoaded",
    () => {

      syncNavbarAuth();

    }
  );

}