/* ============================================================
   NEURALQUEST — AI Knowledge Gaming Platform Client Logic
   Interactive Quiz Arena, Timers, Flashcards, Chat & Gamification
   ============================================================ */

"use strict";

/* ─── API CONFIGURATION ──────────────────────────────────── */
const API_BASE = "/api";

/* ─── STATE ──────────────────────────────────────────────── */
let currentUser        = null;
let currentProfile     = null;
let currentQuiz        = null;
let currentSession     = null;
let activeQuestions    = [];
let currentQuestionIdx = 0;
let userStreak         = 0;
let activeTimer        = null;
let timeRemaining      = 15;
let questionStartTime  = 0;
let currentDocList     = [];

/* ─── DOM ELEMENTS ───────────────────────────────────────── */
const authSection        = document.getElementById("authSection");
const dashboardSection   = document.getElementById("dashboardSection");
const contentViewport    = document.getElementById("contentViewport");

// HUD Elements
const hudLevelVal        = document.getElementById("hudLevelVal");
const hudXpVal           = document.getElementById("hudXpVal");
const hudStreakVal       = document.getElementById("hudStreakVal");
const usernameDisplay    = document.getElementById("usernameDisplay");
const userAvatar         = document.getElementById("userAvatar");
const globalStatus       = document.getElementById("globalStatus");
const statusText         = document.getElementById("statusText");

// Auth
const loginForm          = document.getElementById("loginForm");
const registerForm       = document.getElementById("registerForm");
const loginBtn           = document.getElementById("loginBtn");
const registerBtn        = document.getElementById("registerBtn");
const tabLogin           = document.getElementById("tab-login");
const tabRegister        = document.getElementById("tab-register");
const authMessage        = document.getElementById("authMessage");
const logoutBtn          = document.getElementById("logoutBtn");

// Navigation
const navItems           = document.querySelectorAll(".nav-item");
const viewPanels         = document.querySelectorAll(".view-panel");
const mobileNavToggle    = document.getElementById("mobileNavToggle");
const mainSidebar        = document.getElementById("mainSidebar");

// Dashboard & Doc widgets
const statXp             = document.getElementById("statXp");
const statLevel          = document.getElementById("statLevel");
const statStreak         = document.getElementById("statStreak");
const statAccuracy       = document.getElementById("statAccuracy");
const statGames          = document.getElementById("statGames");
const statDocs           = document.getElementById("statDocs");
const sidebarDocCount    = document.getElementById("sidebarDocCount");
const dashDocSelect      = document.getElementById("dashDocSelect");
const dashModeSelect     = document.getElementById("dashModeSelect");
const dashDiffSelect     = document.getElementById("dashDiffSelect");
const dashStartQuizBtn   = document.getElementById("dashStartQuizBtn");
const recentQuizzesList  = document.getElementById("recentQuizzesList");
const quickPlayBtn       = document.getElementById("quickPlayBtn");

// Documents
const uploadBtn          = document.getElementById("uploadBtn");
const fileInput          = document.getElementById("fileInput");
const uploadProgress     = document.getElementById("uploadProgress");
const progressBar        = document.getElementById("progressBar");
const uploadStatusText   = document.getElementById("uploadStatusText");
const documentsList      = document.getElementById("documentsList");
const kbUploadTriggerBtn = document.getElementById("kbUploadTriggerBtn");

// Quiz Arena
const arenaModeBadge     = document.getElementById("arenaModeBadge");
const arenaQuizTitle     = document.getElementById("arenaQuizTitle");
const arenaDocSource     = document.getElementById("arenaDocSource");
const arenaTimerBox      = document.getElementById("arenaTimerBox");
const arenaTimerVal      = document.getElementById("arenaTimerVal");
const arenaScore         = document.getElementById("arenaScore");
const arenaXpEarned      = document.getElementById("arenaXpEarned");
const arenaProgressBar   = document.getElementById("arenaProgressBar");
const arenaProgressText  = document.getElementById("arenaProgressText");
const arenaStreakCounter = document.getElementById("arenaStreakCounter");

const questionCard       = document.getElementById("questionCard");
const qNumberPill        = document.getElementById("qNumberPill");
const arenaQuestionText  = document.getElementById("arenaQuestionText");
const arenaOptionsGrid   = document.getElementById("arenaOptionsGrid");
const arenaFeedbackBox   = document.getElementById("arenaFeedbackBox");
const feedbackIcon       = document.getElementById("feedbackIcon");
const feedbackTitle      = document.getElementById("feedbackTitle");
const feedbackXp         = document.getElementById("feedbackXp");
const feedbackExplanation= document.getElementById("feedbackExplanation");
const citationText       = document.getElementById("citationText");
const arenaNextBtn       = document.getElementById("arenaNextBtn");

// Flashcard Mode
const flashcardContainer = document.getElementById("flashcardContainer");
const flashcardElement   = document.getElementById("flashcardElement");
const fcFrontText        = document.getElementById("fcFrontText");
const fcBackAnswer       = document.getElementById("fcBackAnswer");
const fcBackExplanation  = document.getElementById("fcBackExplanation");
const fcCitation         = document.getElementById("fcCitation");
const fcPrevBtn          = document.getElementById("fcPrevBtn");
const fcFlipBtn          = document.getElementById("fcFlipBtn");
const fcNextBtn          = document.getElementById("fcNextBtn");

// Results Screen
const arenaResultsScreen = document.getElementById("arenaResultsScreen");
const victorySubtitle    = document.getElementById("victorySubtitle");
const resScore           = document.getElementById("resScore");
const resAccuracy        = document.getElementById("resAccuracy");
const resXp              = document.getElementById("resXp");
const resDashboardBtn    = document.getElementById("resDashboardBtn");
const resPlayAgainBtn    = document.getElementById("resPlayAgainBtn");

// Chat
const chatMessages       = document.getElementById("chatMessages");
const questionInput      = document.getElementById("questionInput");
const sendBtn            = document.getElementById("sendBtn");
const clearChatBtn       = document.getElementById("clearChatBtn");

// Modals & Toast
const toast              = document.getElementById("toast");
let toastTimeout         = null;
const confirmModal       = document.getElementById("confirmModal");
const confirmOk          = document.getElementById("confirmOk");
const confirmCancel      = document.getElementById("confirmCancel");
let pendingDeleteId      = null;


/* ============================================================
   INITIALIZATION & AUTHENTICATION
   ============================================================ */
function getToken() { return localStorage.getItem("authToken"); }
function authHeaders() { return { "Authorization": `Token ${getToken()}`, "Content-Type": "application/json" }; }

function showToast(message, type = "info") {
    if (toastTimeout) clearTimeout(toastTimeout);
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    toastTimeout = setTimeout(() => { toast.classList.remove("show"); }, 3400);
}

function setStatus(text, state = "ready") {
    if (statusText) statusText.textContent = text;
    const dot = globalStatus?.querySelector(".status-dot");
    if (dot) dot.className = `status-dot ${state}`;
}

// Tab Switching
tabLogin?.addEventListener("click", () => switchTab("login"));
tabRegister?.addEventListener("click", () => switchTab("register"));

function switchTab(tab) {
    if (tab === "login") {
        loginForm.classList.remove("hidden");
        registerForm.classList.add("hidden");
        tabLogin.classList.add("active");
        tabRegister.classList.remove("active");
    } else {
        registerForm.classList.remove("hidden");
        loginForm.classList.add("hidden");
        tabRegister.classList.add("active");
        tabLogin.classList.remove("active");
    }
    setAuthMessage("");
}

function setAuthMessage(text, type = "") {
    if (!authMessage) return;
    authMessage.textContent = text;
    authMessage.className = `auth-message ${type}`;
    authMessage.style.display = text ? "block" : "none";
}

loginBtn?.addEventListener("click", loginUser);
document.getElementById("loginUsername")?.addEventListener("keydown", e => { if (e.key === "Enter") loginUser(); });
document.getElementById("loginPassword")?.addEventListener("keydown", e => { if (e.key === "Enter") loginUser(); });

async function loginUser() {
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;
    if (!username || !password) { setAuthMessage("Call-sign and Access Key required.", "error"); return; }

    setAuthMessage("Entering Arena…", "info");
    loginBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/auth/login/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (!res.ok) { setAuthMessage(data.detail || data.error || "Authentication failed.", "error"); return; }

        localStorage.setItem("authToken", data.token);
        showToast(`Welcome to NeuralQuest, Commander ${username}! ⚔️`, "success");
        await enterDashboard(data.user);
    } catch {
        setAuthMessage("Unable to connect to game server.", "error");
    } finally {
        loginBtn.disabled = false;
    }
}

registerBtn?.addEventListener("click", registerUser);
async function registerUser() {
    const username = document.getElementById("registerUsername").value.trim();
    const email    = document.getElementById("registerEmail").value.trim();
    const password = document.getElementById("registerPassword").value;

    if (!username || !password) { setAuthMessage("Call-sign and password are required.", "error"); return; }
    setAuthMessage("Minting player profile…", "info");
    registerBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/auth/register/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, password }),
        });
        const data = await res.json();
        if (!res.ok) {
            const msg = Object.values(data).flat().join(" ") || "Registration failed.";
            setAuthMessage(msg, "error");
            return;
        }
        localStorage.setItem("authToken", data.token);
        showToast("Player registered! Welcome to the Arena 🎉", "success");
        await enterDashboard(data.user);
    } catch {
        setAuthMessage("Unable to connect to game server.", "error");
    } finally {
        registerBtn.disabled = false;
    }
}

logoutBtn?.addEventListener("click", () => {
    localStorage.removeItem("authToken");
    authSection.classList.remove("hidden");
    dashboardSection.classList.add("hidden");
    showToast("Signed out from the Arena.", "info");
});

async function enterDashboard(user) {
    currentUser = user;
    authSection.classList.add("hidden");
    dashboardSection.classList.remove("hidden");

    if (user?.username) {
        usernameDisplay.textContent = user.username;
        userAvatar.textContent = user.username[0].toUpperCase();
    }

    await Promise.all([
        loadPlayerProfile(),
        loadDocuments(),
        loadRecentQuizzes(),
        loadChatHistory(),
    ]);
}

// Auto Login
(async function init() {
    initParticles();
    const token = getToken();
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/auth/me/`, { headers: authHeaders() });
        if (!res.ok) { localStorage.removeItem("authToken"); return; }
        const user = await res.json();
        await enterDashboard(user);
    } catch {
        localStorage.removeItem("authToken");
    }
})();


/* ============================================================
   NAVIGATION & VIEW SWITCHING
   ============================================================ */
navItems.forEach(btn => {
    btn.addEventListener("click", () => {
        const targetView = btn.getAttribute("data-view");
        switchView(targetView);
        if (window.innerWidth <= 768) mainSidebar.classList.remove("open");
    });
});

mobileNavToggle?.addEventListener("click", () => {
    mainSidebar.classList.toggle("open");
});

function switchView(viewName) {
    navItems.forEach(n => {
        if (n.getAttribute("data-view") === viewName) n.classList.add("active");
        else n.classList.remove("active");
    });

    viewPanels.forEach(panel => {
        if (panel.id === `view-${viewName}`) panel.classList.remove("hidden");
        else panel.classList.add("hidden");
    });

    // View specific hooks
    if (viewName === "leaderboard") loadLeaderboard();
    if (viewName === "achievements") loadAchievements();
    if (viewName === "analytics") loadAnalytics();
    if (viewName === "daily-challenge") initDailyChallenge();
}


/* ============================================================
   GAMIFICATION & PROFILE METRICS
   ============================================================ */
async function loadPlayerProfile() {
    try {
        const res = await fetch(`${API_BASE}/game/profile/`, { headers: authHeaders() });
        if (!res.ok) return;
        const profile = await res.json();
        currentProfile = profile;

        // Update Topbar HUD
        if (hudLevelVal) hudLevelVal.textContent = profile.level;
        if (hudXpVal) hudXpVal.textContent = profile.total_xp;
        if (hudStreakVal) hudStreakVal.textContent = profile.current_streak;

        // Update Dashboard Stats Cards
        if (statXp) statXp.innerHTML = `${profile.total_xp} <span class="unit">XP</span>`;
        if (statLevel) statLevel.textContent = `Level ${profile.level}`;
        if (statStreak) statStreak.innerHTML = `${profile.current_streak} <span class="unit">Days</span>`;
        if (statAccuracy) statAccuracy.textContent = `${profile.accuracy_percentage}%`;
        if (statGames) statGames.textContent = profile.games_played;
    } catch (err) {
        console.error("Failed to load player profile:", err);
    }
}


/* ============================================================
   DOCUMENT MANAGEMENT & SELECTION
   ============================================================ */
uploadBtn?.addEventListener("click", () => fileInput.click());
kbUploadTriggerBtn?.addEventListener("click", () => fileInput.click());

fileInput?.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
        showToast("Please select a PDF document.", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", file.name.replace(".pdf", ""));

    uploadProgress.classList.remove("hidden");
    progressBar.style.width = "40%";
    uploadStatusText.textContent = "Extracting & Vectorizing into ChromaDB…";
    setStatus("Vectorizing...", "busy");

    try {
        const res = await fetch(`${API_BASE}/documents/`, {
            method: "POST",
            headers: { "Authorization": `Token ${getToken()}` },
            body: formData,
        });

        progressBar.style.width = "100%";
        if (!res.ok) {
            showToast("Failed to process document.", "error");
            return;
        }

        showToast("Document indexed into Knowledge Base! 📄⚡", "success");
        await loadDocuments();
    } catch {
        showToast("Network error uploading document.", "error");
    } finally {
        setTimeout(() => {
            uploadProgress.classList.add("hidden");
            progressBar.style.width = "0%";
            setStatus("Ready", "ready");
        }, 1200);
        fileInput.value = "";
    }
});

async function loadDocuments() {
    try {
        const res = await fetch(`${API_BASE}/documents/`, { headers: authHeaders() });
        if (!res.ok) return;
        const docs = await res.json();
        currentDocList = docs;

        if (statDocs) statDocs.textContent = docs.length;
        if (sidebarDocCount) sidebarDocCount.textContent = docs.length;

        // Populate Dashboard Document Selector
        if (dashDocSelect) {
            dashDocSelect.innerHTML = '<option value="">-- Choose an uploaded document --</option>';
            docs.forEach(doc => {
                const opt = document.createElement("option");
                opt.value = doc.id;
                opt.textContent = `${doc.title} (${doc.status})`;
                dashDocSelect.appendChild(opt);
            });
        }

        // Render Knowledge Base View
        renderKnowledgeBase(docs);
    } catch (err) {
        console.error("Failed to load documents:", err);
    }
}

function renderKnowledgeBase(docs) {
    if (!documentsList) return;
    documentsList.innerHTML = "";

    if (docs.length === 0) {
        documentsList.innerHTML = `
            <div class="empty-state">
                <p>No documents uploaded yet.</p>
                <span>Upload a course syllabus, notes, or textbook PDF to generate games!</span>
            </div>`;
        return;
    }

    docs.forEach(doc => {
        const card = document.createElement("div");
        card.className = "stat-card";
        card.innerHTML = `
            <div class="stat-icon-wrap purple">📄</div>
            <div style="flex:1;">
                <h4 style="font-size:0.95rem; font-weight:700; color:#fff;">${escapeHTML(doc.title)}</h4>
                <p style="font-size:0.75rem; color:var(--text-muted);">${doc.status.toUpperCase()} · ${new Date(doc.created_at).toLocaleDateString()}</p>
            </div>
            <button class="btn-action" style="padding:0.4rem 0.8rem; font-size:0.75rem;" onclick="launchQuizForDoc(${doc.id})">Battle</button>
        `;
        documentsList.appendChild(card);
    });
}

window.launchQuizForDoc = function(docId) {
    if (dashDocSelect) dashDocSelect.value = docId;
    switchView("dashboard");
    dashDocSelect.scrollIntoView({ behavior: "smooth" });
};


/* ============================================================
   AI QUIZ GENERATION & STARTING SESSIONS
   ============================================================ */
dashStartQuizBtn?.addEventListener("click", generateAndPlayQuiz);
quickPlayBtn?.addEventListener("click", () => {
    if (currentDocList.length === 0) {
        showToast("Please upload a PDF first to play!", "error");
        return;
    }
    if (dashDocSelect) dashDocSelect.value = currentDocList[0].id;
    generateAndPlayQuiz();
});

async function generateAndPlayQuiz() {
    const docId = dashDocSelect?.value;
    if (!docId) {
        showToast("Please select a document to generate questions from.", "error");
        return;
    }

    const gameMode = dashModeSelect?.value || "quiz_battle";
    const difficulty = dashDiffSelect?.value || "medium";

    dashStartQuizBtn.disabled = true;
    dashStartQuizBtn.querySelector(".btn-text").textContent = "AI Synthesizing Grounded Questions…";
    setStatus("Generating Quiz...", "busy");

    try {
        const res = await fetch(`${API_BASE}/game/generate/`, {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify({
                document_id: docId,
                topic: "Key Knowledge Concepts",
                count: 5,
                difficulty: difficulty,
                game_mode: gameMode,
            })
        });

        const quiz = await res.json();
        if (!res.ok) {
            showToast(quiz.error || "Failed to generate quiz.", "error");
            return;
        }

        showToast("Quest generated! Launching Arena ⚔️", "success");
        await startQuizSession(quiz.id);
        await loadRecentQuizzes();
    } catch {
        showToast("Network error during quiz generation.", "error");
    } finally {
        dashStartQuizBtn.disabled = false;
        dashStartQuizBtn.querySelector(".btn-text").textContent = "Generate & Play Game";
        setStatus("Ready", "ready");
    }
}

async function startQuizSession(quizId) {
    try {
        const res = await fetch(`${API_BASE}/game/session/start/${quizId}/`, {
            method: "POST",
            headers: authHeaders(),
        });
        const data = await res.json();
        if (!res.ok) return;

        currentQuiz = data.quiz;
        currentSession = data;
        activeQuestions = data.questions;
        currentQuestionIdx = 0;

        // Switch to Quiz Arena View
        switchView("quiz-arena");
        initArenaHUD();
        renderCurrentQuestion();
    } catch (err) {
        console.error("Failed to start session:", err);
    }
}

async function loadRecentQuizzes() {
    if (!recentQuizzesList) return;
    try {
        const res = await fetch(`${API_BASE}/game/quizzes/`, { headers: authHeaders() });
        if (!res.ok) return;
        const quizzes = await res.json();

        if (quizzes.length === 0) {
            recentQuizzesList.innerHTML = '<div class="empty-list-placeholder">No games generated yet. Select a document on the left to begin!</div>';
            return;
        }

        recentQuizzesList.innerHTML = "";
        quizzes.slice(0, 5).forEach(q => {
            const item = document.createElement("div");
            item.className = "recent-item";
            item.innerHTML = `
                <div>
                    <h4>${escapeHTML(q.title)}</h4>
                    <p>${q.game_mode.toUpperCase()} · ${q.difficulty.toUpperCase()} · ${q.total_questions} Questions</p>
                </div>
                <button class="recent-btn-play" onclick="startQuizSession(${q.id})">Play Again</button>
            `;
            recentQuizzesList.appendChild(item);
        });
    } catch (err) {
        console.error("Failed to load recent quizzes:", err);
    }
}
window.startQuizSession = startQuizSession;


/* ============================================================
   ACTIVE GAMEPLAY LOGIC (MCQ, TIMERS, TRUE/FALSE, FLASHCARDS)
   ============================================================ */
function initArenaHUD() {
    if (arenaQuizTitle) arenaQuizTitle.textContent = currentQuiz.title;
    if (arenaDocSource) arenaDocSource.textContent = `Source Document: ${currentQuiz.document_title || "Verified PDF"}`;
    if (arenaModeBadge) arenaModeBadge.textContent = currentQuiz.game_mode.replace("_", " ").toUpperCase();
    if (arenaScore) arenaScore.textContent = "0";
    if (arenaXpEarned) arenaXpEarned.textContent = "+0";

    arenaResultsScreen.classList.add("hidden");
    if (currentQuiz.game_mode === "time_challenge") {
        arenaTimerBox.classList.remove("hidden");
    } else {
        arenaTimerBox.classList.add("hidden");
    }

    if (currentQuiz.game_mode === "flashcard") {
        questionCard.classList.add("hidden");
        flashcardContainer.classList.remove("hidden");
    } else {
        questionCard.classList.remove("hidden");
        flashcardContainer.classList.add("hidden");
    }
}

function renderCurrentQuestion() {
    if (currentQuestionIdx >= activeQuestions.length) {
        completeSession();
        return;
    }

    const q = activeQuestions[currentQuestionIdx];
    const total = activeQuestions.length;
    const progressPct = ((currentQuestionIdx) / total) * 100;

    if (arenaProgressBar) arenaProgressBar.style.width = `${progressPct}%`;
    if (arenaProgressText) arenaProgressText.textContent = `Question ${currentQuestionIdx + 1} of ${total}`;
    if (qNumberPill) qNumberPill.textContent = `QUESTION ${currentQuestionIdx + 1} OF ${total}`;
    if (arenaQuestionText) arenaQuestionText.textContent = q.question_text;

    // Reset feedback and action buttons
    arenaFeedbackBox.classList.add("hidden");
    arenaNextBtn.classList.add("hidden");

    if (currentQuiz.game_mode === "flashcard") {
        renderFlashcard(q);
        return;
    }

    // Render Options
    arenaOptionsGrid.innerHTML = "";
    const options = [
        { key: "A", text: q.option_a },
        { key: "B", text: q.option_b },
        { key: "C", text: q.option_c },
        { key: "D", text: q.option_d },
    ].filter(o => o.text && o.text.trim().length > 0);

    options.forEach(opt => {
        const btn = document.createElement("button");
        btn.className = "option-btn";
        btn.innerHTML = `
            <span class="option-letter">${opt.key}</span>
            <span class="option-content">${escapeHTML(opt.text)}</span>
        `;
        btn.addEventListener("click", () => handleOptionSelection(opt.key, btn));
        arenaOptionsGrid.appendChild(btn);
    });

    // Start Question Timer if in Time Challenge
    questionStartTime = Date.now();
    if (currentQuiz.game_mode === "time_challenge") {
        startTimer(15);
    }
}

function startTimer(seconds) {
    if (activeTimer) clearInterval(activeTimer);
    timeRemaining = seconds;
    if (arenaTimerVal) arenaTimerVal.textContent = timeRemaining;

    activeTimer = setInterval(() => {
        timeRemaining--;
        if (arenaTimerVal) arenaTimerVal.textContent = timeRemaining;
        if (timeRemaining <= 0) {
            clearInterval(activeTimer);
            handleTimeExpiration();
        }
    }, 1000);
}

function handleTimeExpiration() {
    showToast("Time expired! ⏱️", "error");
    // Submit timeout empty option
    submitAnswer("TIMEOUT", null);
}

async function handleOptionSelection(selectedKey, clickedBtn) {
    if (activeTimer) clearInterval(activeTimer);

    // Disable all option buttons immediately to prevent duplicate submissions
    const allBtns = arenaOptionsGrid.querySelectorAll(".option-btn");
    allBtns.forEach(b => {
        b.disabled = true;
        if (b === clickedBtn) b.classList.add("selected");
    });

    const elapsedSeconds = ((Date.now() - questionStartTime) / 1000).toFixed(1);
    await submitAnswer(selectedKey, clickedBtn, elapsedSeconds);
}

async function submitAnswer(selectedKey, clickedBtn, timeTaken = 0) {
    const q = activeQuestions[currentQuestionIdx];

    try {
        const res = await fetch(`${API_BASE}/game/session/${currentSession.session_id}/submit/`, {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify({
                question_id: q.id,
                selected_option: selectedKey,
                time_taken: timeTaken,
            })
        });

        const result = await res.json();
        if (!res.ok) {
            showToast(result.error || "Submission failed.", "error");
            return;
        }

        // Highlight options
        const allBtns = arenaOptionsGrid.querySelectorAll(".option-btn");
        allBtns.forEach(b => {
            const letter = b.querySelector(".option-letter")?.textContent.trim();
            if (letter === result.correct_option) b.classList.add("correct");
            else if (letter === selectedKey && !result.is_correct) b.classList.add("wrong");
        });

        // Display Grounded AI Explanation & Page Citation
        arenaFeedbackBox.classList.remove("hidden");
        if (result.is_correct) {
            feedbackIcon.textContent = "✅";
            feedbackTitle.textContent = "Correct Fact Verified!";
            feedbackXp.textContent = `+${result.xp_awarded} XP`;
            feedbackXp.style.color = "var(--green)";
        } else {
            feedbackIcon.textContent = "❌";
            feedbackTitle.textContent = `Incorrect (Answer is ${result.correct_option})`;
            feedbackXp.textContent = "+0 XP";
            feedbackXp.style.color = "var(--red)";
        }

        feedbackExplanation.textContent = result.explanation || "Directly sourced from indexed document context.";
        citationText.textContent = `Source: ${result.document_title || "Document"} (Page ${result.source_page || 1}) — Verified Grounded Source`;

        if (arenaScore) arenaScore.textContent = result.current_score;
        if (arenaXpEarned) {
            const currXp = parseInt(arenaXpEarned.textContent.replace("+", "")) || 0;
            arenaXpEarned.textContent = `+${currXp + result.xp_awarded}`;
        }

        // Reveal Next Button
        arenaNextBtn.classList.remove("hidden");
    } catch (err) {
        console.error("Answer submission failed:", err);
    }
}

arenaNextBtn?.addEventListener("click", () => {
    currentQuestionIdx++;
    renderCurrentQuestion();
});


/* ─── FLASHCARD CONTROLS ─────────────────────────────────── */
function renderFlashcard(q) {
    if (flashcardElement) flashcardElement.classList.remove("flipped");
    if (fcFrontText) fcFrontText.textContent = q.question_text;
    if (fcBackAnswer) fcBackAnswer.textContent = q.option_a || "Target Concept";
    if (fcBackExplanation) fcBackExplanation.textContent = "Based on document context. Flip to review explanation and definitions.";
    if (fcCitation) fcCitation.textContent = `Verified Page ${q.source_page || 1}`;
}

flashcardElement?.addEventListener("click", () => {
    flashcardElement.classList.toggle("flipped");
});
fcFlipBtn?.addEventListener("click", () => {
    flashcardElement.classList.toggle("flipped");
});
fcPrevBtn?.addEventListener("click", () => {
    if (currentQuestionIdx > 0) {
        currentQuestionIdx--;
        renderCurrentQuestion();
    }
});
fcNextBtn?.addEventListener("click", () => {
    currentQuestionIdx++;
    renderCurrentQuestion();
});


/* ============================================================
   SESSION COMPLETION & VICTORY
   ============================================================ */
async function completeSession() {
    if (arenaProgressBar) arenaProgressBar.style.width = "100%";

    try {
        const res = await fetch(`${API_BASE}/game/session/${currentSession.session_id}/complete/`, {
            method: "POST",
            headers: authHeaders(),
        });
        const summary = await res.json();
        if (!res.ok) return;

        // Render Victory Modal
        arenaResultsScreen.classList.remove("hidden");
        if (resScore) resScore.textContent = summary.score;
        if (resAccuracy) resAccuracy.textContent = `${summary.accuracy_percentage}%`;
        if (resXp) resXp.textContent = `+${summary.xp_earned} XP`;
        if (victorySubtitle) {
            victorySubtitle.textContent = summary.perfect_bonus > 0
                ? "Flawless Performance! +50 Perfect Bonus Awarded 🌟"
                : `Answered ${summary.correct_count} of ${summary.total_questions} questions correctly.`;
        }

        // Refresh player HUD
        await loadPlayerProfile();
    } catch (err) {
        console.error("Failed to complete session:", err);
    }
}

resDashboardBtn?.addEventListener("click", () => {
    arenaResultsScreen.classList.add("hidden");
    switchView("dashboard");
});
resPlayAgainBtn?.addEventListener("click", () => {
    arenaResultsScreen.classList.add("hidden");
    if (currentQuiz) startQuizSession(currentQuiz.id);
});


/* ============================================================
   GAME MODES CARDS
   ============================================================ */
document.querySelectorAll(".mode-card")?.forEach(card => {
    card.addEventListener("click", () => {
        const mode = card.getAttribute("data-mode");
        if (dashModeSelect) dashModeSelect.value = mode;
        switchView("dashboard");
        showToast(`Mode switched to: ${mode.replace("_", " ").toUpperCase()}`, "info");
    });
});


/* ============================================================
   DAILY CHALLENGE
   ============================================================ */
document.getElementById("startDailyQuestBtn")?.addEventListener("click", async () => {
    if (currentDocList.length === 0) {
        showToast("Please upload a PDF document first for your Daily Challenge!", "error");
        return;
    }
    if (dashDocSelect) dashDocSelect.value = currentDocList[0].id;
    if (dashModeSelect) dashModeSelect.value = "daily_challenge";
    generateAndPlayQuiz();
});

function initDailyChallenge() {
    const dailyStreakVal = document.getElementById("dailyStreakVal");
    if (dailyStreakVal && currentProfile) {
        dailyStreakVal.textContent = `${currentProfile.current_streak} Days`;
    }
}


/* ============================================================
   LEADERBOARD & ACHIEVEMENTS
   ============================================================ */
async function loadLeaderboard() {
    const tbody = document.getElementById("leaderboardBody");
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/game/leaderboard/`, { headers: authHeaders() });
        if (!res.ok) return;
        const list = await res.json();

        tbody.innerHTML = "";
        list.forEach(item => {
            const tr = document.createElement("tr");
            let badgeClass = item.rank === 1 ? "gold" : item.rank === 2 ? "silver" : item.rank === 3 ? "bronze" : "";
            tr.innerHTML = `
                <td><span class="rank-badge ${badgeClass}">${item.rank}</span></td>
                <td><strong>${escapeHTML(item.username)}</strong></td>
                <td><span class="hud-label">LVL</span> ${item.level}</td>
                <td><strong style="color:var(--cyan-2);">${item.total_xp}</strong> XP</td>
                <td>${item.games_played}</td>
                <td>${item.accuracy_percentage}%</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to load leaderboard:", err);
    }
}

async function loadAchievements() {
    const grid = document.getElementById("achievementsList");
    if (!grid) return;

    try {
        const res = await fetch(`${API_BASE}/game/achievements/`, { headers: authHeaders() });
        if (!res.ok) return;
        const achievements = await res.json();

        grid.innerHTML = "";
        achievements.forEach(ach => {
            const card = document.createElement("div");
            card.className = `achievement-card ${ach.unlocked ? "unlocked" : ""}`;
            card.innerHTML = `
                <div class="ach-icon-box">${ach.icon || "🏆"}</div>
                <div class="ach-info">
                    <h4>${escapeHTML(ach.title)}</h4>
                    <p>${escapeHTML(ach.description)}</p>
                    <span class="ach-tag">${ach.unlocked ? "UNLOCKED ✓" : `+${ach.xp_bonus} XP Reward`}</span>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        console.error("Failed to load achievements:", err);
    }
}


/* ============================================================
   LEARNING ANALYTICS
   ============================================================ */
async function loadAnalytics() {
    const barsContainer = document.getElementById("analyticsDifficultyBars");
    const weeklyContainer = document.getElementById("analyticsWeeklyGrid");
    if (!barsContainer) return;

    try {
        const res = await fetch(`${API_BASE}/game/analytics/`, { headers: authHeaders() });
        if (!res.ok) return;
        const data = await res.json();

        // Render difficulty mastery bars
        barsContainer.innerHTML = "";
        Object.entries(data.difficulty_stats || {}).forEach(([diff, stat]) => {
            const bar = document.createElement("div");
            bar.style.marginBottom = "1rem";
            bar.innerHTML = `
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:600; margin-bottom:0.3rem;">
                    <span>${diff.toUpperCase()} (${stat.total} Questions)</span>
                    <span style="color:var(--cyan-2);">${stat.accuracy}%</span>
                </div>
                <div style="height:8px; background:rgba(255,255,255,0.06); border-radius:4px; overflow:hidden;">
                    <div style="width:${stat.accuracy}%; height:100%; background:var(--grad-primary); border-radius:4px;"></div>
                </div>
            `;
            barsContainer.appendChild(bar);
        });

        // Render 7-day activity stream
        if (weeklyContainer) {
            weeklyContainer.innerHTML = "";
            (data.weekly_activity || []).forEach(act => {
                const cell = document.createElement("div");
                cell.className = "stat-card";
                cell.style.padding = "0.75rem";
                cell.innerHTML = `
                    <div style="font-size:0.75rem; color:var(--text-muted); font-weight:700;">${act.date}</div>
                    <div style="font-family:var(--font-game); font-weight:800; color:var(--cyan-2); font-size:1.1rem;">+${act.xp} XP</div>
                `;
                weeklyContainer.appendChild(cell);
            });
        }
    } catch (err) {
        console.error("Failed to load analytics:", err);
    }
}


/* ============================================================
   PRESERVED RAG CHATBOT (AI KNOWLEDGE CHAT)
   ============================================================ */
questionInput?.addEventListener("input", () => {
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 120) + "px";
});
questionInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
sendBtn?.addEventListener("click", sendMessage);

async function sendMessage() {
    const text = questionInput.value.trim();
    if (!text) return;

    questionInput.value = "";
    questionInput.style.height = "auto";
    appendUserMessage(text);

    const typingId = appendTypingIndicator();
    sendBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/chat/`, {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify({ question: text })
        });
        const data = await res.json();
        removeTypingIndicator(typingId);

        if (!res.ok) {
            if (res.status === 401) {
                appendBotMessage("🔒 Your session has expired. Please log out and sign back in to refresh your access.");
                showToast("Session expired. Please log out and sign in again.", "warning");
                return;
            }
            appendBotMessage(data.detail || data.error || "Could not retrieve answer from documents.");
            return;
        }

        appendBotMessage(data.answer, data.sources);
    } catch {
        removeTypingIndicator(typingId);
        appendBotMessage("Connection error while querying RAG intelligence.");
    } finally {
        sendBtn.disabled = false;
    }
}

function appendUserMessage(text) {
    const welcome = document.getElementById("welcomeCard");
    if (welcome) welcome.remove();

    const wrap = document.createElement("div");
    wrap.className = "message user-message";
    wrap.innerHTML = `
        <div class="msg-avatar">${(currentUser?.username || "U")[0].toUpperCase()}</div>
        <div class="msg-body">${escapeHTML(text)}</div>
    `;
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendBotMessage(text, sources = []) {
    const wrap = document.createElement("div");
    wrap.className = "message bot-message";

    let sourcesHTML = "";
    if (sources && sources.length > 0) {
        const citations = sources.map(s => `Doc #${s.document_id} (Page ${s.page || 1})`).join(" · ");
        sourcesHTML = `<div class="sources-container">📖 Citations: ${escapeHTML(citations)}</div>`;
    }

    wrap.innerHTML = `
        <div class="msg-avatar">NQ</div>
        <div class="msg-body">
            <div>${escapeHTML(text)}</div>
            ${sourcesHTML}
        </div>
    `;
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendTypingIndicator() {
    const id = "typing-" + Date.now();
    const wrap = document.createElement("div");
    wrap.className = "message bot-message";
    wrap.id = id;
    wrap.innerHTML = `
        <div class="msg-avatar">NQ</div>
        <div class="msg-body" style="color:var(--text-muted); font-style:italic;">Synthesizing retrieved chunks…</div>
    `;
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

clearChatBtn?.addEventListener("click", () => {
    chatMessages.innerHTML = `
        <div class="welcome-card" id="welcomeCard">
            <div class="welcome-orb"></div>
            <div class="welcome-icon">💬</div>
            <h3>NeuralQuest Knowledge Chat</h3>
            <p>Chat cleared. Ask anything grounded on your uploaded materials.</p>
        </div>`;
    showToast("Chat cleared.", "info");
});

async function loadChatHistory() {
    try {
        const res = await fetch(`${API_BASE}/chat/history/`, { headers: authHeaders() });
        if (!res.ok) return;
        const history = await res.json();
        if (history && history.length > 0) {
            chatMessages.innerHTML = "";
            [...history].reverse().forEach(m => {
                appendUserMessage(m.question);
                appendBotMessage(m.answer);
            });
        }
    } catch {
        /* ignore */
    }
}


/* ============================================================
   BACKGROUND PARTICLES & UTILITIES
   ============================================================ */
function initParticles() {
    const container = document.getElementById("particles");
    if (!container) return;
    const colors = ["#8b5cf6", "#a855f7", "#06b6d4", "#38bdf8", "#3b82f6"];
    for (let i = 0; i < 30; i++) {
        const p = document.createElement("div");
        p.className = "particle";
        const size = Math.random() * 3 + 1;
        p.style.cssText = `
            width:${size}px; height:${size}px;
            left:${Math.random() * 100}%;
            background:${colors[Math.floor(Math.random() * colors.length)]};
            animation-duration:${Math.random() * 15 + 10}s;
            animation-delay:${Math.random() * 8}s;
        `;
        container.appendChild(p);
    }
}

function escapeHTML(str) {
    if (typeof str !== "string") return "";
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}