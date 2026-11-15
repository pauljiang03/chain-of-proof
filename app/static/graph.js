"use strict";

// Proof graph. Read left to right:
//   disk image -> source artifact -> extracted record -> finding (checked by Lean) -> interpretation (not certified).
// Buildless and dependency-free. Record contents are only ever inserted as text.
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const CONAN = (window.CONAN = window.CONAN || {});
  const $ = (id) => document.getElementById(id);
  const array = (value) => Array.isArray(value) ? value : [];
  const object = (value) => value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const text = (value) => value === undefined || value === null ? "" : String(value);
  const clip = (value, chars) => { const s = text(value).replace(/\s+/g, " "); return s.length > chars ? s.slice(0, Math.max(1, chars - 1)) + "…" : s; };
  const mean = (values) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;

  const COLUMNS = [
    { key: "exhibit", title: "DISK IMAGE", width: 112, height: 38, pitch: 50 },
    { key: "artifact", title: "SOURCE ARTIFACT", width: 196, height: 26, pitch: 32 },
    { key: "record", title: "EXTRACTED RECORD", width: 276, height: 40, pitch: 48 },
    { key: "finding", title: "FINDING · CHECKED BY LEAN", width: 304, height: 40, pitch: 54 },
    { key: "judgment", title: "INTERPRETATION · NOT CERTIFIED", width: 264, height: 40, pitch: 52 },
  ];
  const GAP = 66, PAGE = 40, MAX_RECORDS = 6, MIN_FIT = 0.72;
  const COLUMN = {};
  COLUMNS.forEach((column) => { COLUMN[column.key] = column; });

  const state = {
    key: null, signature: null, run: null, events: [], items: [],
    scope: "", query: "", focus: null, page: 0, step: 0, steps: 0, total: 0, browsing: true,
    selected: null, hover: null, view: { x: 24, y: 56, k: 1 }, fitted: false, locked: false,
    model: { nodes: new Map(), edges: [], shown: [] }, timer: null, drag: null, columns: [], width: 0, examined: new Set(), rowKeys: new WeakMap(),
  };

  // A fact ID is not enough to merge copied evidence. Share only identical records,
  // including their provenance, irrespective of JSON object key order.
  function stableJSON(value) {
    if (Array.isArray(value)) return "[" + value.map(stableJSON).join(",") + "]";
    if (value && typeof value === "object") return "{" + Object.keys(value).sort().map((key) => JSON.stringify(key) + ":" + stableJSON(value[key])).join(",") + "}";
    return JSON.stringify(value);
  }
  function recordKey(row) {
    if (!state.rowKeys.has(row)) state.rowKeys.set(row, stableJSON(row));
    return state.rowKeys.get(row);
  }
  function imageKey(provenance) {
    return stableJSON(["image", "image_sha256", "exhibit", "case_id", "snapshot_id", "snapshot", "view", "generation"]
      .map((key) => provenance[key] === undefined ? null : provenance[key]));
  }

  function svg(tag, attributes, content) {
    const node = document.createElementNS(NS, tag);
    for (const [name, value] of Object.entries(attributes || {})) node.setAttribute(name, value);
    if (content !== undefined) node.textContent = content;
    return node;
  }
  // Some records carry the time the image was examined, not a time from the device.
  // Those must never read as an event time in the graph.
  const EXAMINED = /^when the image was examined/i;
  const timeMeaning = (row) => { const provenance = object(row.prov); return text(provenance.time_meaning || provenance.timestamp_semantics || ""); };
  function when(row) {
    if (!Number.isSafeInteger(row.t) || row.t <= 0) return "";
    if (EXAMINED.test(timeMeaning(row)) || (!timeMeaning(row) && state.examined.has(row.t))) return "at examination";
    const time = new Date(row.t / 1000);
    return Number.isNaN(time.getTime()) ? "" : time.toISOString().slice(0, 19).replace("T", " ") + "Z";
  }
  // Group records by the file or structure they were read from: drop the trailing locator.
  function artifactOf(row) {
    const provenance = object(row.prov);
    const raw = typeof provenance.artifact === "string" && provenance.artifact.trim() ? provenance.artifact.trim() : "Source not recorded";
    const key = raw.replace(/,\s*file table record\b.*$/i, "")
      .replace(/\s+(?:line|record|entry|row|offset|stream|key|value|at sector|sector|cluster)\b.*$/i, "")
      .replace(/\s+of\s+[\\/].*$/i, "").trim() || raw;
    const parts = key.split(/[\\/]/).filter(Boolean);
    return { key, label: /[\\/]/.test(key) && parts.length ? parts[parts.length - 1] : key };
  }

  // ---- data ---------------------------------------------------------------
  function prepare() {
    const run = object(state.run), index = new Map(), ambiguous = new Set(), order = new Map();
    const focused = state.items.find((item) => item.key === state.focus);
    state.rowKeys = new WeakMap();
    array(run.findings).forEach((finding) => array(object(finding).cited_facts).forEach((row) => {
      if (row && typeof row === "object") {
        if (!index.has(row.id)) index.set(row.id, row);
        else if (recordKey(index.get(row.id)) !== recordKey(row)) ambiguous.add(row.id);
      }
    }));
    ambiguous.forEach((id) => index.delete(id));  // a refusal must not borrow an arbitrary conflicting copy
    array(state.events).forEach((event) => {
      const sequence = Number(object(event).sequence);
      if (event && event.finding_id && Number.isFinite(sequence) && !order.has(event.finding_id)) order.set(event.finding_id, sequence);
    });
    const items = [];
    array(run.findings).forEach((finding, at) => {
      if (object(finding).status === "verified") items.push({ key: "F:f" + (at + 1), id: text(finding.finding_id), refused: false, data: finding, at });
    });
    array(run.rejections).forEach((rejection, at) => items.push({ key: "F:r" + (at + 1), id: text(object(rejection).finding_id), refused: true, data: object(rejection), at: 1e6 + at }));
    // Replay order: the audit sequence where it is recorded; otherwise the order in the bundle.
    if (items.some((item) => order.has(item.id))) {
      items.forEach((item) => { item.sequence = order.has(item.id) ? order.get(item.id) : item.at - 1e9; });
      items.sort((left, right) => left.sequence - right.sequence);
    }
    items.forEach((item) => {
      item.rows = item.refused ? refusedRows(item.data, index) : uniqueRows(array(item.data.cited_facts));
      const data = item.data;
      item.hay = [item.id, data.question, data.english, data.reason, array(data.rules).join(" "),
        item.rows.map((row) => [row.id, row.kind, row.obj_text, row.aux_text, object(row.prov).artifact, object(row.prov).exhibit].join(" ")).join(" ")]
        .join(" ").toLowerCase();
    });
    state.items = items;
    if (focused) {
      const matches = items.filter((item) => item.id === focused.id && item.refused === focused.refused);
      const retained = matches.length === 1 ? matches[0] : matches.find((item) => item.key === focused.key);
      state.focus = retained ? retained.key : null;
    }
    // Times this case itself declares to be examination times.
    state.examined = new Set();
    for (const item of items) for (const row of item.rows) if (EXAMINED.test(timeMeaning(row))) state.examined.add(row.t);
  }
  function uniqueRows(rows) {
    const seen = new Set();
    return rows.filter((row) => row && typeof row === "object" && !seen.has(recordKey(row)) && seen.add(recordKey(row)));
  }
  // A refused proposal has no certificate. Show the records it named, from the checker's diagnostics.
  function refusedRows(rejection, index) {
    const rows = new Map();
    const add = (id, fallback) => { if (id !== undefined && id !== null && !rows.has(id)) rows.set(id, index.get(id) || fallback); };
    array(object(rejection.proof_gap).requirements).forEach((requirement) => {
      array(object(object(requirement).observed).records).forEach((record) => add(object(record).id, {
        id: record.id, kind: record.kind, t: record.t_us, obj_text: object(record.obj).text, aux_text: object(record.aux).text, prov: {} }));
      array(object(requirement).fact_ids).forEach((id) => add(id, { id, prov: {} }));
    });
    array(rejection.parts).forEach((part) => array(object(part).bricks).forEach((brick) => {
      const match = /\bis\s+(\d+)\s+\((\w+)\)/.exec(text(brick));
      if (match) add(Number(match[1]), { id: Number(match[1]), kind: match[2], prov: {} });
    }));
    return [...rows.values()];
  }
  function selection() {
    if (state.focus) {
      const base = state.items.find((item) => item.key === state.focus);
      if (base) {
        const ids = new Set(base.rows.map(recordKey));
        return [base, ...state.items.filter((item) => item !== base && item.rows.some((row) => ids.has(recordKey(row))))];
      }
    }
    let list = state.items;
    if (state.scope) list = list.filter((item) => text(item.data.question) === state.scope);
    if (state.query) list = list.filter((item) => item.hay.includes(state.query));
    return list;
  }

  // ---- model and layout ---------------------------------------------------
  function build() {
    const all = selection();
    state.total = all.length;
    state.page = Math.max(0, Math.min(state.page, Math.ceil(all.length / PAGE) - 1));
    const shown = all.slice(state.page * PAGE, state.page * PAGE + PAGE);
    const nodes = new Map(), edges = [], edgeIndex = new Map();
    const node = (id, column, extra) => {
      let item = nodes.get(id);
      if (!item) {
        item = { id, column, ins: new Set(), outs: new Set(), birth: Infinity, cls: "", x: 0, w: COLUMN[column].width, h: COLUMN[column].height, y: 0, ...extra };
        nodes.set(id, item);
      }
      return item;
    };
    const edge = (from, to, cls, birth) => {
      const key = JSON.stringify([from.id, to.id]), existing = edgeIndex.get(key);
      if (existing) { existing.birth = Math.min(existing.birth, birth); return; }
      from.outs.add(to.id); to.ins.add(from.id);
      const created = { from, to, cls, birth };
      edgeIndex.set(key, created); edges.push(created);
    };
    const shared = new Map();
    shown.forEach((item) => item.rows.forEach((row) => shared.set(recordKey(row), (shared.get(recordKey(row)) || 0) + 1)));

    shown.forEach((item, position) => {
      const birth = position + 1;
      const finding = node(item.key, "finding", { item, owned: [], cls: item.refused ? "refused" : item.data.strength === "heuristic" ? "heuristic" : "strong" });
      finding.birth = birth;
      // Keep records that several findings rest on visible; fold the rest of a long list.
      const ranked = item.rows.map((row, at) => [row, at]).sort((a, b) => (shared.get(recordKey(b[0])) - shared.get(recordKey(a[0]))) || a[1] - b[1]).map((pair) => pair[0]);
      const visible = ranked.length > MAX_RECORDS + 1 ? ranked.slice(0, MAX_RECORDS) : ranked;
      visible.forEach((row) => {
        const key = "R:" + recordKey(row), fresh = !nodes.has(key);
        const record = node(key, "record", { row });
        if (fresh) finding.owned.push(record);
        record.birth = Math.min(record.birth, birth);
        edge(record, finding, item.refused ? "refused" : "", birth);
        const provenance = object(row.prov);
        if (!provenance.artifact && !provenance.exhibit) return;
        const source = artifactOf(row), exhibitName = text(provenance.exhibit) || "Exhibit not recorded";
        const scope = imageKey(provenance);
        const artifact = node("A:" + stableJSON([scope, source.key]), "artifact", { label: source.label, path: source.key, exhibit: exhibitName, rows: [] });
        if (!artifact.rows.includes(row)) artifact.rows.push(row);
        artifact.birth = Math.min(artifact.birth, birth);
        edge(artifact, record, "", birth);
        const exhibit = node("E:" + scope, "exhibit", { label: exhibitName, image: text(provenance.image), artifacts: new Set() });
        exhibit.artifacts.add(artifact.id);
        exhibit.birth = Math.min(exhibit.birth, birth);
        edge(exhibit, artifact, "", birth);
      });
      if (visible.length < ranked.length) {
        const more = node("M:" + item.key, "record", { item, count: ranked.length - visible.length, cls: "more" });
        more.birth = birth;
        finding.owned.push(more);
        edge(more, finding, "more", birth);
      }
    });
    const byId = new Map();
    state.items.forEach((item) => byId.set(item.id, byId.has(item.id) ? null : item));
    array(object(state.run).conclusions).forEach((conclusion, at) => {
      // A label-only reference cannot select among duplicate claim occurrences.
      const cited = array(object(conclusion).finding_ids).map((id) => byId.get(text(id)))
        .filter((item) => item && !item.refused).map((item) => nodes.get(item.key)).filter(Boolean);
      if (!cited.length) return;
      const judgment = node("J:j" + (at + 1), "judgment", { conclusion });
      judgment.birth = Math.max(...cited.map((finding) => finding.birth));
      cited.forEach((finding) => edge(finding, judgment, "judgment", judgment.birth));
    });

    // Each finding is a block; the records it introduced stack beside it.
    let y = 0;
    shown.forEach((item) => {
      const finding = nodes.get(item.key), pitch = COLUMN.record.pitch;
      const block = Math.max(COLUMN.finding.pitch, finding.owned.length * pitch);
      finding.owned.forEach((record, at) => { record.y = y + (block - finding.owned.length * pitch) / 2 + at * pitch + pitch / 2; });
      finding.y = y + block / 2;
      y += block + 8;
    });
    const place = (column, towards) => {
      const list = [...nodes.values()].filter((item) => item.column === column);
      list.forEach((item) => { item.wish = mean([...item[towards]].map((id) => nodes.get(id).y)); });
      list.sort((a, b) => a.wish - b.wish);
      let floor = -Infinity;
      list.forEach((item) => { item.y = Math.max(item.wish, floor); floor = item.y + COLUMN[column].pitch; });
    };
    place("artifact", "outs");
    place("exhibit", "outs");
    place("judgment", "ins");
    // Columns with nothing in them take no room.
    const filled = new Set(["record", "finding"]);
    nodes.forEach((item) => filled.add(item.column));
    let left = 0;
    state.columns = COLUMNS.filter((column) => filled.has(column.key)).map((column) => { const placed = { ...column, x: left }; left += column.width + GAP; return placed; });
    state.width = left - GAP;
    const xs = {};
    state.columns.forEach((column) => { xs[column.key] = column.x; });
    nodes.forEach((item) => { item.x = xs[item.column]; });

    // The replay runs through every finding in the selection, not only the page on screen.
    state.steps = all.length;
    // Browsing a page reveals that page, not the end of the entire investigation.
    // Explicit replay positions always identify the page containing that position.
    state.step = state.browsing ? Math.min(state.steps, (state.page + 1) * PAGE)
      : Math.max(0, Math.min(state.steps, state.step));
    state.model = { nodes, edges, shown };
  }

  // ---- drawing ------------------------------------------------------------
  function drawNode(item) {
    const group = svg("g", { class: "node " + item.column + (item.cls ? " " + item.cls : ""), transform: `translate(${item.x},${item.y - item.h / 2})` });
    const box = () => group.append(svg("rect", { class: "box", width: item.w, height: item.h, rx: 4 }));
    const tip = (value) => group.append(svg("title", {}, value));
    if (item.column === "exhibit") {
      box();
      group.append(svg("text", { class: "id", x: 10, y: 16 }, clip(item.label, 13)), svg("text", { class: "sub", x: 10, y: 30 }, clip(item.image || "image not recorded", 17)));
      tip("Exhibit " + item.label + (item.image ? " · " + item.image : ""));
    } else if (item.column === "artifact") {
      box();
      group.append(svg("text", { x: 9, y: 17 }, clip(item.label, 30)));
      tip(item.path);
    } else if (item.cls === "more") {
      box();
      group.append(svg("text", { class: "sub", x: 9, y: 16 }, "+ " + item.count + " more cited records"));
      tip("Select to list every record this finding cites");
    } else if (item.column === "record") {
      box();
      const row = item.row;
      group.append(svg("text", { class: "id", x: 8, y: 16 }, clip(CONAN.evidence ? CONAN.evidence.entity(row).title : (row.obj_text || row.kind), 37)),
        svg("text", { class: "sub", x: 8, y: 31 }, clip("#" + text(row.id) + " · " + (CONAN.evidence ? (CONAN.evidence.types[row.kind] || ["", row.kind])[1] : row.kind) + " · " + when(row), 48)));
      tip([row.kind, row.obj_text, row.aux_text && row.aux_text !== "(none)" ? row.aux_text : "", object(row.prov).artifact].filter(Boolean).join(" · "));
    } else if (item.column === "finding") {
      const data = item.item.data, refused = item.item.refused;
      box();
      group.append(svg("rect", { class: "stripe", width: 4, height: item.h, rx: 2 }),
        svg("text", { class: "id", x: 12, y: 16 }, clip(item.item.id, 16)),
        svg("text", { class: "tag", x: item.w - 9, y: 16, "text-anchor": "end" }, refused ? "REFUSED" : item.cls === "heuristic" ? "CERTIFIED · HEURISTIC" : "CERTIFIED"),
        svg("text", { class: "sub", x: 12, y: 31 }, clip(refused ? (object(data.proof_gap).summary || data.reason || "Refused by the checker") : (CONAN.evidence ? CONAN.evidence.title(data) : data.english), 51)));
      tip(refused ? text(data.reason) : text(data.english));
    } else {
      const conclusion = object(item.conclusion);
      box();
      group.append(svg("text", { class: "id", x: 10, y: 16 }, clip(conclusion.conclusion_id, 14)),
        svg("text", { class: "tag", x: item.w - 9, y: 16, "text-anchor": "end" }, "NOT CERTIFIED"),
        svg("text", { class: "sub", x: 10, y: 31 }, clip(conclusion.text, 44)));
      tip(text(conclusion.text));
    }
    group.addEventListener("click", (event) => { event.stopPropagation(); select(item.id); });
    group.addEventListener("dblclick", (event) => { event.stopPropagation(); if (item.column === "finding") focus(item.item.key); });
    group.addEventListener("pointerenter", () => { state.hover = item.id; highlight(); });
    group.addEventListener("pointerleave", () => { state.hover = null; highlight(); });
    return group;
  }
  function draw() {
    const root = $("graph"), model = state.model;
    root.replaceChildren();
    const viewport = svg("g", { class: "viewport" });
    state.columns.forEach((column) => viewport.append(
      svg("text", { class: "column-title", x: column.x, y: -24 }, column.title),
      svg("line", { class: "column-rule", x1: column.x, x2: column.x + column.width, y1: -16, y2: -16 })));
    const edgeLayer = svg("g"), nodeLayer = svg("g");
    model.edges.forEach((edge) => {
      const x1 = edge.from.x + edge.from.w, x2 = edge.to.x, middle = (x1 + x2) / 2;
      edge.el = svg("path", { class: "edge" + (edge.cls ? " " + edge.cls : ""), d: `M${x1},${edge.from.y} C${middle},${edge.from.y} ${middle},${edge.to.y} ${x2},${edge.to.y}` });
      edgeLayer.append(edge.el);
    });
    model.nodes.forEach((item) => { item.el = drawNode(item); nodeLayer.append(item.el); });
    viewport.append(edgeLayer, nodeLayer);
    root.append(viewport);
    state.viewport = viewport;
    const none = !model.shown.length;
    $("graph-empty").hidden = !none;
    if (none) $("graph-empty").textContent = state.items.length
      ? "No finding matches this scope or filter."
      : "No checked claims yet. Findings appear here as the checker accepts or refuses them.";
    applyView(); applyStep(); highlight(); controls();
  }
  function applyView() {
    if (state.viewport) state.viewport.setAttribute("transform", `translate(${state.view.x},${state.view.y}) scale(${state.view.k})`);
  }
  // Motion. A spring always starts from the value on screen and can be interrupted at any frame.
  // Parameters follow Apple's damping ratio and response; 1.0 / 0.4 is critically damped.
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const motion = { frame: 0, velocity: { x: 0, y: 0, k: 0 } };
  function interrupt() { if (motion.frame) { cancelAnimationFrame(motion.frame); motion.frame = 0; } }
  function settle(target, velocity, damping = 1, response = 0.4) {
    interrupt();
    if (reduceMotion.matches) { state.view = { ...target }; applyView(); return; }
    motion.velocity = { x: (velocity && velocity.x) || 0, y: (velocity && velocity.y) || 0, k: 0 };
    const stiffness = (2 * Math.PI / response) ** 2, friction = 4 * Math.PI * damping / response;
    let last = performance.now();
    const step = (now) => {
      const dt = Math.min(0.032, (now - last) / 1000);
      last = now;
      let moving = false;
      for (const axis of ["x", "y", "k"]) {   // independent springs per axis
        const offset = state.view[axis] - target[axis], rest = axis === "k" ? 0.0005 : 0.25;
        motion.velocity[axis] += (-stiffness * offset - friction * motion.velocity[axis]) * dt;
        state.view[axis] += motion.velocity[axis] * dt;
        if (Math.abs(offset) > rest || Math.abs(motion.velocity[axis]) > rest * 12) moving = true;
      }
      if (!moving) { state.view = { ...target }; motion.frame = 0; applyView(); return; }
      applyView();
      motion.frame = requestAnimationFrame(step);
    };
    motion.frame = requestAnimationFrame(step);
  }
  // Where a flick would come to rest (exponential decay, as scrolling does).
  const project = (velocity, rate = 0.998) => (velocity / 1000) * rate / (1 - rate);
  // Past an edge the canvas follows less and less instead of stopping dead.
  const rubberband = (overshoot, dimension, constant = 0.55) => (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));
  const banded = (value, min, max, dimension) => value > max ? max + rubberband(value - max, dimension) : value < min ? min - rubberband(min - value, dimension) : value;
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  function limits(k = state.view.k) {
    const host = $("graph-host").getBoundingClientRect(), box = bounds();
    if (!box || !host.width) return null;
    const margin = 160;
    return { width: host.width, height: host.height, minX: margin - state.width * k, maxX: host.width - margin,
      minY: margin - box.bottom * k, maxY: host.height - margin - box.top * k };
  }
  // How far the replay has come on the page being shown.
  const local = () => Math.max(0, Math.min(state.model ? state.model.shown.length : 0, state.step - state.page * PAGE));
  function bounds(whole) {
    const ys = [...state.model.nodes.values()].filter((item) => whole || item.birth <= Math.max(local(), 1));
    if (!ys.length) return null;
    return { top: Math.min(...ys.map((item) => item.y - item.h / 2)) - 34, bottom: Math.max(...ys.map((item) => item.y + item.h / 2)) };
  }
  function insets() {   // the floating toolbar and legend cover part of the canvas
    const host = $("graph-host").getBoundingClientRect();
    const bar = document.querySelector(".graph-toolbar").getBoundingClientRect(), legend = document.querySelector(".graph-legend").getBoundingClientRect();
    return { top: Math.max(0, bar.bottom - host.top) + 12, bottom: Math.max(0, host.bottom - legend.top) + 10 };
  }
  function fit(animate, whole) {
    const host = $("graph-host").getBoundingClientRect(), box = bounds(whole);
    if (!host.width || !host.height || !box) return false;
    // Never start smaller than readable: a wide graph begins at its evidence side and pans.
    const k = Math.max(MIN_FIT, Math.min(1, (host.width - 40) / state.width)), inset = insets();
    const height = (box.bottom - box.top) * k, room = host.height - inset.top - inset.bottom;
    const target = { k, x: Math.max(20, (host.width - state.width * k) / 2), y: inset.top + (height < room ? (room - height) / 2 : 4) - box.top * k };
    if (animate === true) settle(target);
    else { interrupt(); state.view = target; applyView(); }
    return true;
  }
  function zoom(factor, cx, cy, animate) {
    const host = $("graph-host").getBoundingClientRect();
    const px = cx === undefined ? host.width / 2 : cx, py = cy === undefined ? host.height / 2 : cy;
    const k = clamp(state.view.k * factor, 0.2, 2.5), ratio = k / state.view.k;
    const target = { k, x: px - (px - state.view.x) * ratio, y: py - (py - state.view.y) * ratio };
    if (animate) settle(target, null, 1, 0.3);
    else { interrupt(); state.view = target; applyView(); }
  }
  function lineage(id) {
    const seen = new Set([id]);
    for (const direction of ["ins", "outs"]) {
      const stack = [id];
      while (stack.length) {
        const item = state.model.nodes.get(stack.pop());
        if (item) item[direction].forEach((next) => { if (!seen.has(next)) { seen.add(next); stack.push(next); } });
      }
    }
    return seen;
  }
  function highlight() {
    const root = $("graph"), model = state.model;
    const active = state.hover && model.nodes.has(state.hover) ? state.hover : model.nodes.has(state.selected) ? state.selected : null;
    const set = active ? lineage(active) : null;
    root.classList.toggle("faded", Boolean(set));
    model.nodes.forEach((item) => {
      item.el.classList.toggle("hl", Boolean(set && set.has(item.id)));
      item.el.classList.toggle("selected", item.id === state.selected);
    });
    model.edges.forEach((edge) => edge.el.classList.toggle("hl", Boolean(set && set.has(edge.from.id) && set.has(edge.to.id))));
  }
  function applyStep() {
    const model = state.model, at = local();
    model.nodes.forEach((item) => {
      item.el.classList.toggle("unborn", item.birth > at);
      item.el.classList.toggle("current", !state.browsing && item.column === "finding" && item.birth === at);
    });
    model.edges.forEach((edge) => edge.el.classList.toggle("unborn", edge.birth > at));
    const slider = $("graph-step");
    slider.max = String(state.steps);
    slider.value = String(state.step);
    slider.disabled = !state.steps;
    slider.setAttribute("aria-valuetext", !state.steps ? "No claims to replay" : state.browsing
      ? "Viewing claims " + (state.page * PAGE + 1) + " through " + state.step + " of " + state.steps
      : state.step + " of " + state.steps + " checked claims");
    controls();
    const last = at > 0 ? model.shown[at - 1] : null;
    $("graph-step-label").textContent = !state.steps ? "No claims to replay"
      : state.browsing ? "Viewing " + (state.page * PAGE + 1) + "–" + state.step + " / " + state.steps
      : state.step + " / " + state.steps + (last ? " · " + last.id + (last.refused ? " refused" : " certified") : " · Start");
  }
  function controls() {
    const start = state.total ? state.page * PAGE + 1 : 0, end = Math.min(state.total, (state.page + 1) * PAGE);
    $("graph-range").textContent = state.total ? start + "–" + end + " of " + state.total : "0";
    $("graph-prev").disabled = state.page === 0;
    $("graph-next").disabled = end >= state.total;
    $("graph-focus").hidden = !state.focus;
    const focused = state.items.find((item) => item.key === state.focus);
    $("graph-focus-label").textContent = focused ? focused.id + " and related" : "";
    $("graph-focus").title = focused ? "Showing " + focused.id + " and the findings that cite any of the same records" : "";
    const action = state.timer ? "Pause" : !state.browsing && state.step > 0 && state.step < state.steps ? "Resume" : "Replay";
    $("graph-play").textContent = (state.timer ? "❚❚ " : "▶ ") + action;
    $("graph-play").setAttribute("aria-label", action + " the graph");
    $("graph-play").disabled = !state.steps;
    $("graph-lock").setAttribute("aria-pressed", String(state.locked));
    $("graph-start").disabled = !state.steps || state.step === 0;
    $("graph-end").disabled = !state.steps || (!state.browsing && state.step === state.steps && state.page === Math.max(0, Math.ceil(state.steps / PAGE) - 1));
  }
  function scopes() {
    const select = $("graph-scope"), counts = new Map();
    state.items.forEach((item) => { const question = text(item.data.question); counts.set(question, (counts.get(question) || 0) + 1); });
    select.replaceChildren();
    const every = document.createElement("option");
    every.value = ""; every.textContent = "All questions (" + state.items.length + ")";
    select.append(every);
    if (counts.size > 1) counts.forEach((total, question) => {
      const option = document.createElement("option");
      option.value = question; option.textContent = clip(question || "No question recorded", 64) + " (" + total + ")";
      select.append(option);
    });
    if (![...counts.keys()].includes(state.scope)) state.scope = "";
    select.value = state.scope;
  }
  function rebuild(refit) {
    stop();
    interrupt();
    build();
    draw();
    if (refit || !state.fitted) state.fitted = fit();
  }

  // ---- replay -------------------------------------------------------------
  function stop() { if (state.timer) { clearInterval(state.timer); state.timer = null; controls(); } }
  // Scroll so the finding the replay has just reached is on screen, whether it is playing or being dragged.
  function followTarget(item, host, inset, view) {
    const visibleTop = inset.top + 12, visibleBottom = Math.max(visibleTop + 1, host.height - inset.bottom - 12);
    // A manually enlarged card must still fit when replay takes control again.
    const k = Math.min(view.k, Math.max(1, host.width - 40) / item.w, (visibleBottom - visibleTop) / item.h);
    const target = { ...view, k }, left = item.x * k + view.x, right = (item.x + item.w) * k + view.x;
    const top = (item.y - item.h / 2) * k + view.y, bottom = (item.y + item.h / 2) * k + view.y;
    if (left < 20) target.x = 20 - item.x * k;
    else if (right > host.width - 20) target.x = host.width - 20 - (item.x + item.w) * k;
    if (top < visibleTop || bottom > visibleBottom) target.y = (visibleTop + visibleBottom) / 2 - item.y * k;
    return target;
  }
  function follow() {
    if (state.locked) return;   // the viewer asked for the view to stay where it is
    const at = local(), host = $("graph-host").getBoundingClientRect();
    const newest = [...state.model.nodes.values()].find(item => item.column === "finding" && item.birth === at);
    if (!newest || !host.height || !host.width) return;
    // Replay positions and the visible card change together, including during fast playback.
    interrupt();
    state.view = followTarget(newest, host, insets(), state.view);
    applyView();
  }
  // Move the replay to a position, turning to the page that holds it.
  function seek(step) {
    state.browsing = false;
    state.step = Math.max(0, Math.min(state.steps, Math.round(Number(step) || 0)));
    const page = Math.max(0, Math.floor((state.step - 1) / PAGE));
    if (page === state.page) { applyStep(); return follow(); }
    state.page = page;
    interrupt();
    build();
    draw();
    if (!state.locked) fit(false, true);
    follow();
  }
  function play() {
    if (state.timer) return stop();
    if (!state.steps) return;
    if (state.browsing || state.step >= state.steps) seek(0);
    // A short case plays slowly enough to follow; a long one still finishes in about half a minute.
    const pace = Math.max(70, Math.min(520, Math.round(30000 / Math.max(1, state.steps))));
    state.timer = setInterval(() => {
      seek(state.step + 1);
      if (state.step >= state.steps) stop();
    }, pace);
    controls();
  }

  // ---- inspector ----------------------------------------------------------
  function select(id) {
    state.selected = id;
    highlight();
    const item = state.model.nodes.get(id), app = CONAN.app;
    if (!item || !app) return;
    if (item.column === "finding" && !item.item.refused) return app.openFinding(item.item.data);
    if (item.cls === "more") return app.openFinding(item.item.data);
    const el = app.element, summary = [], evidence = [];
    let title = "Inspector", proof = null;
    const jump = (label, target) => { const button = el("button", "text-button", label); button.type = "button"; button.addEventListener("click", () => select(target)); return button; };
    const links = (label, ids) => { const box = el("div", "link-list"); box.append(el("p", "proof-heading", label)); ids.forEach((target) => { const n = state.model.nodes.get(target); if (n) box.append(jump(describe(n), target)); }); return box; };
    if (item.column === "finding") {
      const data = item.item.data, gap = object(data.proof_gap);
      title = "Refused proposal " + item.item.id;
      const badges = el("div", "finding-identity");
      badges.append(app.badge("REFUSED BY THE CHECKER", "refused"));
      summary.push(badges);
      if (data.question) summary.push(el("p", "finding-question", data.question));
      summary.push(el("p", "statement", gap.summary || data.reason || "The checker refused this proposal."), el("p", "detail-intro", "A refusal means the cited records do not establish the claim. It does not mean the claim is false."));
      item.item.rows.forEach((row) => evidence.push(app.recordCard(row)));
      if (!item.item.rows.length) evidence.push(el("p", "detail-intro", "The diagnostics did not name records."));
      proof = [el("p", "proof-heading", "Checker conditions")];
      const checks = el("div", "check-list");
      array(data.parts).forEach((part) => array(object(part).bricks).forEach((brick) => checks.append(el("div", /^FAIL/.test(text(brick)) ? "fail" : "ok", text(brick)))));
      proof.push(checks);
      array(gap.requirements).forEach((raw) => {
        const requirement = object(raw);
        proof.push(el("p", "proof-heading", text(requirement.category || "unmet condition").replace(/_/g, " ")));
        if (requirement.reason) proof.push(el("p", "", requirement.reason));
        if (requirement.action) proof.push(el("p", "detail-intro", requirement.action));
      });
      proof.push(el("p", "proof-heading", "Proposed claim"), app.code(data.claim));
    } else if (item.column === "record") {
      title = "Record #" + text(item.row.id);
      summary.push(el("p", "statement", [item.row.kind, item.row.obj_text].filter(Boolean).join(" · ")), links("Cited by", [...item.outs]));
      evidence.push(app.recordCard(item.row));
    } else if (item.column === "artifact") {
      title = "Source artifact";
      summary.push(el("p", "statement mono", item.path), el("p", "detail-intro", "Exhibit " + item.exhibit + " · " + item.rows.length + " cited record" + (item.rows.length === 1 ? "" : "s") + " in view"));
      item.rows.forEach((row) => evidence.push(app.recordCard(row)));
    } else if (item.column === "exhibit") {
      title = "Exhibit " + item.label;
      summary.push(el("p", "statement", item.image ? "Disk image " + item.image : "Image name not recorded"), links("Artifacts read from it, in view", [...item.outs]));
      evidence.push(el("p", "detail-intro", "Records are extracted from this image by deterministic readers. The proof checks claims against those records; it does not check the readers."));
    } else {
      const conclusion = object(item.conclusion);
      title = "Interpretation " + text(conclusion.conclusion_id);
      const badges = el("div", "finding-identity");
      badges.append(app.badge("NOT CERTIFIED", "judgment"));
      if (conclusion.rests_on_heuristic) badges.append(app.badge("Rests on a heuristic finding", "heuristic"));
      summary.push(badges, el("p", "statement", text(conclusion.text)), links("Cites certified findings", [...item.ins]));
      evidence.push(el("p", "detail-caveat", conclusion.note || "The investigator's judgment. Citing certified findings does not certify the interpretation."));
      if (conclusion.author) evidence.push(el("p", "detail-intro", "Author: " + conclusion.author));
    }
    app.inspect(title, summary, evidence, proof);
  }
  function describe(item) {
    if (item.column === "finding") return item.item.id + " · " + clip(item.item.refused ? "refused" : item.item.data.english, 60);
    if (item.column === "record") return "#" + text(item.row.id) + " " + text(item.row.kind);
    if (item.column === "artifact") return clip(item.path, 64);
    if (item.column === "judgment") return text(object(item.conclusion).conclusion_id);
    return text(item.label);
  }
  function focus(key) {
    state.focus = key; state.page = 0; state.selected = key; state.browsing = true;
    rebuild(true);
  }

  // ---- events -------------------------------------------------------------
  function wire() {
    const root = $("graph");
    // Lock view: the replay still moves through the findings, but the canvas stays where the viewer put it.
    try { state.locked = localStorage.getItem("conan.graph.lock") === "1"; } catch (error) { /* starts unlocked */ }
    $("graph-lock").addEventListener("click", () => {
      state.locked = !state.locked;
      try { localStorage.setItem("conan.graph.lock", state.locked ? "1" : "0"); } catch (error) { /* not remembered */ }
      controls();
      if (!state.locked && !state.browsing && state.step > 0) follow();   // unlocking catches up with the replay
    });
    root.addEventListener("pointerdown", (event) => {
      if (event.target.closest(".node") || event.button !== 0) return;
      interrupt();   // grab the canvas mid-flight; it continues from where it is
      state.drag = { x: event.clientX, y: event.clientY, vx: state.view.x, vy: state.view.y, moved: false, lim: limits(),
        trail: [{ t: event.timeStamp, x: event.clientX, y: event.clientY }] };
      root.setPointerCapture(event.pointerId);
      root.classList.add("dragging");
    });
    root.addEventListener("pointermove", (event) => {
      const drag = state.drag;
      if (!drag) return;
      const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
      drag.trail.push({ t: event.timeStamp, x: event.clientX, y: event.clientY });
      if (drag.trail.length > 6) drag.trail.shift();
      const lim = drag.lim;
      state.view.x = lim ? banded(drag.vx + dx, lim.minX, lim.maxX, lim.width) : drag.vx + dx;
      state.view.y = lim ? banded(drag.vy + dy, lim.minY, lim.maxY, lim.height) : drag.vy + dy;
      applyView();
    });
    const release = (event) => {
      const drag = state.drag;
      state.drag = null;
      root.classList.remove("dragging");
      if (!drag) return false;
      if (drag.moved) {
        // Hand the pointer's velocity to the spring and aim at where the flick was going.
        const recent = drag.trail.filter((point) => event.timeStamp - point.t < 110);
        const first = recent[0], last = recent[recent.length - 1], dt = first && last ? (last.t - first.t) / 1000 : 0;
        const velocity = dt > 0.012 ? { x: (last.x - first.x) / dt, y: (last.y - first.y) / dt } : { x: 0, y: 0 };
        const lim = drag.lim, target = { k: state.view.k, x: state.view.x + project(velocity.x), y: state.view.y + project(velocity.y) };
        if (lim) { target.x = clamp(target.x, lim.minX, lim.maxX); target.y = clamp(target.y, lim.minY, lim.maxY); }
        if (Math.abs(target.x - state.view.x) + Math.abs(target.y - state.view.y) > 1) settle(target, velocity);
      }
      return drag.moved;
    };
    root.addEventListener("pointerup", (event) => { if (!release(event) && state.selected) { state.selected = null; highlight(); } });
    root.addEventListener("pointercancel", release);
    root.addEventListener("wheel", (event) => {
      event.preventDefault();
      interrupt();
      const host = root.getBoundingClientRect();
      if (event.ctrlKey || event.metaKey) return zoom(Math.exp(-event.deltaY * 0.01), event.clientX - host.left, event.clientY - host.top);
      const lim = limits();
      state.view.x = lim ? clamp(state.view.x - event.deltaX, lim.minX, lim.maxX) : state.view.x - event.deltaX;
      state.view.y = lim ? clamp(state.view.y - event.deltaY, lim.minY, lim.maxY) : state.view.y - event.deltaY;
      applyView();
    }, { passive: false });
    $("graph-zoom-in").addEventListener("click", () => zoom(1.25, undefined, undefined, true));
    $("graph-zoom-out").addEventListener("click", () => zoom(0.8, undefined, undefined, true));
    $("graph-fit").addEventListener("click", () => fit(true));
    $("graph-play").addEventListener("click", play);
    const slider = $("graph-step");
    slider.addEventListener("pointerdown", stop);
    for (const name of ["input", "change"]) slider.addEventListener(name, event => { stop(); seek(event.target.value); });
    slider.addEventListener("keydown", event => {
      if (event.key === "Home" || event.key === "End") { event.preventDefault(); stop(); seek(event.key === "End" ? state.steps : 0); }
    });
    $("graph-start").addEventListener("click", () => { stop(); seek(0); controls(); });
    $("graph-end").addEventListener("click", () => { stop(); seek(state.steps); controls(); });
    $("graph-scope").addEventListener("change", (event) => { state.scope = event.target.value; state.focus = null; state.page = 0; state.browsing = true; rebuild(true); });
    $("graph-search").addEventListener("input", (event) => {
      state.query = event.target.value.trim().toLowerCase(); state.focus = null; state.page = 0; state.browsing = true;
      rebuild(true);
    });
    $("graph-prev").addEventListener("click", () => { state.page -= 1; state.browsing = true; rebuild(true); });
    $("graph-next").addEventListener("click", () => { state.page += 1; state.browsing = true; rebuild(true); });
    $("graph-focus-clear").addEventListener("click", () => { state.focus = null; state.page = 0; state.browsing = true; rebuild(true); });
    window.addEventListener("resize", resize);
    if (typeof ResizeObserver !== "undefined") new ResizeObserver(resize).observe($("graph-host"));
  }

  function resize() {
    if (!state.fitted) state.fitted = fit();
    else if (!state.browsing && state.step > 0) follow();
  }

  CONAN.graph = {
    render(run, events, key, revision = null) {
      const bundle = object(run);
      const signature = revision === null ? JSON.stringify([bundle, array(events)]) : revision;
      const changedCase = key !== state.key;
      if (!changedCase && signature === state.signature) return;
      if (changedCase) Object.assign(state, { scope: "", query: "", focus: null, page: 0, step: 0, browsing: true, selected: null, hover: null, fitted: false });
      state.key = key; state.signature = signature; state.run = bundle; state.events = array(events);
      if (changedCase) $("graph-search").value = "";
      prepare();
      scopes();
      rebuild(changedCase);
    },
    clear() {
      stop();
      Object.assign(state, { key: null, signature: null, run: null, events: [], items: [], selected: null, hover: null, fitted: false });
      state.model = { nodes: new Map(), edges: [], shown: [] };
      $("graph").replaceChildren();
    },
    resize,
    focusFinding(id, data = null) {
      const matches = state.items.filter((item) => item.id === id && !item.refused && (!data || item.data === data));
      if (matches.length === 1) focus(matches[0].key);
    },
  };
  wire();
})();
