/* CONAN-F report builder: choose what goes into an examiner's report, preview it, print it.
   The server writes the report; this file only chooses its contents and shows the result. */
(() => {
  "use strict";
  const CONAN = (window.CONAN = window.CONAN || {});
  const $ = (id) => document.getElementById(id);
  // key, label, note, included by default
  const SECTIONS = [
    ["needs", "Appendix: refused proposals", "What the checker did not accept, and why", false],
    ["judgments", "Analysis and conclusions", "Investigator conclusions with supporting finding references", true],
    ["workflow", "Question-by-question plan", "Only in a report of all findings", false],
    ["evidence", "Appendix: full evidence records", "Every cited record with its complete provenance", false],
    ["proofs", "Appendix: Lean proofs", "The claim and Lean source of each certificate", false],
    ["activity", "Appendix: audit and coverage", "Recorded tool calls and coverage summaries", false],
  ];
  const COVER = ["reference", "report_id", "report_version", "examiner", "organisation", "address", "report_date", "requested_by", "request_date", "authority", "purpose", "received", "submitted_by", "collection_method", "additional_items", "method_notes", "disposition", "impact", "root_cause", "response", "recommendations"];
  const LONG_FIELDS = new Set(["purpose", "additional_items", "method_notes", "disposition", "impact", "root_cause", "response", "recommendations"]);
  const limit = key => LONG_FIELDS.has(key) ? 600 : 200;
  const today = () => { const now = new Date(); return now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0") + "-" + String(now.getDate()).padStart(2, "0"); };
  const PREVIEW_LIMIT = 6 * 1024 * 1024;   // characters; larger reports are exported, not previewed
  const state = {
    name: null, revision: null, ids: [], known: new Set(), marked: new Set(), scope: "all", length: "short", sections: new Set(), cover: {}, empty: new Set(),
    shadow: null, stale: true, active: false, request: 0, timer: 0, built: false,
  };

  // Remembered per case in this browser only: a convenience, never the record of anything.
  const storageKey = () => "conan-f.report." + state.name;
  function load() {
    state.marked = new Set(); state.scope = "all"; state.length = "short"; state.cover = { report_date: today(), report_version: "1" };   // a report is dated the day it is made
    state.sections = new Set(SECTIONS.filter((section) => section[3]).map((section) => section[0]));
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey()) || "null");
      if (!saved || typeof saved !== "object") return;
      if (Array.isArray(saved.marked)) state.marked = new Set(saved.marked.filter((id) => typeof id === "string"));
      if (saved.scope === "marked") state.scope = "marked";
      if (saved.length === "full") state.length = "full";
      if (Array.isArray(saved.sections)) state.sections = new Set(saved.sections.filter((key) => SECTIONS.some((section) => section[0] === key)));
      for (const key of COVER) if (key !== "report_date" && saved.cover && typeof saved.cover[key] === "string") state.cover[key] = saved.cover[key].slice(0, limit(key));
    } catch (_) { /* private windows and blocked storage: carry on without it */ }
  }
  function save() {
    try {
      localStorage.setItem(storageKey(), JSON.stringify({ marked: [...state.marked], scope: state.scope, length: state.length, sections: [...state.sections], cover: state.cover }));
    } catch (_) { /* see load() */ }
  }

  const marked = () => state.ids.filter((id) => state.marked.has(id));   // in the case's own order
  const chosen = () => (state.scope === "marked" ? marked() : state.ids);
  function query(download) {
    const params = new URLSearchParams({ name: state.name, format: "html" });
    if (download) params.set("download", "1");
    // The short report is the summary, timeline and evidence: one or two printed pages.
    if (state.length === "short") params.set("brief", "1");
    // Do not add empty optional sections to the examiner's report.
    const included = (section) => state.length === "full" && !state.empty.has(section[0]) && state.sections.has(section[0]);
    params.set("sections", SECTIONS.filter((section) => included(section) && !(section[0] === "workflow" && state.scope === "marked")).map((section) => section[0]).join(","));
    if (state.scope === "marked") params.set("ids", marked().join(","));
    for (const key of COVER) if (state.cover[key]) params.set(key, state.cover[key]);
    return "/api/report?" + params;
  }

  function message(title, detail) {
    const box = $("report-empty");
    box.replaceChildren(Object.assign(document.createElement("h3"), { textContent: title }), Object.assign(document.createElement("p"), { textContent: detail }));
    box.hidden = false;
    $("report-host").hidden = true;
    state.built = false;
    controls();
  }
  function controls() {
    const count = marked().length, none = state.scope === "marked" && !count;
    $("report-count-all").textContent = "(" + state.ids.length + ")";
    $("report-count-marked").textContent = "(" + count + ")";
    $("report-scope-marked").disabled = !count;
    $("report-print").disabled = !state.built || state.stale;
    const link = $("report-export");
    if (none || !state.name) { link.removeAttribute("href"); link.removeAttribute("download"); link.setAttribute("aria-disabled", "true"); }
    // The file name makes the desktop window save the report instead of opening it in place of the app.
    else { link.href = query(true); link.download = String(state.name).replace(/\//g, "-") + ".html"; link.removeAttribute("aria-disabled"); }
    const workflow = document.querySelector('#report-sections input[value="workflow"]');
    if (workflow) workflow.disabled = state.scope === "marked";
    const badge = $("count-report");
    if (badge) badge.textContent = count ? String(count) : "";
  }
  function form() {
    $("report-method_notes").hidden = state.length === "short";
    $("report-method-label").hidden = state.length === "short";
    document.querySelectorAll('#report-form input[name="report-scope"]').forEach((input) => { input.checked = input.value === state.scope; });
    document.querySelectorAll('#report-form input[name="report-length"]').forEach((input) => { input.checked = input.value === state.length; });
    $("report-extras").hidden = state.length !== "full";   // the parts that add pages belong to the full report
    // A part of the report with nothing in it for this case is not offered.
    document.querySelectorAll("#report-sections input").forEach((input) => { input.checked = state.sections.has(input.value); input.closest("label").hidden = state.empty.has(input.value); });
    for (const key of COVER) $("report-" + key).value = state.cover[key] || "";
  }

  // The report arrives as a finished page. Show it inside a shadow root so its styles and
  // the workbench's cannot touch each other, and so it prints as part of this page.
  function mount(text) {
    const parsed = new DOMParser().parseFromString(text, "text/html");
    parsed.querySelectorAll("script, iframe, object, embed, link, meta, base, form").forEach((node) => node.remove());
    const host = $("report-host");
    if (!state.shadow) {
      state.shadow = host.attachShadow({ mode: "open" });
      state.shadow.addEventListener("click", (event) => {
        const link = event.target.closest ? event.target.closest("a") : null;
        if (!link) return;
        event.preventDefault();   // the report has only in-page links
        const href = link.getAttribute("href") || "";
        const target = href.startsWith("#") ? state.shadow.getElementById(decodeURIComponent(href.slice(1))) : null;
        if (target) target.scrollIntoView({ block: "start" });
      });
    }
    const style = document.createElement("style"), page = document.createElement("div");
    // On screen the workbench already supplies the desk around the page. A long report holds hundreds of
    // findings; laying out only the ones near the view keeps the tab quick. Print still lays out all of them.
    style.textContent = [...parsed.querySelectorAll("style")].map((sheet) => sheet.textContent).join("\n")
      + "\n@media screen { .report { background: transparent; } main { margin: 0; max-width: none; border: 0; border-radius: 0; }"
      + " article { content-visibility: auto; contain-intrinsic-size: auto 1500px; } }";
    page.className = "report";
    page.append(...[...parsed.body.childNodes].map((node) => document.adoptNode(node)));
    state.shadow.replaceChildren(style, page);
    host.hidden = false;
    $("report-empty").hidden = true;
    $("report-preview").scrollTop = 0;
  }

  async function refresh() {
    clearTimeout(state.timer);
    if (!state.active || !state.name) return;
    const request = ++state.request, count = chosen().length;
    if (!state.ids.length) return message("No certified findings yet", "A report can be built once this case has findings the checker accepted.");
    if (!count) return message("No findings are marked", "Tick findings in the Findings table, or use Add to report in the inspector. You can also report all certified findings.");
    $("report-status").textContent = "Building the report…";
    try {
      const response = await fetch(query(false), { cache: "no-store" });
      const text = await response.text();
      if (request !== state.request) return;
      if (!response.ok) {
        let reason = "The server could not build this report.";
        try { reason = JSON.parse(text).error || reason; } catch (_) { /* keep the general reason */ }
        throw new Error(reason);
      }
      const size = text.length >= 1048576 ? (text.length / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(text.length / 1024)) + " KB";
      const summary = count + (count === 1 ? " finding" : " findings") + " · " + size;
      state.stale = false;
      if (text.length > PREVIEW_LIMIT) {
        message("Too large to preview", "This report is " + size + ". Export it as HTML and open the file, or leave out an appendix or mark fewer findings to preview and print it here.");
        $("report-status").textContent = summary + " · preview skipped";
        return;
      }
      mount(text);
      state.built = true;
      $("report-status").textContent = summary;
      controls();
    } catch (error) {
      if (request !== state.request) return;
      message("The report could not be built", error.message);
      $("report-status").textContent = "";
    }
  }
  function changed(delay) {
    state.stale = true;
    save();
    controls();
    clearTimeout(state.timer);
    if (state.active) state.timer = setTimeout(refresh, delay || 0);
  }

  function print() {
    // In the desktop window the system print panel is reached through the window's own handler.
    const native = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.browserDelegate;
    if (native && typeof native.postMessage === "function") native.postMessage("print"); else window.print();
  }

  function wire() {
    const sections = $("report-sections");
    SECTIONS.forEach(([key, label, note]) => {
      const row = document.createElement("label"), input = document.createElement("input"), text = document.createElement("span");
      input.type = "checkbox"; input.value = key;
      text.append(label, Object.assign(document.createElement("small"), { textContent: note }));
      row.append(input, text);
      sections.append(row);
    });
    $("report-form").addEventListener("submit", (event) => event.preventDefault());
    $("report-form").addEventListener("change", (event) => {
      const input = event.target;
      if (input.name === "report-scope" && input.checked) state.scope = input.value;
      else if (input.name === "report-length" && input.checked) { state.length = input.value; form(); }
      else if (input.closest("#report-sections")) { if (input.checked) state.sections.add(input.value); else state.sections.delete(input.value); }
      else return;
      changed();
    });
    for (const key of COVER) $("report-" + key).addEventListener("input", (event) => { state.cover[key] = event.target.value.trim().slice(0, limit(key)); changed(350); });
    $("report-print").addEventListener("click", print);
    $("report-export").addEventListener("click", (event) => { if (!event.currentTarget.hasAttribute("href")) event.preventDefault(); });
  }

  CONAN.report = {
    /** A case was opened or re-read: `ids` are its certified findings, in order; `empty` names report parts it has nothing for. */
    open(name, ids, revision = null, empty = []) {
      const list = (ids || []).map(String), same = name === state.name && revision === state.revision
        && list.length === state.ids.length && list.every((id, index) => id === state.ids[index]);
      state.empty = new Set(empty);
      if (name !== state.name) { state.name = name; load(); state.built = false; state.stale = true; if (state.shadow) state.shadow.replaceChildren(); }
      state.ids = list; state.known = new Set(list); state.revision = revision;
      if (state.scope === "marked" && !marked().length) state.scope = "all";
      if (!same) { state.stale = true; state.request += 1; }  // discard any preview of the previous contents
      form();
      controls();
      if (state.active && state.stale) changed();
    },
    activate() { state.active = true; if (state.stale || !state.built) refresh(); },
    deactivate() { state.active = false; clearTimeout(state.timer); },
    has: (id) => state.marked.has(String(id)),
    count: () => marked().length,
    toggle(id, on) {
      const key = String(id), before = marked().length;
      if (on === undefined ? !state.marked.has(key) : on) state.marked.add(key); else state.marked.delete(key);
      const after = marked().length;
      // Marking the first finding means "report these"; unmarking the last returns to all.
      if (!before && after) state.scope = "marked"; else if (before && !after) state.scope = "all";
      form();
      changed();
      document.dispatchEvent(new CustomEvent("conan:marks"));
    },
  };
  wire();
})();
