(() => {
  "use strict";

  const SESSION_STORAGE_KEY = "enterprise-decision-agent-session-v1";
  const HEALTH_ENDPOINT = "/health";
  const READY_ENDPOINT = "/ready";
  const EXECUTE_ENDPOINT = "/api/v1/agent/execute";
  const SESSION_ENDPOINT = "/api/v1/demo/session";
  const STATUS_POLL_MS = 12000;

  const elements = {
    form: document.getElementById("query-form"),
    query: document.getElementById("query"),
    send: document.getElementById("send-request"),
    cancel: document.getElementById("cancel-request"),
    clearSession: document.getElementById("clear-session"),
    sessionId: document.getElementById("session-id"),
    message: document.getElementById("request-message"),
    healthBadge: document.getElementById("health-badge"),
    healthText: document.getElementById("health-text"),
    readyBadge: document.getElementById("ready-badge"),
    readyText: document.getElementById("ready-text"),
    answer: document.getElementById("answer"),
    citations: document.getElementById("citations"),
    metadata: document.getElementById("metadata"),
    resultStatus: document.getElementById("result-status"),
    traceCard: document.getElementById("trace-card"),
    traceSummary: document.getElementById("trace-summary"),
    traceStages: document.getElementById("trace-stages"),
    chatHistory: document.getElementById("chat-history"),
  };

  const TRACE_ATTRIBUTE_LABELS = Object.freeze({
    route: "Route",
    skill_name: "Skill",
    tool_name: "Tool",
    retrieved_count: "Retrieved",
    reranked_count: "Reranked",
    selected_evidence_count: "Evidence",
    row_count: "Rows",
    denied: "Denied",
    timeout: "Timeout",
    answerable: "Answerable",
    review_outcome: "Review",
  });
  const TRACE_STAGE_ALLOWLIST = new Set([
    "routing",
    "planning",
    "tool_execution",
    "data_access",
    "retrieval",
    "reranking",
    "evidence_selection",
    "review",
    "answer_generation",
  ]);

  let activeController = null;
  let pollTimer = null;
  let sessionId = loadOrCreateSession();

  function randomIdentifier(prefix) {
    let value;
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
      value = globalThis.crypto.randomUUID();
    } else if (globalThis.crypto && typeof globalThis.crypto.getRandomValues === "function") {
      const bytes = new Uint8Array(16);
      globalThis.crypto.getRandomValues(bytes);
      value = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
    } else {
      value = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
    }
    return `${prefix}-${value}`;
  }

  function loadOrCreateSession() {
    try {
      const stored = globalThis.localStorage.getItem(SESSION_STORAGE_KEY);
      if (stored && stored.length <= 128) {
        return stored;
      }
    } catch {
      // Storage can be unavailable in hardened/private browser modes.
    }
    return createAndStoreSession();
  }

  function createAndStoreSession() {
    const nextSession = randomIdentifier("session");
    try {
      globalThis.localStorage.setItem(SESSION_STORAGE_KEY, nextSession);
    } catch {
      // The in-memory value still provides a valid session for this page.
    }
    return nextSession;
  }

  function showSession() {
    elements.sessionId.textContent = `Session ${sessionId.slice(-8)}`;
    elements.sessionId.title = sessionId;
  }

  function setBadge(badge, textElement, state, label) {
    badge.classList.remove(
      "status-checking",
      "status-ready",
      "status-unavailable",
      "status-liveness",
    );
    badge.classList.add(`status-${state}`);
    textElement.textContent = label;
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    return { response, payload };
  }

  async function refreshServiceStatus() {
    const results = await Promise.allSettled([
      fetchJson(HEALTH_ENDPOINT, { cache: "no-store" }),
      fetchJson(READY_ENDPOINT, { cache: "no-store" }),
    ]);

    const health = results[0];
    if (
      health.status === "fulfilled" &&
      health.value.response.ok &&
      health.value.payload &&
      health.value.payload.status === "ok"
    ) {
      setBadge(elements.healthBadge, elements.healthText, "ready", "Service Online");
    } else {
      setBadge(elements.healthBadge, elements.healthText, "unavailable", "Service Unreachable");
    }

    const readiness = results[1];
    if (
      readiness.status === "fulfilled" &&
      readiness.value.response.ok &&
      readiness.value.payload &&
      readiness.value.payload.status === "ready"
    ) {
      setBadge(elements.readyBadge, elements.readyText, "ready", "Runtime Ready");
    } else if (
      readiness.status === "fulfilled" &&
      readiness.value.payload &&
      readiness.value.payload.status === "not_ready"
    ) {
      setBadge(elements.readyBadge, elements.readyText, "liveness", "Runtime Not Ready");
    } else {
      setBadge(elements.readyBadge, elements.readyText, "unavailable", "Readiness Unknown");
    }
  }

  function startStatusPolling() {
    stopStatusPolling();
    void refreshServiceStatus();
    pollTimer = globalThis.setInterval(() => {
      void refreshServiceStatus();
    }, STATUS_POLL_MS);
  }

  function stopStatusPolling() {
    if (pollTimer !== null) {
      globalThis.clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function setRequestState(isLoading) {
    elements.send.disabled = isLoading;
    elements.cancel.disabled = !isLoading;
    elements.query.disabled = isLoading;
    for (const button of document.querySelectorAll(".example-button")) {
      button.disabled = isLoading;
    }
  }

  function showMessage(message, isError = false) {
    elements.message.textContent = message;
    elements.message.classList.toggle("message-error", isError);
  }

  function currentTimeLabel() {
    return new Intl.DateTimeFormat("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date());
  }

  function appendChatMessage(role, content, tags = []) {
    const article = document.createElement("article");
    const avatar = document.createElement("div");
    const body = document.createElement("div");
    const meta = document.createElement("div");
    const author = document.createElement("strong");
    const time = document.createElement("span");
    const paragraph = document.createElement("p");
    article.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}`;
    avatar.className = "message-avatar";
    avatar.textContent = role === "user" ? "YOU" : "AI";
    avatar.setAttribute("aria-hidden", "true");
    body.className = "message-body";
    meta.className = "message-meta";
    author.textContent = role === "user" ? "User" : "Enterprise Decision Assistant";
    time.textContent = currentTimeLabel();
    paragraph.textContent = content;
    meta.append(author, time);
    body.append(meta, paragraph);
    if (Array.isArray(tags) && tags.length > 0) {
      const tagList = document.createElement("div");
      tagList.className = "message-tags";
      for (const tag of tags.filter(Boolean)) {
        const item = document.createElement("span");
        item.textContent = String(tag);
        tagList.append(item);
      }
      body.append(tagList);
    }
    article.append(avatar, body);
    elements.chatHistory.append(article);
    elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
  }

  function resetConversationView() {
    elements.chatHistory.replaceChildren();
    appendChatMessage(
      "assistant",
      "Created a new session. You can ask about Enterprise Knowledge, Data Analysis, or Decision Recommendations.",
      [],
    );
    elements.answer.textContent = "Awaiting answer";
    replaceCitations([]);
    replaceMetadata({ status: "Awaiting Request" });
    renderTrace(null);
    elements.resultStatus.textContent = "Awaiting Request";
    elements.resultStatus.classList.remove("result-status-success", "result-status-failed");
  }

  function replaceCitations(citations) {
    elements.citations.replaceChildren();
    if (!Array.isArray(citations) || citations.length === 0) {
      const emptyItem = document.createElement("li");
      emptyItem.textContent = "No citations";
      elements.citations.append(emptyItem);
      return;
    }
    for (const citation of citations) {
      const item = document.createElement("li");
      item.textContent = String(citation);
      elements.citations.append(item);
    }
  }

  function addMetadataRow(label, value) {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value || "—";
    row.append(term, description);
    elements.metadata.append(row);
  }

  function replaceMetadata(data) {
    elements.metadata.replaceChildren();
    addMetadataRow("Status", data.status);
    addMetadataRow("Analysis Type", routePresentation(data.route));
    addMetadataRow("Skill Used", skillPresentation(data.skill));
    addMetadataRow("Session Context", contextPresentation(data.memory_context_status));
    if (data.error_code) {
      addMetadataRow("Error Code", data.error_code);
    }
  }

  function routePresentation(route) {
    const labels = { knowledge: "Enterprise Knowledge", data: "Data Analysis", mixed: "Decision Recommendation" };
    return labels[route] || route || "—";
  }

  function contextPresentation(status) {
    const available = new Set(["loaded", "completed", "available", "used"]);
    return available.has(status) ? "Incorporated session context" : "No history used this turn";
  }

  function skillPresentation(skill) {
    if (skill && skill.includes("inventory") && skill.includes("diagnosis")) {
      return "Inventory Risk Diagnosis";
    }
    const labels = {
      "inventory-analysis": "Inventory Data Analysis",
      "knowledge-qa": "Enterprise Knowledge Q&A",
    };
    return labels[skill] || (skill ? "Enterprise Analysis" : "—");
  }

  function traceStatusPresentation(status) {
    const states = {
      completed: { label: "Completed", tone: "completed" },
      failed: { label: "Failed", tone: "failed" },
      unsupported: { label: "Unsupported", tone: "neutral" },
      cancelled: { label: "Cancelled", tone: "neutral" },
      not_requested: { label: "Not Requested", tone: "neutral" },
      skipped: { label: "Skipped", tone: "neutral" },
    };
    return states[status] || { label: "Unknown Status", tone: "neutral" };
  }

  function formatDuration(value) {
    return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(0)} ms` : "Unknown";
  }

  function renderTraceAttributes(attributes) {
    if (!Array.isArray(attributes)) {
      return "";
    }
    return attributes
      .filter(
        (attribute) =>
          attribute &&
          typeof attribute.key === "string" &&
          Object.hasOwn(TRACE_ATTRIBUTE_LABELS, attribute.key),
      )
      .map((attribute) => `${TRACE_ATTRIBUTE_LABELS[attribute.key]}: ${String(attribute.value)}`)
      .join(" · ");
  }

  function renderTrace(trace) {
    elements.traceStages.replaceChildren();
    elements.traceSummary.textContent = "";
    elements.traceCard.hidden = true;
    if (!trace || typeof trace !== "object" || !Array.isArray(trace.stages)) {
      return;
    }
    const summaryParts = [
      `Status: ${traceStatusPresentation(trace.final_status).label}`,
      `Duration: ${formatDuration(trace.duration_ms)}`,
    ];
    if (typeof trace.truncated_stage_count === "number" && trace.truncated_stage_count > 0) {
      summaryParts.push(`Omitted ${trace.truncated_stage_count} stages`);
    }
    if (typeof trace.dropped_span_count === "number" && trace.dropped_span_count > 0) {
      summaryParts.push(`Dropped ${trace.dropped_span_count} spans`);
    }
    elements.traceSummary.textContent = summaryParts.join(" · ");
    for (const stage of trace.stages) {
      if (
        !stage ||
        typeof stage !== "object" ||
        !TRACE_STAGE_ALLOWLIST.has(stage.stage)
      ) {
        continue;
      }
      const item = document.createElement("li");
      const heading = document.createElement("div");
      const name = document.createElement("strong");
      const status = document.createElement("span");
      const duration = document.createElement("span");
      const detail = document.createElement("p");
      const presentation = traceStatusPresentation(stage.status);
      name.textContent = typeof stage.stage === "string" ? stage.stage : "Stage";
      status.textContent = presentation.label;
      status.className = `trace-stage-status trace-stage-status-${presentation.tone}`;
      duration.textContent = formatDuration(stage.duration_ms);
      heading.append(name, status, duration);
      detail.textContent = renderTraceAttributes(stage.attributes);
      item.append(heading);
      if (detail.textContent) {
        item.append(detail);
      }
      elements.traceStages.append(item);
    }
    elements.traceCard.hidden = false;
  }

  function responsePresentation(status) {
    if (status === "completed") {
      return { label: "Completed", tone: "success", message: "Request completed successfully." };
    }
    if (status === "unsupported") {
      return {
        label: "Unsupported",
        tone: "neutral",
        message: "The Agent does not currently support this type of request.",
      };
    }
    return { label: "Execution Failed", tone: "failed", message: "Request execution failed." };
  }

  function renderFormalResponse(data) {
    const presentation = responsePresentation(data.status);
    elements.resultStatus.textContent = presentation.label;
    elements.resultStatus.classList.toggle(
      "result-status-success",
      presentation.tone === "success",
    );
    elements.resultStatus.classList.toggle(
      "result-status-failed",
      presentation.tone === "failed",
    );
    const answer =
      data.answer ||
      (data.status === "unsupported"
        ? "The Agent currently does not support this type of request."
        : "No answer available for this request.");
    elements.answer.textContent = answer;
    appendChatMessage("assistant", answer, [routePresentation(data.route)]);
    replaceCitations(data.citations);
    replaceMetadata(data);
    renderTrace(data.trace);
    return presentation;
  }

  function publicErrorMessage(statusCode, payload) {
    if (statusCode === 429) {
      return "The demo is busy or your request limit has been reached. Please wait and try again.";
    }
    if (statusCode === 401) {
      return "Your demo visit could not be verified. Please send again to start a new visit.";
    }
    if (statusCode === 422) {
      return "Request validation failed. Please check your query and try again.";
    }
    if (statusCode === 503) {
      return "The agent service is not ready yet. Please try again later.";
    }
    if (statusCode >= 500) {
      return "The service is temporarily unable to fulfill the request. Please try again later.";
    }
    if (payload && payload.code === "runtime_unavailable") {
      return "The agent service is not ready yet. Please try again later.";
    }
    return `Request failed (HTTP ${statusCode}).`;
  }

  async function submitQuery(event) {
    event.preventDefault();
    if (activeController !== null) {
      return;
    }
    const query = elements.query.value.trim();
    if (!query) {
      showMessage("Please enter a query before sending.", true);
      elements.query.focus();
      return;
    }

    const requestId = randomIdentifier("request");
    const payload = { request_id: requestId, session_id: sessionId, query };
    appendChatMessage("user", query);
    elements.query.value = "";
    activeController = new AbortController();
    setRequestState(true);
    showMessage("Agent Workflow executing: Routing, Tool Calling, Evidence Synthesis & Review...");
    elements.resultStatus.textContent = "Processing";
    elements.resultStatus.classList.remove("result-status-success", "result-status-failed");

    try {
      const session = await fetchJson(SESSION_ENDPOINT, {
        cache: "no-store",
        credentials: "same-origin",
        signal: activeController.signal,
      });
      // Private/local apps intentionally do not expose the public-demo bootstrap.
      if (session.response.status !== 404 && !session.response.ok) {
        showMessage(publicErrorMessage(session.response.status, session.payload), true);
        elements.resultStatus.textContent = "Request Failed";
        return;
      }
      const result = await fetchJson(EXECUTE_ENDPOINT, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: activeController.signal,
      });
      if (!result.response.ok) {
        showMessage(publicErrorMessage(result.response.status, result.payload), true);
        elements.resultStatus.textContent = "Request Failed";
        elements.resultStatus.classList.add("result-status-failed");
        return;
      }
      if (!result.payload || typeof result.payload !== "object") {
        showMessage("Service returned an unrecognized response.", true);
        elements.resultStatus.textContent = "Invalid Response";
        elements.resultStatus.classList.add("result-status-failed");
        return;
      }
      const presentation = renderFormalResponse(result.payload);
      showMessage(presentation.message, presentation.tone === "failed");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        showMessage("Request cancelled.");
        elements.resultStatus.textContent = "Cancelled";
      } else {
        showMessage("Unable to connect to service. Please verify process status and try again.", true);
        elements.resultStatus.textContent = "Connection Failed";
        elements.resultStatus.classList.add("result-status-failed");
      }
    } finally {
      activeController = null;
      setRequestState(false);
      void refreshServiceStatus();
    }
  }

  elements.form.addEventListener("submit", (event) => {
    void submitQuery(event);
  });

  elements.query.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      elements.form.requestSubmit();
    }
  });

  elements.cancel.addEventListener("click", () => {
    if (activeController !== null) {
      activeController.abort();
    }
  });

  elements.clearSession.addEventListener("click", () => {
    sessionId = createAndStoreSession();
    showSession();
    resetConversationView();
    showMessage("New session created.");
  });

  for (const button of document.querySelectorAll(".example-button")) {
    button.addEventListener("click", () => {
      elements.query.value = button.dataset.query || "";
      elements.query.focus();
    });
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopStatusPolling();
    } else {
      startStatusPolling();
    }
  });

  showSession();
  startStatusPolling();
})();
