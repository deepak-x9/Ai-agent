const API_BASE_URL = "http://localhost:8000";
const SESSION_KEY = "qa_assistant_session_id";
const CHAT_KEY = "qa_assistant_chat_history";

const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const loadingEl = document.getElementById("loading");
const newChatBtn = document.getElementById("newChatBtn");

let sessionId = localStorage.getItem(SESSION_KEY) || null;
let chatHistory = JSON.parse(localStorage.getItem(CHAT_KEY) || "[]");

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function saveLocalState() {
  localStorage.setItem(CHAT_KEY, JSON.stringify(chatHistory));
  if (sessionId) {
    localStorage.setItem(SESSION_KEY, sessionId);
  }
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addCopyButtons(container) {
  container.querySelectorAll("pre").forEach((pre) => {
    if (pre.querySelector(".copy-code")) return;

    const button = document.createElement("button");
    button.className = "copy-code";
    button.textContent = "Copy code";

    button.addEventListener("click", async () => {
      const codeText = pre.querySelector("code")?.innerText || "";
      try {
        await navigator.clipboard.writeText(codeText);
        button.textContent = "Copied!";
        setTimeout(() => (button.textContent = "Copy code"), 1500);
      } catch {
        button.textContent = "Failed";
      }
    });

    pre.appendChild(button);
  });
}

function renderMessage(role, content, languageHint = "") {
  const messageEl = document.createElement("article");
  messageEl.className = `message ${role}`;

  const label = role === "user" ? "You" : "AI Assistant";
  const langText = languageHint ? ` • detected: ${languageHint}` : "";

  if (role === "assistant") {
    const html = marked.parse(content);
    messageEl.innerHTML = `<span class="meta">${label}${langText}</span>${html}`;
    messageEl.querySelectorAll("pre code").forEach((block) => hljs.highlightElement(block));
    addCopyButtons(messageEl);
  } else {
    messageEl.innerHTML = `<span class="meta">${label}</span><p>${escapeHtml(content)}</p>`;
  }

  messagesEl.appendChild(messageEl);
  scrollToBottom();
}

function renderHistory() {
  messagesEl.innerHTML = "";
  chatHistory.forEach((entry) => {
    renderMessage(entry.role, entry.content, entry.detected_language);
  });
}

function setLoading(isLoading) {
  loadingEl.classList.toggle("hidden", !isLoading);
}

async function sendMessage(message) {
  const payload = { message, session_id: sessionId };

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    const details = err.detail || "Unknown server error.";
    throw new Error(details);
  }

  return response.json();
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();

  if (!message) return;

  renderMessage("user", message);
  chatHistory.push({ role: "user", content: message });
  saveLocalState();
  messageInput.value = "";

  setLoading(true);

  try {
    const data = await sendMessage(message);
    sessionId = data.session_id;

    renderMessage("assistant", data.answer, data.detected_language);
    chatHistory.push({
      role: "assistant",
      content: data.answer,
      detected_language: data.detected_language,
    });
    saveLocalState();
  } catch (error) {
    const errorText = error instanceof Error ? error.message : "Unexpected error.";
    renderMessage("assistant", `<p class="error">Error: ${escapeHtml(errorText)}</p>`);
  } finally {
    setLoading(false);
  }
});

newChatBtn.addEventListener("click", async () => {
  if (sessionId) {
    try {
      await fetch(`${API_BASE_URL}/chat/${sessionId}`, { method: "DELETE" });
    } catch {
      // Best effort only.
    }
  }

  sessionId = null;
  chatHistory = [];
  localStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(CHAT_KEY);
  renderHistory();
});

renderHistory();
