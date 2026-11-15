"use strict";

// Buildless, same-origin client. Record contents are always inserted as text.
(() => {
  const CONAN = (window.CONAN = window.CONAN || {});
  const $ = (id) => document.getElementById(id);
  const state = {
    config: null, runs: [], selected: null, payload: null, activeName: null,
    tab: "summary", detailTab: "evidence", search: "", findingLimit: 40, selectedFinding: null,
    findingView: "overview", evidenceTopic: "all", evidenceModel: null, needsLimit: 40, loading: false, submitting: false, stopping: false,
    request: 0, timer: null, connected: false, sidebarRenderKey: null,
  };
  const statuses = new Set(["running", "completed", "partial", "failed", "cancelled", "saved"]);
  const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
  const shortDate = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
  const longDate = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
  const timeDate = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit", second: "2-digit" });

  function element(tag, className, text) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined && text !== null) item.textContent = String(text);
    return item;
  }
  const object = (value) => value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const array = (value) => Array.isArray(value) ? value : [];
  const present = (value, fallback = "Not recorded") => value === undefined || value === null || value === "" ? fallback : typeof value === "object" ? JSON.stringify(value) : String(value);
  const count = (value, fallback = "Unmeasured") => Number.isSafeInteger(value) && value >= 0 ? number.format(value) : fallback;
  const measure = (section, key) => object(section).status === "measured" ? count(section[key]) : object(section).status === "invalid" ? "Invalid" : "Unmeasured";
  const isRunning = () => state.payload && state.payload.status === "running";
  const savedRun = () => object(state.payload && state.payload.run);
  const isAccepted = (finding) => object(finding).status === "verified";
  const acceptedFindings = (run = savedRun()) => array(run.findings).filter(isAccepted);
  const summary = () => state.runs.find((entry) => entry.name === state.selected) || {};
  function date(value, formatter = longDate) {
    if (!value) return "Time not recorded";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? String(value) : formatter.format(parsed);
  }
  function badge(text, kind = "") {
    const allowed = new Set(["accepted", "completed", "success", "running", "needs", "partial", "cancelled", "rejected", "refused", "heuristic", "failed", "error", "invalid", "synthetic", "judgment"]);
    return element("span", "badge" + (allowed.has(kind) ? " " + kind : ""), text);
  }
  function statusLabel(status) {
    return ({ running: "Running", completed: "Completed", partial: "Partial report", failed: "Failed", cancelled: "Cancelled", saved: "Saved report" })[status] || "Status unknown";
  }
  function empty(title, description, symbol = "◇") {
    const box = element("div", "empty-state");
    const icon = element("div", "empty-icon", symbol);
    icon.setAttribute("aria-hidden", "true");
    box.append(icon, element("h3", "", title), element("p", "", description));
    return box;
  }
  function code(value) {
    return element("pre", "", typeof value === "string" ? value : JSON.stringify(value, null, 2));
  }
  function notice(message, error = false) {
    $("notice").hidden = !message;
    $("notice").textContent = message || "";
    $("notice").classList.toggle("error", error);
  }
  function connection(online) {
    state.connected = online;
    $("connection-dot").className = "connection-dot " + (online ? "online" : "offline");
    $("connection-label").textContent = online ? "Connected to local server" : "Local server unavailable";
  }
  async function api(path, body) {
    const options = { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } };
    if (body !== undefined) {
      if (!state.config || !state.config.token) throw new Error("The server configuration is unavailable. Refresh the workspace before starting a run.");
      options.method = "POST";
      options.headers["Content-Type"] = "application/json";
      options.headers["X-COP-Token"] = state.config.token;
      options.body = JSON.stringify(body);
    }
    let response;
    try { response = await fetch(path, options); }
    catch (_) { connection(false); throw new Error("Cannot reach the local server. Check that cop serve is running, then refresh."); }
    let value;
    try { value = await response.json(); }
    catch (_) { throw new Error("The local server returned an unreadable response."); }
    connection(true);
    if (!response.ok) throw new Error(typeof value.error === "string" ? value.error : "The request could not be completed.");
    return value;
  }

  function renderRuns() {
    const renderKey = JSON.stringify([state.selected, state.runs.map((entry) =>
      [entry.name, entry.title, entry.status, entry.generated_at, Boolean(entry.sample)])]);
    if (renderKey === state.sidebarRenderKey) return;
    state.sidebarRenderKey = renderKey;
    const container = $("run-list");
    container.replaceChildren();
    if (!state.runs.length) {
      container.append(element("p", "sidebar-empty", "No saved investigations yet. Your reports will appear here."));
      return;
    }
    state.runs.forEach((entry) => {
      const button = element("button", "run-item" + (entry.name === state.selected ? " active" : ""));
      button.type = "button";
      button.setAttribute("aria-current", entry.name === state.selected ? "page" : "false");
      button.append(element("span", "run-item-title", present(entry.title, entry.name)));
      const meta = element("span", "run-item-meta");
      const status = statuses.has(entry.status) ? entry.status : "saved";
      const dot = element("span", "run-status-dot " + status);
      dot.setAttribute("aria-hidden", "true");
      const label = entry.sample ? "Synthetic sample" : statusLabel(entry.status);
      meta.append(dot, element("span", "", label));
      if (entry.generated_at) meta.append(element("span", "", "· " + date(entry.generated_at, shortDate)));
      button.append(meta);
      button.addEventListener("click", () => selectRun(entry.name));
      container.append(button);
    });
  }
  async function refreshRuns() {
    const result = await api("/api/runs");
    state.runs = array(result.runs).filter((entry) => typeof entry.name === "string");
    const active = state.runs.find((entry) => entry.status === "running");
    state.activeName = active ? active.name : null;
    renderRuns();
    updateStartButton();
  }
  async function selectRun(name) {
    state.selected = name;
    state.payload = null;
    state.search = "";
    state.findingLimit = 40;
    state.evidenceTopic = "all";
    state.needsLimit = 40;
    $("finding-search").value = "";
    clearInspector();
    if (CONAN.graph) CONAN.graph.clear();
    renderRuns();
    notice("");
    $("welcome").hidden = true;
    $("workspace").hidden = false;
    $("report-actions").hidden = true;
    $("report-title").textContent = present(summary().title, name);
    $("report-meta").replaceChildren(element("span", "empty-loading", "Loading saved records…"));
    $("finding-list").replaceChildren(empty("Loading investigation", "Reading the saved report and available audit entries."));
    // Clear the previous case immediately; a failed load must not leave another case's details visible.
    for (const id of ["needs-list", "activity-list", "history-list", "coverage-content", "conclusions", "unverified-findings", "finding-pagination"]) $(id).replaceChildren();
    for (const id of ["metric-accepted", "metric-refused", "metric-judgments", "metric-extracted", "metric-inspected"]) $(id).textContent = "—";
    $("evidence-hash").textContent = "";
    for (const id of ["count-findings", "count-needs", "count-activity"]) $(id).textContent = "";
    $("run-progress").hidden = true;
    $("sample-banner").hidden = !summary().sample;
    await loadRun(name);
  }
  async function loadRun(name, silent = false) {
    const request = ++state.request;
    try {
      const value = await api("/api/run?" + new URLSearchParams({ name }));
      if (state.selected !== name || request !== state.request) return;
      state.payload = value;
      renderRun();
    } catch (error) {
      if (state.selected !== name || request !== state.request) return;
      if (!silent || !state.payload) {
        notice(error.message, true);
        $("report-meta").replaceChildren(element("span", "", "Report unavailable"));
        $("finding-list").replaceChildren(empty("This report could not be loaded", "Use the refresh button to retry. Existing report files have not been changed."));
      }
    }
  }
  function reportURL(format, download = false) {
    const query = { name: state.selected, format };
    if (download) query.download = "1";
    return "/api/report?" + new URLSearchParams(query);
  }
  function renderRun() {
    const payload = state.payload, run = savedRun(), meta = summary(), coverage = object(run.coverage);
    $("welcome").hidden = true;
    $("workspace").hidden = false;
    $("report-title").textContent = present(object(run.case).name, present(meta.title, payload.name));
    const metadata = $("report-meta");
    metadata.replaceChildren(badge(statusLabel(payload.status), payload.status));
    if (meta.sample || payload.name === "sample") metadata.append(badge("SYNTHETIC", "synthetic"));
    const generated = object(run.case).generated_at || meta.generated_at;
    if (generated) metadata.append(element("span", "", "Report saved " + date(generated)));
    $("sample-banner").hidden = !(meta.sample || payload.name === "sample");
    $("report-actions").hidden = !payload.run;
    for (const format of ["html", "md", "json"]) $("download-" + format).href = reportURL(format, true);
    const findings = acceptedFindings(run), rejections = array(run.rejections);
    $("metric-accepted").textContent = payload.run ? count(findings.length, "—") : count(meta.verified, "—");
    $("metric-refused").textContent = payload.run ? count(rejections.length, "—") : count(meta.rejected, "—");
    $("metric-extracted").textContent = object(coverage.extraction).status === "measured" ? count(coverage.extraction.record_count, "—") : "—";
    $("metric-extracted-note").textContent = object(coverage.extraction).status === "measured" ? "(supplied count)" : object(coverage.extraction).status === "invalid" ? "(invalid summary; see Coverage)" : "(not measured)";
    $("metric-judgments").textContent = payload.run ? count(array(run.conclusions).length, "—") : "—";
    const evidenceHash = object(run.case).facts_sha256;
    $("evidence-hash").textContent = typeof evidenceHash === "string" && evidenceHash ? "evidence " + evidenceHash.slice(0, 16) + "…" : "";
    $("evidence-hash").title = typeof evidenceHash === "string" && evidenceHash ? "SHA-256 of the evidence store: " + evidenceHash : "";
    $("metric-inspected").textContent = object(coverage.inspection).status === "measured" ? count(coverage.inspection.record_count, "—") : "—";
    $("count-findings").textContent = payload.run ? count(findings.length, "") : "";
    $("count-needs").textContent = payload.run ? count(rejections.length, "") : "";
    $("count-activity").textContent = array(payload.events).length ? count(payload.events.length, "") : "";
    $("activity-refresh-label").textContent = isRunning() ? "REFRESHES EVERY 2 SECONDS" : "RECORDED ACTIVITY";
    // A view with nothing in it is not offered: no refusals, no recorded activity, no coverage measurements.
    const filled = {
      needs: rejections.length > 0,
      activity: array(payload.events).length > 0 || isRunning() || object(run.history).schema_version === 1,
      coverage: coverage.schema_version === 1,
    };
    for (const name of Object.keys(filled)) $("tab-" + name).hidden = !filled[name];
    $("tab-gap").hidden = !Object.values(filled).some(Boolean);
    if (filled[state.tab] === false) switchTab("summary");
    $("metric-extracted").parentElement.hidden = object(coverage.extraction).status !== "measured" && object(coverage.extraction).status !== "invalid";
    $("metric-inspected").parentElement.hidden = object(coverage.inspection).status !== "measured";
    $("metric-judgments").parentElement.hidden = !array(run.conclusions).length;
    renderProgress();
    // Share one exact revision across both views; equal counts do not mean equal records.
    const revision = JSON.stringify([payload.run, payload.events]);
    if (CONAN.graph) CONAN.graph.render(payload.run, payload.events, payload.name, revision);
    if (CONAN.report) {
      const has = (key) => Object.prototype.hasOwnProperty.call(run, key);
      const nothing = [];   // parts of a report this case has nothing for
      if (!array(run.rejections).length) nothing.push("needs");
      if (!array(run.conclusions).length) nothing.push("judgments");
      if (!["collection", "investigation", "case_answers", "answer_projection", "conflicts"].some(has)) nothing.push("workflow");
      if (!Object.keys(object(run.audit)).length && object(run.coverage).schema_version !== 1 && object(run.history).schema_version !== 1) nothing.push("activity");
      CONAN.report.open(payload.name, findings.map((finding) => String(finding.finding_id)), revision, nothing);
    }
    // The summary and the timeline draw the same records in plain words; they add no finding.
    const story = CONAN.story ? CONAN.story.open(payload.run, payload.name, revision) : null;
    if (CONAN.timeline) CONAN.timeline.render(story, payload.name);
    state.evidenceModel = CONAN.evidence ? CONAN.evidence.open(payload.run, revision) : null;
    if (CONAN.overview) CONAN.overview.render(story, payload.run, payload.brief, state.evidenceModel);
    renderFindings();
    renderNeeds();
    renderActivity();
    renderCoverage();
    if (payload.error) notice(present(payload.error), true);
    else if (state.connected) notice("");
    updateStartButton();
  }
  function renderProgress() {
    const status = state.payload.status;
    const show = ["running", "failed", "cancelled", "partial"].includes(status);
    $("run-progress").hidden = !show;
    $("run-progress").classList.toggle("terminal", status !== "running");
    $("stop-investigation").hidden = status !== "running" || state.activeName !== state.selected;
    $("stop-investigation").disabled = state.stopping;
    $("stop-investigation").textContent = state.stopping ? "Stopping…" : "Stop investigation";
    const events = array(state.payload.events);
    if (status === "running") {
      $("progress-title").textContent = state.stopping ? "Stopping the investigation" : "Investigation in progress";
      $("progress-description").textContent = events.length
        ? count(events.length) + " recent completed tool calls available. View Activity for the recorded work."
        : "Waiting for a completed tool call. A running call may not appear until it finishes.";
    } else {
      $("progress-title").textContent = ({ failed: "The investigation ended with an error", cancelled: "Investigation cancelled", partial: "This report contains partial work" })[status] || "";
      $("progress-description").textContent = state.payload.run
        ? "The available report is retained. Review its findings, missing evidence, and recorded limits."
        : "No report bundle is available yet. Recorded completed activity is shown below when available.";
    }
  }
  function searchable(finding) {
    return [finding.finding_id, finding.question, finding.english, array(finding.rules).join(" ")].filter(Boolean).join(" ").toLocaleLowerCase();
  }
  function renderFindings() {
    const overview = state.findingView === "overview" && state.evidenceModel;
    $("findings-overview").setAttribute("aria-pressed", String(!!overview));
    $("findings-exact").setAttribute("aria-pressed", String(!overview));
    const topics = $("evidence-topics"); topics.hidden = !overview;
    topics.replaceChildren();
    if (overview) {
      const available = CONAN.evidence.categories.filter(category => state.evidenceModel.groups.some(group => group.category === category.key));
      [{key: "all", label: "All topics"}, ...available].forEach(category => {
        const amount = state.evidenceModel.groups.filter(group => category.key === "all" || group.category === category.key).length;
        const button = element("button", "topic-chip" + (category.lane === undefined ? "" : " c" + category.lane), category.label + " · " + amount);
        button.type = "button"; button.setAttribute("aria-pressed", String(state.evidenceTopic === category.key));
        button.addEventListener("click", () => { state.evidenceTopic = category.key; renderFindings(); }); topics.append(button);
      });
      $("findings-view-count").textContent = state.evidenceModel.groups.length + " entries · " + state.evidenceModel.findings.length + " supporting findings";
      CONAN.evidence.render($("finding-list"), state.evidenceModel, state.evidenceTopic, state.search);
      $("finding-pagination").replaceChildren();
      renderUnverifiedFindings(); renderConclusions(); return;
    }
    const findings = acceptedFindings();
    $("findings-view-count").textContent = findings.length + " stored checker outcomes";
    const matches = state.search ? findings.filter((finding) => searchable(finding).includes(state.search.toLocaleLowerCase())) : findings;
    const container = $("finding-list");
    container.replaceChildren();
    if (!matches.length) {
      container.append(empty(state.search ? "No matching findings" : "No accepted findings are available", state.search
        ? "Try a finding ID, a question, or words from the finding."
        : isRunning() ? "The investigator is working. Accepted claims will appear when the server provides a report bundle."
        : "This report does not contain accepted findings. Activity and evidence requirements may still be available."));
    }
    if (matches.length) {
      const table = element("table", "grid-table"), head = element("thead"), headRow = element("tr"), body = element("tbody");
      ["Report", "ID", "Basis", "Statement", "Records", "Rules"].forEach((label) => { const th = element("th", "", label); th.scope = "col"; headRow.append(th); });
      head.append(headRow);
      matches.slice(0, state.findingLimit).forEach((finding) => {
        const row = element("tr", String(finding.finding_id) === String(state.selectedFinding) ? "selected" : "");
        row.tabIndex = 0;
        row.dataset.finding = present(finding.finding_id, "");
        const basis = element("td"), statement = element("td");
        basis.append(badge(finding.strength === "heuristic" ? "Heuristic" : present(finding.strength, "Rule type not recorded"), finding.strength === "heuristic" ? "heuristic" : "accepted"));
        statement.append(element("strong", "finding-heading", CONAN.evidence ? CONAN.evidence.title(finding) : present(finding.question)));
        statement.append(exactStatements(finding));
        const inspect = element("button", "text-button", "Inspect evidence & proof →"); inspect.type = "button";
        inspect.addEventListener("click", event => { event.stopPropagation(); openFinding(finding); }); statement.append(inspect);
        row.append(markCell(finding), element("td", "id", present(finding.finding_id)), basis, statement,
          element("td", "num", count(array(finding.cited_facts).length, "—")), element("td", "id", array(finding.rules).join(" ")));
        row.addEventListener("click", () => openFinding(finding));
        row.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openFinding(finding); } });
        body.append(row);
      });
      table.append(head, body);
      container.append(table);
    }
    const pagination = $("finding-pagination");
    pagination.replaceChildren();
    if (matches.length > state.findingLimit) {
      pagination.append(element("span", "", "Showing " + count(state.findingLimit) + " of " + count(matches.length)));
      const more = element("button", "button secondary", "Show 40 more");
      more.type = "button";
      more.addEventListener("click", () => { state.findingLimit += 40; renderFindings(); });
      pagination.append(more);
    }
    renderUnverifiedFindings();
    renderConclusions();
  }
  function exactStatements(finding) {
    const details = element("details", "exact-statements"), parts = array(finding.parts).filter(part => typeof object(part).english === "string");
    details.append(element("summary", "", parts.length > 1 ? "Read " + parts.length + " exact statements" : "Read exact statement"));
    details.addEventListener("click", event => event.stopPropagation());
    details.addEventListener("keydown", event => event.stopPropagation());
    details.addEventListener("toggle", () => { if (details.open && details.childElementCount === 1) {
      if (parts.length > 1) {
        const list = element("ol"); parts.forEach(part => list.append(element("li", "", part.english))); details.append(list);
      } else details.append(element("p", "", present(finding.english, "No fixed sentence was included.")));
    }});
    return details;
  }
  function browseEvidence(topic = "all", search = "") {
    state.findingView = "overview"; state.evidenceTopic = topic; state.search = search;
    $("finding-search").value = search; renderFindings(); switchTab("findings", true);
    $("panel-findings").scrollTop = 0;
  }
  function renderUnverifiedFindings() {
    const container = $("unverified-findings");
    const wasOpen = container.querySelector("details")?.open;
    container.replaceChildren();
    const rows = array(savedRun().findings).filter((finding) => !isAccepted(finding));
    if (!rows.length) return;
    const details = element("details", "interpretations");
    details.open = Boolean(wasOpen);
    details.append(element("summary", "", count(rows.length) + " unverified rows in the findings field · excluded from accepted results"),
      element("p", "", "These rows are not explicitly marked verified. They are preserved here as supplied content, not accepted findings or independently verified certificates."));
    rows.forEach((raw, index) => {
      const finding = object(raw), entry = element("details", "provenance");
      entry.append(element("summary", "", "Row " + (index + 1) + " · " + present(finding.finding_id, "No finding ID") + " · status " + present(finding.status, "unknown")), code(raw));
      details.append(entry);
    });
    container.append(details);
  }
  function renderConclusions() {
    const container = $("conclusions"), conclusions = array(savedRun().conclusions);
    const wasOpen = container.querySelector("details")?.open;
    container.replaceChildren();
    if (!conclusions.length || state.search) return;
    const details = element("details", "interpretations");
    details.open = Boolean(wasOpen);
    details.append(element("summary", "", count(conclusions.length) + " investigator interpretations · not certified"), element("p", "", "These are the investigator’s judgments, outside Lean. Citing accepted findings does not certify an interpretation or a causal claim."));
    conclusions.forEach((item) => {
      const entry = element("div", "interpretation-item");
      entry.append(element("span", "small-mono", present(item.conclusion_id)), element("p", "", present(item.text)), element("span", "small-mono", "Cites findings: " + (array(item.finding_ids).join(", ") || "not recorded")));
      details.append(entry);
    });
    container.append(details);
  }
  function renderNeeds() {
    const container = $("needs-list"), rejections = array(savedRun().rejections);
    container.replaceChildren();
    if (!rejections.length) {
      container.append(empty("No refusal diagnostics are available", "This does not establish that the investigation is complete or that no evidence is missing."));
      return;
    }
    rejections.slice(0, state.needsLimit).forEach((rejection) => {
      const gap = object(rejection.proof_gap), diagnostic = gap.status === "diagnostic";
      const card = element("article", "finding-card needs-card"), body = element("div", "finding-body");
      const identity = element("div", "finding-identity");
      identity.append(element("span", "finding-id", present(rejection.finding_id)), badge("NOT ESTABLISHED", "needs"));
      body.append(identity);
      if (rejection.question) body.append(element("p", "finding-question", rejection.question));
      const sentence = element("p", "finding-sentence", diagnostic ? present(gap.summary) : "The checker refused this proposal. Structured evidence requirements were not recorded.");
      sentence.style.marginTop = "12px";
      body.append(sentence);
      card.append(body);
      if (diagnostic) {
        const requirements = element("div", "requirement-list");
        array(gap.requirements).forEach((raw) => {
          const requirement = object(raw), row = element("div", "requirement");
          row.append(element("strong", "", present(requirement.category, "Evidence requirement").replaceAll("_", " ")));
          if (requirement.reason) row.append(element("p", "", requirement.reason));
          if (requirement.action) row.append(element("p", "action", requirement.action));
          if (array(requirement.fact_ids).length) row.append(element("span", "small-mono", "Proposed fact IDs: " + requirement.fact_ids.join(", ")));
          if (requirement.required !== undefined || requirement.observed !== undefined) {
            const details = element("details", "provenance");
            details.append(element("summary", "", "Inspect diagnostic conditions"), code({ ...(requirement.observed !== undefined ? { observed: requirement.observed } : {}), ...(requirement.required !== undefined ? { required: requirement.required } : {}) }));
            row.append(details);
          }
          requirements.append(row);
        });
        if (gap.disclaimer) requirements.append(element("p", "field-help", gap.disclaimer));
        card.append(requirements);
      }
      container.append(card);
    });
    if (rejections.length > state.needsLimit) {
      const more = element("button", "button secondary", "Show 40 more refused proposals");
      more.type = "button";
      more.addEventListener("click", () => { state.needsLimit += 40; renderNeeds(); });
      container.append(more);
    }
  }
  function renderActivity() {
    const container = $("activity-list");
    const open = new Set([...container.querySelectorAll("details[open]")].map((item) => item.dataset.eventKey));
    container.replaceChildren();
    const events = array(state.payload.events).slice().sort((left, right) => (Number(right.sequence) || 0) - (Number(left.sequence) || 0));
    if (!events.length) container.append(empty("No completed audit calls are available", isRunning()
      ? "The current tool call may still be running. This view refreshes every two seconds."
      : "This may be a legacy report or a run without an audit log. Missing activity is not evidence that no work occurred."));
    else {
      const feed = element("div", "activity-feed");
      const names = { forms: "Read available claim forms", sql: "Queried the fact store", fact: "Inspected an evidence record", check: "Submitted a claim to the checker", conclude: "Recorded an investigator interpretation" };
      events.slice(0, 100).forEach((event) => {
        const row = element("article", "activity-row");
        const title = element("div", "activity-title");
        title.append(element("span", "", names[event.tool] || present(event.tool, "Recorded tool call")), badge(present(event.outcome, "unknown"), event.outcome));
        const body = element("div", "activity-body");
        body.append(title, element("div", "activity-meta", "Sequence " + present(event.sequence, "unknown") + (event.finding_id ? " · Finding " + event.finding_id : "")));
        if (event.arguments !== undefined && event.arguments !== null) {
          const details = element("details");
          details.dataset.eventKey = present(event.sequence) + ":" + present(event.tool);
          details.open = open.has(details.dataset.eventKey);
          details.append(element("summary", "", "View recorded arguments"), code(event.arguments));
          body.append(details);
        }
        const timestamp = element("time", "activity-time", date(event.completed_at, timeDate));
        if (event.completed_at) { timestamp.dateTime = event.completed_at; timestamp.title = String(event.completed_at); }
        row.append(element("span", "activity-symbol", "↳"), body, timestamp);
        feed.append(row);
      });
      container.append(feed);
      container.append(element("p", "field-help", "Showing " + count(Math.min(100, events.length)) + " supplied recent calls. Displayed times use your local time zone; hover a time for the recorded timestamp."));
    }
    renderHistory();
  }
  function renderHistory() {
    const container = $("history-list"), history = object(savedRun().history);
    container.replaceChildren();
    if (history.schema_version !== 1) return;
    container.append(element("h3", "history-heading", "Recorded claim attempts"), element("p", "history-help", "Explicit revision links only. Recorded checker outcomes are not independent verification, and the log does not guarantee complete history."));
    const integrity = object(history.audit_integrity).status;
    if (integrity === "failed") container.append(element("div", "notice error", "Invalid history audit. Treat these recorded events as diagnostics only."));
    else if (integrity !== "passed") container.append(element("p", "field-help", "History audit integrity: " + present(integrity, "unavailable") + ". No integrity guarantee is supplied."));
    const attempts = array(history.attempts);
    if (!attempts.length) container.append(element("p", "history-help", history.available ? "No attempts appear in the supplied history." : "Attempt history is unavailable; this does not establish that no attempts occurred."));
    else {
      container.append(historyTable(attempts.slice(-40)));
      if (attempts.length > 40) container.append(element("p", "field-help", "Last 40 of " + count(attempts.length) + " recorded attempts, in supplied order. Download the JSON bundle for the full supplied history."));
    }
    if (array(history.unmatched_proposals).length) {
      container.append(element("h3", "history-heading", "Proposals with unknown position in the audit"), element("p", "history-help", "These proposal rows cannot be placed in the recorded event sequence."), historyTable(history.unmatched_proposals.slice(-40)));
    }
  }
  function historyTable(attempts) {
    const wrap = element("div", "history-table-wrap"), table = element("table", "history-table");
    const head = element("thead"), row = element("tr");
    ["Attempt / finding", "Outcome", "Explicit revision"].forEach((label) => { const th = element("th", "", label); th.scope = "col"; row.append(th); });
    head.append(row); table.append(head);
    const body = element("tbody");
    attempts.forEach((attempt) => {
      const tr = element("tr"), identity = element("td"), outcome = element("td"), revision = element("td");
      identity.append(element("div", "small-mono", present(attempt.attempt_id)), element("div", "", present(attempt.finding_id, "No finding ID")));
      outcome.append(badge(present(attempt.status, "unknown"), attempt.status));
      if (attempt.duplicate_of) outcome.append(element("div", "field-help", "Duplicate of " + attempt.duplicate_of + "; no new proof"));
      if (attempt.error) outcome.append(element("div", "field-help", attempt.error));
      revision.textContent = attempt.revises !== undefined && attempt.revises !== null ? "Revises " + present(attempt.revises) + " · " + present(attempt.revision_status, "unknown") : "None recorded";
      if (attempt.revision_error) revision.append(element("div", "field-help", attempt.revision_error));
      tr.append(identity, outcome, revision); body.append(tr);
    });
    table.append(body); wrap.append(table); return wrap;
  }
  function coverageRow(label, value) {
    const row = element("div", "coverage-row");
    row.append(element("span", "", label), element("strong", "", present(value, "Unmeasured")));
    return row;
  }
  function coverageCard(title, status) {
    const card = element("section", "coverage-card"), heading = element("h3", "", title);
    if (status) heading.append(badge(status, status === "invalid" ? "invalid" : ""));
    card.append(heading); return card;
  }
  function renderCoverage() {
    const container = $("coverage-content"), run = savedRun(), coverage = object(run.coverage);
    container.replaceChildren();
    if (coverage.schema_version !== 1) {
      container.append(empty("Coverage measurements are unavailable", "This saved report does not include the supported coverage summary. Unknown measurements are not zero."));
    } else {
      const grid = element("div", "coverage-grid");
      const records = coverageCard("Records and findings");
      records.append(coverageRow("Extracted records", measure(coverage.extraction, "record_count")), coverageRow("Explicitly inspected records", measure(coverage.inspection, "record_count")), coverageRow("Distinct cited records", measure(coverage.citations, "record_count")), coverageRow("Recorded accepted findings", measure(coverage.certification, "finding_count")), element("p", "", "SQL results and aggregates are not counted as full-record inspection. Logged access does not establish that a model understood a record."));
      const q = object(coverage.questions), questions = coverageCard("Public question answer presence", present(q.status, "unmeasured"));
      questions.append(coverageRow("Public questions", q.status === "invalid" ? "Invalid" : count(q.total_count)));
      [["Answers supplied", "answered_count"], ["Explicitly unknown", "unknown_count"], ["Explicitly unanswered", "unanswered_count"], ["No response supplied", "missing_count"]].forEach(([label, key]) => questions.append(coverageRow(label, measure(q, key))));
      questions.append(element("p", "", "Answer presence is not correctness, completeness, or forensic truth. No answer key is used for these counts."));
      const failures = object(coverage.failures), tools = object(failures.tools), extraction = object(failures.extraction);
      const problems = coverageCard("Execution and source limits");
      problems.append(coverageRow("Run outcome", present(object(failures.run).status, "Unmeasured")), coverageRow("Tool errors", measure(tools, "error_count")), coverageRow("Refused tool calls", measure(tools, "rejected_count")), coverageRow("Reader failures", measure(extraction, "reader_failure_count")), coverageRow("Unsupported sources", measure(extraction, "unsupported_source_count")), coverageRow("Extraction warnings", measure(extraction, "warning_count")), coverageRow("Unclassified extraction issues", measure(extraction, "unclassified_issue_count")));
      const issues = array(extraction.issues);
      const messages = [];
      for (const [key, section] of Object.entries(coverage)) if (section && typeof section === "object" && !Array.isArray(section)) array(section.problems).forEach((message) => messages.push(key + ": " + message));
      for (const section of [tools, extraction]) array(section.problems).forEach((message) => messages.push(String(message)));
      if (issues.length || messages.length) {
        const details = element("details", "provenance");
        details.append(element("summary", "", "Inspect reported issues"));
        const list = element("ul", "coverage-notes");
        issues.forEach((issue) => list.append(element("li", "", present(issue.category) + ": " + present(issue.message))));
        messages.forEach((message) => list.append(element("li", "", message)));
        details.append(list); problems.append(details);
      }
      const inspection = object(coverage.inspection), scope = coverageCard("Measurement boundaries");
      scope.append(coverageRow("Inspection audit integrity", present(inspection.audit_integrity, "Unavailable")), coverageRow("Certificate replay by this viewer", "Not performed"));
      const list = element("ul", "coverage-notes");
      array(coverage.limitations).forEach((message) => list.append(element("li", "", message)));
      if (list.childElementCount) scope.append(list);
      else scope.append(element("p", "", "Supplied record counts do not establish evidence completeness. Independent verification must be performed separately."));
      grid.append(records, questions, problems, scope);
      container.append(grid);
    }
    const audit = object(run.audit), auditCard = coverageCard("Audit integrity", present(audit.status, "unavailable"));
    auditCard.classList.add("full-width");
    auditCard.style.marginTop = "16px";
    if (audit.status === "invalid" || audit.passed === false) {
      auditCard.classList.add("invalid-audit");
      auditCard.append(element("div", "notice error", "Invalid audit. The recorded events are diagnostic only; this viewer does not repair or independently recheck the log."));
    } else if (audit.status === "valid" && audit.passed === true) auditCard.append(element("p", "", "The bundle reports a passed integrity check. This viewer does not recheck the audit file."));
    else auditCard.append(element("p", "", "An audit integrity result is not available in this report."));
    auditCard.append(coverageRow("Recorded completed events", count(audit.count)), coverageRow("Audit file (literal path)", present(audit.path)), coverageRow("File SHA-256", present(audit.sha256)), coverageRow("Chain head", present(audit.head)), coverageRow("Expected head supplied", present(audit.expected_head, "Not supplied")));
    array(audit.problems).forEach((message) => auditCard.append(element("p", "", message)));
    auditCard.append(element("p", "", "Integrity does not authenticate an author or establish complete history. Detecting a complete rewrite requires an independently retained checkpoint."));
    container.append(auditCard);
  }

  function detailField(list, name, value, mono = false) {
    const row = element("div");
    row.append(element("dt", "", name), element("dd", mono ? "code" : "", present(value)));
    list.append(row);
  }
  function factTime(row) {
    if (!Number.isSafeInteger(row.t)) return row.t === undefined || row.t === null ? "Not recorded" : "Not an exact browser integer; inspect the original JSON artifact.";
    const time = new Date(row.t / 1000);
    return (Number.isNaN(time.getTime()) ? "Outside the browser’s date range" : time.toISOString()) + "\n" + row.t + " microseconds since the Unix epoch";
  }
  const RECORD_PAGE = 40;
  function recordCard(row, conflict = false) {
    const record = element("article", "evidence-record"), heading = element("h3", "", "Record #" + present(row.id));
    heading.append(badge(present(row.kind, "Kind unavailable")));
    record.append(heading);
    if (conflict) record.append(element("div", "notice error", "Conflicting copied rows share this fact ID. This viewer keeps them separate and does not resolve the conflict."));
    const fields = element("dl", "evidence-fields"), provenance = object(row.prov);
    if (CONAN.evidence) CONAN.evidence.properties(row).forEach(property => detailField(fields, property.label, property.value));
    else { detailField(fields, "Object", row.obj_text === undefined ? row.obj : row.obj_text);
      detailField(fields, "Related value", row.aux_text === undefined ? row.aux : row.aux_text); }
    detailField(fields, "Image / exhibit", [provenance.image, provenance.exhibit].filter((value) => value !== undefined && value !== null).join(" · ") || undefined);
    detailField(fields, "Artifact", provenance.artifact, true);
    detailField(fields, "Recorded time", factTime(row), true);
    detailField(fields, "Time meaning", provenance.time_meaning || provenance.timestamp_semantics);
    detailField(fields, "Uncertainty", row.res === undefined || row.res === null ? undefined : present(row.res) + " microseconds");
    detailField(fields, "Parser / tool", [provenance.parser, provenance.tool].filter((value) => value !== undefined && value !== null).join(" · ") || undefined);
    detailField(fields, "Row SHA-256", row.row_sha256, true);
    record.append(fields);
    // The full copied row is rendered only when it is opened.
    const copied = element("details", "provenance");
    copied.append(element("summary", "", "Full copied record and provenance"));
    copied.addEventListener("toggle", () => { if (copied.open && copied.childElementCount === 1) copied.append(code(row)); });
    record.append(copied);
    return record;
  }
  function inspect(title, summary, evidence, proof) {
    $("detail-title").textContent = title;
    $("detail-summary").replaceChildren(...summary);
    $("detail-evidence").replaceChildren(...evidence);
    $("detail-proof").replaceChildren(...(proof || []));
    document.querySelector(".detail-tabs").hidden = !proof;
    switchDetail("evidence");
    $("detail-evidence").scrollTop = 0;
    $("detail-summary").scrollTop = 0;
  }
  function clearInspector() {
    state.selectedFinding = null;
    inspect("Inspector", [element("p", "inspector-empty", "Select something on the timeline, in the graph or in a table to see its records, source and proof.")], [], null);
  }
  // A finding can be marked for the examiner's report from the table or the inspector.
  function markCell(finding) {
    const cell = element("td", "mark"), box = element("input");
    box.type = "checkbox";
    box.dataset.mark = String(finding.finding_id);
    box.checked = !!CONAN.report && CONAN.report.has(finding.finding_id);
    box.setAttribute("aria-label", "Include " + present(finding.finding_id) + " in the report");
    box.addEventListener("change", () => { if (CONAN.report) CONAN.report.toggle(finding.finding_id, box.checked); });
    cell.addEventListener("click", (event) => event.stopPropagation());   // ticking a box does not open the row
    cell.addEventListener("keydown", (event) => event.stopPropagation());
    cell.append(box);
    return cell;
  }
  function markButton(finding) {
    const button = element("button", "text-button mark-button");
    button.type = "button";
    button.dataset.markButton = String(finding.finding_id);
    const label = () => { const on = !!CONAN.report && CONAN.report.has(finding.finding_id); button.textContent = on ? "✓ In report — remove" : "Add to report"; button.setAttribute("aria-pressed", String(on)); };
    button.addEventListener("click", () => { if (CONAN.report) CONAN.report.toggle(finding.finding_id); });
    button.refresh = label;
    label();
    return button;
  }
  document.addEventListener("conan:marks", () => {
    document.querySelectorAll("input[data-mark]").forEach((box) => { box.checked = CONAN.report.has(box.dataset.mark); });
    document.querySelectorAll("button[data-mark-button]").forEach((button) => button.refresh && button.refresh());
  });
  function openFinding(finding) {
    if (!isAccepted(finding)) {
      notice("This row is not an accepted finding. Inspect its supplied contents in the unverified rows disclosure.", true);
      return;
    }
    state.selectedFinding = finding.finding_id;
    document.querySelectorAll("#finding-list tr[data-finding]").forEach((row) => row.classList.toggle("selected", row.dataset.finding === String(finding.finding_id)));
    const badges = element("div", "finding-identity");
    badges.append(badge("CHECKER ACCEPTED", "accepted"), badge(present(finding.strength, "Strength not recorded"), finding.strength === "heuristic" ? "heuristic" : ""));
    const summary = [badges];
    summary.push(element("p", "statement", CONAN.evidence ? CONAN.evidence.title(finding) : present(finding.question)));
    summary.push(exactStatements(finding));
    const show = element("button", "text-button", "Show in proof graph →");
    show.type = "button";
    show.addEventListener("click", () => { switchTab("graph"); if (CONAN.graph) CONAN.graph.focusFinding(String(finding.finding_id), finding); });
    const actions = element("div", "detail-actions");
    actions.append(show, markButton(finding));
    summary.push(actions);
    const rows = array(finding.cited_facts);
    const evidence = [element("p", "detail-intro", rows.length + (rows.length === 1 ? " cited record." : " cited records.") + " Provenance is bound metadata; it does not prove that the parser or its interpretation is correct.")];
    if (!rows.length) evidence.push(empty("No copied records", "This bundle does not include evidence records for this finding."));
    const ids = new Map();
    rows.forEach((row) => {
      const identity = JSON.stringify(row.id), serialized = JSON.stringify(row);
      if (!ids.has(identity)) ids.set(identity, new Set());
      ids.get(identity).add(serialized);
    });
    // Long citation lists are rendered a page at a time.
    const cards = (from) => rows.slice(from, from + RECORD_PAGE).map((row) => recordCard(row, ids.get(JSON.stringify(row.id)).size > 1));
    evidence.push(...cards(0));
    if (rows.length > RECORD_PAGE) {
      let shown = RECORD_PAGE;
      const more = element("button", "button", "Show " + RECORD_PAGE + " more of " + count(rows.length));
      more.type = "button";
      more.addEventListener("click", () => {
        more.before(...cards(shown));
        shown += RECORD_PAGE;
        if (shown >= rows.length) more.remove();
      });
      evidence.push(more);
    }
    const proof = [element("p", "detail-caveat", "This is the saved claim and embedded Lean source. The viewer has not independently verified the certificate. Use cop verify with the original evidence store to replay verification.")];
    const fields = element("dl", "evidence-fields");
    detailField(fields, "Trust tier", finding.trust_tier);
    detailField(fields, "Declared axioms", finding.axioms);
    detailField(fields, "Rules", array(finding.rules).length ? finding.rules.join(", ") : undefined);
    proof.push(fields, element("h3", "proof-heading", "Declared claim"));
    proof.push(finding.claim !== undefined ? code(finding.claim) : element("p", "detail-intro", "The claim was not included in this bundle."));
    proof.push(element("h3", "proof-heading", "Embedded Lean source"));
    proof.push(typeof finding.lean === "string" && finding.lean.trim() ? code(finding.lean) : element("p", "detail-intro", "Embedded Lean source was not included. No filesystem path is inferred."));
    inspect("Finding " + present(finding.finding_id), summary, evidence, proof);
  }
  function switchTab(name, focus = false) {
    state.tab = name;
    document.querySelectorAll("[data-tab]").forEach((button) => {
      const active = button.dataset.tab === name;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      $("panel-" + button.dataset.tab).hidden = !active;
      if (focus && active) button.focus();
    });
    $("shell").dataset.tab = name;   // the Summary and Report tabs take the inspector's room; the Report prints alone
    if (name === "graph" && CONAN.graph) CONAN.graph.resize();
    if (name === "timeline" && CONAN.timeline) CONAN.timeline.activate();
    if (name === "summary" && CONAN.overview) CONAN.overview.activate();
    if (CONAN.report) { if (name === "report") CONAN.report.activate(); else CONAN.report.deactivate(); }
  }
  function switchDetail(name, focus = false) {
    state.detailTab = name;
    document.querySelectorAll("[data-detail-tab]").forEach((button) => {
      const active = button.dataset.detailTab === name;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      $("detail-" + button.dataset.detailTab).hidden = !active;
      if (focus && active) button.focus();
    });
  }
  function tabKeys(event, names, active, change) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const index = names.indexOf(active);
    const next = event.key === "Home" ? 0 : event.key === "End" ? names.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + names.length) % names.length;
    change(names[next], true);
  }
  function updateStartButton() {
    const backend = array(state.config && state.config.backends).find((item) => item.id === $("investigation-backend").value);
    const ready = state.config && state.config.token && backend && backend.available;
    $("start-investigation").disabled = !ready || Boolean(state.activeName) || state.submitting;
    $("start-investigation").textContent = state.submitting ? "Starting…" : "Start investigation";
    if (state.activeName) $("backend-help").textContent = "An investigation is already running. Stop it or wait for it to finish before starting another.";
    else if (!ready) $("backend-help").textContent = "No available backend is selected. Configure a supported provider locally and refresh the workspace.";
    else $("backend-help").textContent = "Detected locally. Provider authentication has not been checked. Starting a run may incur provider usage.";
  }
  function applyConfig(config) {
    state.config = config;
    state.activeName = config.active_run || null;
    const defaults = object(config.defaults), select = $("investigation-backend");
    select.replaceChildren();
    array(config.backends).forEach((backend) => {
      const option = element("option", "", present(backend.label, backend.id) + (backend.available ? "" : " · unavailable"));
      option.value = String(backend.id);
      option.disabled = !backend.available;
      select.append(option);
    });
    const preferred = array(config.backends).find((backend) => backend.id === defaults.backend && backend.available) || array(config.backends).find((backend) => backend.available);
    if (preferred) select.value = preferred.id;
    else if (!select.options.length) { const option = element("option", "", "No backend configured"); option.value = ""; select.append(option); }
    $("facts-path").value = defaults.facts || "";
    $("investigation-model").value = preferred && preferred.id === defaults.backend ? defaults.model || "" : "";
    if (typeof defaults.minutes === "number" && defaults.minutes >= 1) $("investigation-minutes").value = defaults.minutes;
    updateStartButton();
  }
  function openNew() {
    $("form-error").hidden = true;
    updateStartButton();
    $("new-dialog").showModal();
    $("investigation-title").focus();
  }
  function newName(title) {
    const stem = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 32) || "investigation";
    return stem + "-" + Date.now().toString(36);
  }
  async function startInvestigation(event) {
    event.preventDefault();
    if (state.submitting || $("start-investigation").disabled || !$("investigation-form").reportValidity()) return;
    state.submitting = true;
    $("form-error").hidden = true;
    updateStartButton();
    const title = $("investigation-title").value.trim();
    const body = { name: newName(title), facts: $("facts-path").value.trim(), title,
      brief: $("investigation-brief").value.trim(),
      questions: $("investigation-questions").value.split(/\r?\n/).map((question) => question.trim()).filter(Boolean),
      backend: $("investigation-backend").value, model: $("investigation-model").value.trim(),
      minutes: Number($("investigation-minutes").value) };
    try {
      const result = await api("/api/investigations", body);
      state.activeName = result.name;
      $("new-dialog").close();
      $("tab-activity").hidden = false;
      switchTab("activity");
      await refreshRuns();
      await selectRun(result.name);
      schedulePoll(2000);
    } catch (error) {
      $("form-error").textContent = error.message;
      $("form-error").hidden = false;
    } finally { state.submitting = false; updateStartButton(); }
  }
  async function stopInvestigation() {
    if (!state.selected || state.stopping || state.activeName !== state.selected) return;
    state.stopping = true;
    const name = state.selected;
    renderProgress();
    try {
      await api("/api/stop", { name });
      await refreshRuns();
      if (state.selected === name) await loadRun(name);
    } catch (error) { notice(error.message, true); }
    finally { state.stopping = false; if (state.payload) renderProgress(); }
  }
  function schedulePoll(delay) {
    clearTimeout(state.timer);
    state.timer = setTimeout(poll, delay);
  }
  async function poll() {
    try {
      const wasRunning = isRunning();
      await refreshRuns();
      if (state.selected && (wasRunning || summary().status === "running")) await loadRun(state.selected, true);
      if (!state.selected && state.runs.length) await selectRun(state.activeName || state.runs[0].name);
    } catch (_) { /* Keep the last available report; connection status shows failures. */ }
    schedulePoll(state.activeName || isRunning() ? 2000 : 10000);
  }
  async function refreshAll() {
    $("refresh-runs").disabled = true;
    try {
      const config = await api("/api/config");
      // Keep an open, edited form intact; the server token and availability still refresh.
      if ($("new-dialog").open) { state.config = config; state.activeName = config.active_run || null; updateStartButton(); }
      else applyConfig(config);
      await refreshRuns();
      if (state.selected) await loadRun(state.selected);
      else if (state.runs.length) await selectRun(state.activeName || state.runs[0].name);
      else { $("welcome").hidden = false; $("workspace").hidden = true; notice(""); }
    } catch (error) { notice(error.message, true); }
    finally { $("refresh-runs").disabled = false; }
  }

  document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => $(button.dataset.close).close()));
  document.querySelectorAll("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  }));
  document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.tab)));
  document.querySelectorAll("[data-detail-tab]").forEach((button) => button.addEventListener("click", () => switchDetail(button.dataset.detailTab)));
  document.querySelector(".report-tabs").addEventListener("keydown", (event) => tabKeys(event, ["summary", "timeline", "graph", "findings", "needs", "activity", "coverage", "report"].filter((name) => !$("tab-" + name).hidden), state.tab, switchTab));
  $("open-report").addEventListener("click", () => switchTab("report", true));
  document.querySelector(".detail-tabs").addEventListener("keydown", (event) => tabKeys(event, ["evidence", "proof"], state.detailTab, switchDetail));
  $("finding-search").addEventListener("input", (event) => { state.search = event.target.value.trim(); state.findingLimit = 40; renderFindings(); });
  for (const [id, view] of [["findings-overview", "overview"], ["findings-exact", "exact"]]) $(id).addEventListener("click", () => {
    state.findingView = view; state.findingLimit = 40; renderFindings();
  });
  $("open-demo").addEventListener("click", async () => { await selectRun("sample"); switchTab("summary", true); });
  $("new-investigation").addEventListener("click", openNew);
  $("welcome-new").addEventListener("click", openNew);
  $("refresh-runs").addEventListener("click", refreshAll);
  $("investigation-form").addEventListener("submit", startInvestigation);
  $("investigation-backend").addEventListener("change", () => {
    const defaults = object(state.config && state.config.defaults);
    if ($("investigation-model").value === defaults.model && $("investigation-backend").value !== defaults.backend) $("investigation-model").value = "";
    updateStartButton();
  });
  $("stop-investigation").addEventListener("click", stopInvestigation);
  $("sidebar-toggle").addEventListener("click", () => {
    const hidden = $("shell").classList.toggle("no-sidebar");
    $("sidebar-toggle").setAttribute("aria-expanded", String(!hidden));
    if (CONAN.graph) CONAN.graph.resize();
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".download-menu")) document.querySelector(".download-menu").open = false;
  });
  window.addEventListener("beforeunload", () => clearTimeout(state.timer));

  CONAN.app = { element, badge, code, present, openFinding, recordCard, inspect, switchTab, browseEvidence };

  async function init() {
    const [config, runs] = await Promise.allSettled([api("/api/config"), api("/api/runs")]);
    if (config.status === "fulfilled") applyConfig(config.value);
    else notice(config.reason.message, true);
    if (runs.status === "fulfilled") {
      state.runs = array(runs.value.runs).filter((entry) => typeof entry.name === "string");
      renderRuns();
      const selected = state.activeName || state.runs.find((entry) => !entry.sample)?.name || state.runs[0]?.name;
      if (selected) await selectRun(selected);
      else $("welcome").hidden = false;
    } else {
      $("run-list").replaceChildren(element("p", "sidebar-empty", "Reports could not be loaded. Use refresh to reconnect."));
      $("welcome").hidden = false;
      notice(runs.reason.message, true);
    }
    schedulePoll(state.activeName ? 2000 : 10000);
  }
  init();
})();
