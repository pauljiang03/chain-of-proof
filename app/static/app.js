"use strict";

// Workbench client. Record contents are always inserted as text, never as HTML.
(() => {
  const CONAN = (window.CONAN = window.CONAN || {});
  const $ = (id) => document.getElementById(id);
  const state = {
    config: null, runs: [], selected: null, payload: null, activeName: null,
    tab: "summary", detailTab: "evidence", search: "", findingLimit: 40, selectedFinding: null,
    findingView: "overview", evidenceTopic: "all", evidenceModel: null, submitting: false, stopping: false,
    request: 0, timer: null, connected: false, sidebarRenderKey: null,
  };
  const statuses = new Set(["running", "completed", "partial", "failed", "cancelled", "saved"]);
  const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
  const shortDate = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
  const longDate = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });

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
    catch (_) { connection(false); throw new Error("Cannot reach the local server. Check that conan serve is running, then refresh."); }
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
    // Clear the previous case first: a failed load must not leave another case's details visible.
    for (const id of ["conclusions", "unverified-findings", "finding-pagination"]) $(id).replaceChildren();
    for (const id of ["metric-accepted", "metric-refused", "metric-judgments", "metric-extracted", "metric-inspected"]) $(id).textContent = "—";
    $("evidence-hash").textContent = "";
    $("count-findings").textContent = "";
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
    for (const format of ["html", "md", "json"]) {
      const link = $("download-" + format);
      link.href = reportURL(format, true);
      // Without a file name the desktop window opens the file in place of the app.
      link.download = String(state.selected).replace(/\//g, "-") + "." + format;
    }
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
    $("metric-extracted").parentElement.hidden = object(coverage.extraction).status !== "measured" && object(coverage.extraction).status !== "invalid";
    $("metric-inspected").parentElement.hidden = object(coverage.inspection).status !== "measured";
    $("metric-judgments").parentElement.hidden = !array(run.conclusions).length;
    renderProgress();
    // One exact revision for every view; equal counts do not mean equal records.
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
    const story = CONAN.story ? CONAN.story.open(payload.run, payload.name, revision) : null;
    if (CONAN.timeline) CONAN.timeline.render(story, payload.name);
    state.evidenceModel = CONAN.evidence ? CONAN.evidence.open(payload.run, revision) : null;
    if (CONAN.overview) CONAN.overview.render(story, payload.run, payload.brief, state.evidenceModel, payload.narrative);
    renderFindings();
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
        ? "The investigator is working. " + count(events.length) + " recent tool calls completed."
        : "Waiting for a completed tool call. A running call may not appear until it finishes.";
    } else {
      $("progress-title").textContent = ({ failed: "The investigation ended with an error", cancelled: "Investigation cancelled", partial: "This report contains partial work" })[status] || "";
      $("progress-description").textContent = state.payload.run
        ? "The findings verified before it ended are kept."
        : "No findings were saved.";
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
    details.append(element("summary", "", count(conclusions.length) + " investigator interpretations · not certified"));
    conclusions.forEach((item) => {
      const entry = element("div", "interpretation-item");
      entry.append(element("span", "small-mono", present(item.conclusion_id)), element("p", "", present(item.text)), element("span", "small-mono", "Cites findings: " + (array(item.finding_ids).join(", ") || "not recorded")));
      details.append(entry);
    });
    container.append(details);
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
    const label = () => { const on = !!CONAN.report && CONAN.report.has(finding.finding_id); button.textContent = on ? "In report — remove" : "Add to report"; button.setAttribute("aria-pressed", String(on)); };
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
    const evidence = [element("p", "detail-intro", rows.length + (rows.length === 1 ? " cited record." : " cited records."))];
    if (!rows.length) evidence.push(empty("No copied records", "This bundle does not include evidence records for this finding."));
    const ids = new Map();
    rows.forEach((row) => {
      const identity = JSON.stringify(row.id), serialized = JSON.stringify(row);
      if (!ids.has(identity)) ids.set(identity, new Set());
      ids.get(identity).add(serialized);
    });
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
    const proof = [];
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
    $("shell").dataset.tab = name;   // the stylesheet hides the inspector on Summary and Report
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
  const LACKS = { key: "needs a key", packages: "not installed", program: "not installed" };
  const chosenBackend = () => array(state.config && state.config.backends).find((item) => item.id === $("investigation-backend").value);
  function updateStartButton() {
    const backend = chosenBackend();
    const ready = state.config && state.config.token && backend && backend.available;
    $("start-investigation").disabled = !ready || Boolean(state.activeName) || state.submitting;
    $("start-investigation").textContent = state.submitting ? "Starting…" : "Start investigation";
    const label = backend ? present(backend.label, backend.id) : "", minutes = $("investigation-minutes").value;
    const standard = backend && typeof backend.model === "string" ? backend.model : "";
    $("investigation-model").placeholder = standard || "default";
    $("investigation-settings").textContent = [label, $("investigation-model").value.trim() || standard, minutes ? minutes + " min" : ""].filter(Boolean).join(" · ");
    // The server keeps a typed API key and never sends it back.
    const lacks = backend ? backend.needs : null, source = backend ? backend.key : null;
    $("api-key-field").hidden = !(lacks === "key" && backend.can_save_key === true);
    $("api-key-status").hidden = !source;
    $("api-key-source").textContent = source === "saved" ? "An API key is saved on this computer." + (state.keyNote ? " " + state.keyNote : "")
      : source ? "Uses the key in the ANTHROPIC_API_KEY setting of this computer." : "";
    $("api-key-remove").hidden = source !== "saved";
    $("api-install-note").hidden = !array(state.config && state.config.backends).some((item) => item.id === "deepagents" && item.needs === "packages");
    let help;
    if (state.activeName) help = "Another investigation is running. Stop it or wait for it to finish.";
    else if (lacks === "key") help = backend.can_save_key === true ? "Add your Anthropic API key to start." : "Set ANTHROPIC_API_KEY on this computer, then start again.";
    else if (lacks) help = label + " is not installed on this computer.";
    else if (!ready) help = "No AI service is set up on this computer.";
    else if (backend.id === "deepagents") help = "Uses your Anthropic API key. Anthropic bills it for the run and receives the records the investigator reads.";
    else help = "Runs on your " + label + " account.";
    $("backend-help").textContent = help;
  }
  function fillBackends(chosen) {
    const config = object(state.config), select = $("investigation-backend");
    select.replaceChildren();
    array(config.backends).forEach((backend) => {
      const option = element("option", "", present(backend.label, backend.id) + (backend.available ? "" : " · " + (LACKS[backend.needs] || "unavailable")));
      option.value = String(backend.id);
      option.disabled = !backend.available && backend.needs !== "key";   // a service that only lacks a key can be chosen, to add one
      select.append(option);
    });
    const usable = (backend) => backend.available || backend.needs === "key";
    const wanted = array(config.backends).find((backend) => backend.id === chosen && usable(backend))
      || array(config.backends).find((backend) => backend.id === object(config.defaults).backend && usable(backend))
      || array(config.backends).find((backend) => backend.available);
    if (wanted) select.value = wanted.id;
    else if (!select.options.length) { const option = element("option", "", "No AI service"); option.value = ""; select.append(option); }
  }
  async function setKey(value) {
    if (state.savingKey) return;
    state.savingKey = true;
    $("api-key-save").disabled = true;
    $("form-error").hidden = true;
    try {
      const reply = await api("/api/credentials", { anthropic_api_key: value });
      $("api-key").value = "";
      state.keyNote = ({ no_model: "It cannot use the standard model: enter another model above.",
        offline: "Anthropic could not be reached to check it.", unknown: "It could not be checked." })[reply.check] || "";
      state.config = await api("/api/config");
      fillBackends($("investigation-backend").value);
    } catch (error) {
      $("form-error").textContent = error.message;
      $("form-error").hidden = false;
    } finally { state.savingKey = false; $("api-key-save").disabled = false; updateStartButton(); }
  }
  // Browsers hide a chosen file's path; only the desktop window can supply one (via /api/choose).
  const chooser = () => Boolean(state.config && state.config.chooser === true);
  async function chooseEvidence() {
    if (!chooser() || state.choosing) return;
    state.choosing = true;
    try {
      const reply = await api("/api/choose", {});
      if (reply && typeof reply.path === "string" && reply.path) {
        $("facts-path").value = reply.path;
        $("facts-path").dispatchEvent(new Event("input", { bubbles: true }));
      }
    } catch { /* the path can still be typed */ }
    finally { state.choosing = false; }
  }
  function applyConfig(config) {
    state.config = config;
    state.activeName = config.active_run || null;
    const defaults = object(config.defaults);
    fillBackends(null);
    $("investigation-model").value = "";   // empty means the service's standard model, shown as the placeholder
    if (typeof defaults.minutes === "number" && defaults.minutes >= 1) $("investigation-minutes").value = defaults.minutes;
    updateStartButton();
  }
  // A page sees only a dropped file's name; the desktop window maps it to a path (via /api/dropped).
  const droppable = () => Boolean(state.config && state.config.drop === true);
  const carriesFile = (event) => Boolean(event.dataTransfer) && Array.from(event.dataTransfer.types || []).includes("Files");
  async function dropEvidence(file) {
    const note = $("facts-note");
    let path = "";
    if (droppable()) {
      try { const reply = await api("/api/dropped", { name: file.name }); if (reply && typeof reply.path === "string") path = reply.path; } catch { /* say so below */ }
    }
    note.hidden = Boolean(path);
    if (path) {
      $("facts-path").value = path;
      $("facts-path").dispatchEvent(new Event("input", { bubbles: true }));
    } else note.textContent = droppable() ? "The location of that file could not be read. Choose the file, or type its path."
      : "A browser does not tell this page where a dropped file is. Type its path, or use the desktop app.";
  }
  function openNew() {
    $("form-error").hidden = true;
    $("facts-note").hidden = true;
    $("facts-path").placeholder = droppable() ? "Drop the file here, or choose it" : "/path/to/case_facts.json";
    $("facts-choose").hidden = !chooser();
    $("investigation-advanced").open = false;
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
    if (state.submitting || $("start-investigation").disabled) return;
    if (!$("investigation-form").checkValidity()) $("investigation-advanced").open = true;   // a folded field cannot show its message
    if (!$("investigation-form").reportValidity()) return;
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
      switchTab("summary");   // progress shows in the strip above the tabs
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
      if ($("new-dialog").open) { state.config = config; state.activeName = config.active_run || null; fillBackends($("investigation-backend").value); updateStartButton(); }
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
  document.querySelector(".report-tabs").addEventListener("keydown", (event) => tabKeys(event, ["summary", "timeline", "graph", "findings", "report"], state.tab, switchTab));
  document.querySelector(".detail-tabs").addEventListener("keydown", (event) => tabKeys(event, ["evidence", "proof"], state.detailTab, switchDetail));
  $("finding-search").addEventListener("input", (event) => { state.search = event.target.value.trim(); state.findingLimit = 40; renderFindings(); });
  for (const [id, view] of [["findings-overview", "overview"], ["findings-exact", "exact"]]) $(id).addEventListener("click", () => {
    state.findingView = view; state.findingLimit = 40; renderFindings();
  });
  $("new-investigation").addEventListener("click", openNew);
  $("welcome-new").addEventListener("click", openNew);
  $("refresh-runs").addEventListener("click", refreshAll);
  $("investigation-form").addEventListener("submit", startInvestigation);
  $("facts-choose").addEventListener("click", chooseEvidence);
  // A file dropped anywhere starts a new investigation with it; otherwise the window would open the file.
  let dragDepth = 0;
  const dragging = (on) => { dragDepth = on ? dragDepth : 0; $("facts-drop").classList.toggle("dropping", on); };
  window.addEventListener("dragenter", (event) => { if (carriesFile(event)) { dragDepth += 1; dragging(true); } });
  window.addEventListener("dragleave", (event) => { if (carriesFile(event) && (dragDepth -= 1) <= 0) dragging(false); });
  window.addEventListener("dragover", (event) => { if (carriesFile(event)) { event.preventDefault(); event.dataTransfer.dropEffect = "copy"; } });
  window.addEventListener("drop", (event) => {
    if (!carriesFile(event)) return;
    event.preventDefault();
    dragging(false);
    const file = event.dataTransfer.files && event.dataTransfer.files[0];
    if (!file) return;
    if (!$("new-dialog").open) openNew();
    dropEvidence(file);
  });
  for (const id of ["investigation-model", "investigation-minutes"]) $(id).addEventListener("input", updateStartButton);
  $("investigation-backend").addEventListener("change", () => {
    $("investigation-model").value = "";   // a model name belongs to one service
    updateStartButton();
  });
  $("api-key-save").addEventListener("click", () => { if ($("api-key").value.trim()) setKey($("api-key").value.trim()); });
  $("api-key").addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();   // Enter here saves the key; it does not start the investigation
    if ($("api-key").value.trim()) setKey($("api-key").value.trim());
  });
  $("api-key-remove").addEventListener("click", () => setKey(""));
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

  // Pane edges: drag or arrow keys resize; double-click or Enter restores the default.
  const PANES = [
    { handle: "resize-side", pane: "sidebar", name: "--side-w", base: 208, min: 160, max: 440, sign: 1 },
    { handle: "resize-insp", pane: "inspector", name: "--insp-w", base: 380, min: 280, max: 820, sign: -1 },
    { handle: "resize-report", pane: "report-form", name: "--report-w", base: 264, min: 220, max: 600, sign: 1 },
  ];
  function resizablePanes() {
    const shell = $("shell");
    let saved = {}, queued = 0;
    try { saved = object(JSON.parse(localStorage.getItem("conan.panes") || "{}")); } catch { saved = {}; }
    const keep = () => { try { localStorage.setItem("conan.panes", JSON.stringify(saved)); } catch { /* the sizes last for this window only */ } };
    const refit = () => { if (!queued) queued = requestAnimationFrame(() => { queued = 0; window.dispatchEvent(new Event("resize")); }); };
    for (const pane of PANES) {
      const handle = $(pane.handle);
      const shown = () => Math.round($(pane.pane).getBoundingClientRect().width) || pane.base;
      const set = (width) => {
        const value = Math.round(Math.max(pane.min, Math.min(pane.max, width)));
        shell.style.setProperty(pane.name, value + "px");
        handle.setAttribute("aria-valuenow", String(value));
        refit();
        return value;
      };
      const store = (value) => { saved[pane.name] = value; keep(); };
      const reset = () => { shell.style.removeProperty(pane.name); handle.setAttribute("aria-valuenow", String(pane.base)); delete saved[pane.name]; keep(); refit(); };
      handle.setAttribute("aria-valuemin", String(pane.min)); handle.setAttribute("aria-valuemax", String(pane.max));
      handle.setAttribute("aria-valuenow", String(pane.base));
      if (Number.isFinite(saved[pane.name])) set(saved[pane.name]);
      handle.addEventListener("pointerdown", (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        const from = event.clientX, start = shown();
        let value = start;
        try { handle.setPointerCapture(event.pointerId); } catch { /* the drag still works while the pointer stays on the handle */ }
        handle.classList.add("dragging"); document.body.classList.add("resizing");
        const move = (step) => { value = set(start + pane.sign * (step.clientX - from)); };
        const done = () => {
          handle.removeEventListener("pointermove", move); handle.removeEventListener("pointerup", done); handle.removeEventListener("pointercancel", done);
          handle.classList.remove("dragging"); document.body.classList.remove("resizing");
          if (value !== start) store(value);
        };
        handle.addEventListener("pointermove", move); handle.addEventListener("pointerup", done); handle.addEventListener("pointercancel", done);
      });
      handle.addEventListener("dblclick", reset);
      handle.addEventListener("keydown", (event) => {
        const step = (event.shiftKey ? 64 : 16) * pane.sign;
        if (event.key === "ArrowRight") store(set(shown() + step));
        else if (event.key === "ArrowLeft") store(set(shown() - step));
        else if (event.key === "Home") store(set(pane.min));
        else if (event.key === "End") store(set(pane.max));
        else if (event.key === "Enter") reset();
        else return;
        event.preventDefault();
      });
    }
  }

  CONAN.app = { element, badge, code, present, openFinding, recordCard, inspect, switchTab };

  async function init() {
    resizablePanes();
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
