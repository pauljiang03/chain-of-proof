/* CONAN-F timeline: when the cited evidence records say things happened.
   Every mark is one record that an accepted finding cites. Nothing is inferred here:
   a record is placed at its own recorded time and says what that time means. Times are
   shown on the case's own clock when the records name its time zone, and in UTC otherwise. */
(() => {
  "use strict";
  const CONAN = (window.CONAN = window.CONAN || {});
  const $ = (id) => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const svg = (tag, attrs, text) => {
    const node = document.createElementNS(NS, tag);
    for (const key in attrs) node.setAttribute(key, attrs[key]);
    if (text !== undefined) node.textContent = String(text);
    return node;
  };
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  };
  const array = (value) => (Array.isArray(value) ? value : []);
  const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
  const MINUTE = 60000, HOUR = 60 * MINUTE, DAY = 24 * HOUR;
  function formats(timeZone) {
    const make = (options) => new Intl.DateTimeFormat("en-GB", { timeZone, hourCycle: "h23", ...options });
    return {
      full: make({ day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      minute: make({ day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }),
      day: make({ weekday: "short", day: "numeric", month: "short", year: "numeric" }),
      short: make({ day: "numeric", month: "short" }),
      clock: make({ hour: "2-digit", minute: "2-digit" }),
      seconds: make({ hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      month: make({ month: "short", year: "numeric" }),
      year: make({ year: "numeric" }),
      parts: make({ year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric", second: "numeric" }),
    };
  }
  // The case clock. It is the time zone the evidence records themselves name; with none named, UTC.
  const UTC = formats("UTC");
  let F = UTC, zone = { name: "UTC", local: false, records: 0 };
  const leads = new Map();
  // How far the case clock runs ahead of UTC at an instant, in milliseconds (negative west of Greenwich).
  function lead(t) {
    if (!zone.local) return 0;
    const key = Math.floor(t / (15 * MINUTE));
    let value = leads.get(key);
    if (value === undefined) {
      const p = {};
      for (const part of F.parts.formatToParts(t)) p[part.type] = Number(part.value);
      value = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - Math.floor(t / 1000) * 1000;
      leads.set(key, value);
    }
    return value;
  }
  const wall = (t) => t + lead(t);                 // what the case clock reads, written as if it were UTC
  const unwall = (w) => w - lead(w - lead(w));     // and back to the instant
  function adopt(found) {
    leads.clear();
    F = UTC; zone = { name: "UTC", local: false, records: 0 };
    if (!found) return;
    try { F = formats(found.name); zone = { name: found.name, local: true, records: found.records }; } catch (_) { F = UTC; /* a zone this system does not know */ }
  }
  const zoneNote = () => (zone.local ? "local time (" + zone.name + ")" : "UTC");

  // ---- the story model: records in plain words -------------------------------
  // Kinds of activity, in a fixed order. A lane keeps its colour whatever else is shown.
  const LANES = [
    { key: "devices", name: "Devices & discs" },
    { key: "files", name: "Files & folders" },
    { key: "web", name: "Web" },
    { key: "messages", name: "E-mail & cloud" },
    { key: "programs", name: "Programs" },
    { key: "accounts", name: "Sign-ins & accounts" },
    { key: "system", name: "System & notes" },
    { key: "other", name: "Other records" },
  ];
  const LANE_INDEX = Object.fromEntries(LANES.map((lane, index) => [lane.key, index]));
  // record kind: lane, one of them, several of them, and whether it is drawn as a key event.
  // Key events are chosen here by record type alone; no model decides what matters.
  const KINDS = {
    usbInsert: ["devices", "USB device connected", "USB device connections", true],
    volumeSeen: ["devices", "Storage volume seen", "storage volumes seen", true],
    cdBurn: ["devices", "Disc-burning trace", "disc-burning traces", true],
    volumeOnDevice: ["devices", "Volume on a device", "volumes on devices", false],
    unallocatedOnDevice: ["devices", "Unused space on a device", "unused-space records", false],
    fileCreated: ["files", "File created", "files created", false],
    fileModified: ["files", "File modified", "files modified", false],
    fileDeleted: ["files", "File deleted", "files deleted", true],
    fileRenamed: ["files", "File renamed", "files renamed", true],
    fileSeen: ["files", "File noted by the system", "files noted by the system", false],
    lnkTarget: ["files", "File opened", "files opened", true],
    folderOpened: ["files", "Folder record", "folder records", false],
    fileContent: ["files", "File content read", "file contents read", false],
    localSearch: ["files", "Search typed on the PC", "searches typed on the PC", true],
    webVisit: ["web", "Web page visit", "web page visits", false],
    webSearch: ["web", "Web search", "web searches", true],
    fileDownloaded: ["web", "File downloaded", "files downloaded", true],
    emailSent: ["messages", "E-mail", "e-mails", true],
    cloudFile: ["messages", "Cloud file activity", "cloud file records", true],
    programRun: ["programs", "Program activity", "program activity records", false],
    programInstalled: ["programs", "Program installed", "programs installed", true],
    sessionEvent: ["accounts", "Sign-in or power event", "sign-in and power events", false],
    accountSeen: ["accounts", "Account record", "account records", false],
    systemSetting: ["system", "System setting", "system settings", false],
    shadowCopy: ["system", "Backup snapshot made", "backup snapshots made", true],
    noteText: ["system", "Note", "notes", true],
    tag: ["other", "Label", "labels", false],
  };
  const EXAMINED = /^when the image was examined/i;   // a time of examination is not a time of an event
  const ZONE = /\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)\/[A-Za-z_]+(?:\/[A-Za-z_]+)?/;
  const show = (value) => (value === undefined || value === null ? "" : typeof value === "string" ? value : JSON.stringify(value));
  const stable = (value) => (value && typeof value === "object"
    ? Array.isArray(value) ? "[" + value.map(stable).join(",") + "]"
      : "{" + Object.keys(value).sort().map((key) => JSON.stringify(key) + ":" + stable(value[key])).join(",") + "}"
    : JSON.stringify(value));
  const lower = (list, value) => {
    let a = 0, b = list.length;
    while (a < b) { const middle = (a + b) >> 1; if (list[middle] < value) a = middle + 1; else b = middle; }
    return a;
  };
  function clip(value, max = 80) {
    const text = String(value).replace(/\s+/g, " ").trim();
    if (text.length <= max) return text;
    const head = Math.ceil(max * 0.4);
    return text.slice(0, head) + "…" + text.slice(text.length - (max - head - 1));
  }
  const describe = (record, max = 90) => record.one + (record.obj ? ": " + clip(record.obj, max) : "") + (record.aux ? " — " + clip(record.aux, Math.max(30, max / 2)) : "");

  function make(row) {
    const kind = typeof row.kind === "string" ? row.kind : "";
    const known = Object.prototype.hasOwnProperty.call(KINDS, kind) ? KINDS[kind] : ["other", kind ? "Record (" + kind + ")" : "Record", "records", false];
    const prov = row.prov && typeof row.prov === "object" ? row.prov : {};
    const obj = show(row.obj_text === undefined ? row.obj : row.obj_text), aux = show(row.aux_text === undefined ? row.aux : row.aux_text);
    const meaning = typeof prov.time_meaning === "string" ? prov.time_meaning : typeof prov.timestamp_semantics === "string" ? prov.timestamp_semantics : "";
    const exhibit = prov.exhibit === undefined || prov.exhibit === null ? "" : String(prov.exhibit);
    return {
      row, kind, lane: LANE_INDEX[known[0]], one: known[1], many: known[2], marked: known[3], obj, aux: aux === "(none)" ? "" : aux,
      meaning, exhibit, image: prov.image === undefined || prov.image === null ? "" : String(prov.image), ms: null, findings: [],
      text: (known[1] + " " + obj + " " + aux + " " + exhibit + " " + kind).toLowerCase(),
    };
  }
  function build(run) {
    const findings = array(run && run.findings).filter((finding) => finding && finding.status === "verified");
    const byContent = new Map();
    for (const finding of findings) {
      for (const row of array(finding.cited_facts)) {
        if (!row || typeof row !== "object") continue;
        const key = stable(row);   // a differing copy of a record is kept as a different record
        let record = byContent.get(key);
        if (!record) byContent.set(key, (record = make(row)));
        if (record.findings[record.findings.length - 1] !== finding) record.findings.push(finding);
      }
    }
    const records = [...byContent.values()];
    const examined = new Set(records.filter((record) => EXAMINED.test(record.meaning)).map((record) => record.row.t));
    const events = [];
    for (const record of records) {
      const t = record.row.t;
      if (Number.isSafeInteger(t) && t > 0 && !EXAMINED.test(record.meaning) && !(!record.meaning && examined.has(t))) { record.ms = t / 1000; events.push(record); }
    }
    events.sort((a, b) => a.ms - b.ms);
    // The busiest period: the run of records with no gap longer than two days that holds the most records.
    let main = null, start = 0;
    for (let i = 1; i <= events.length; i += 1) {
      if (i === events.length || events[i].ms - events[i - 1].ms > 2 * DAY) {
        if (!main || i - start > main.count) main = { from: events[start].ms, to: events[i - 1].ms, count: i - start };
        start = i;
      }
    }
    const lanes = LANES.map(() => ({ records: 0, events: 0 }));
    records.forEach((record) => { lanes[record.lane].records += 1; if (record.ms !== null) lanes[record.lane].events += 1; });
    // The case's time zone is the one most of its records say their local times were converted from.
    const named = new Map();
    for (const record of records) {
      const prov = record.row.prov, match = prov && typeof prov.time_zone === "string" ? prov.time_zone.match(ZONE) : null;
      if (match) named.set(match[0], (named.get(match[0]) || 0) + 1);
    }
    const chosen = [...named.entries()].sort((a, b) => b[1] - a[1])[0];
    return {
      zone: chosen ? { name: chosen[0], records: chosen[1] } : null,
      findings, records, events, times: events.map((record) => record.ms), lanes, main,
      range: events.length ? { from: events[0].ms, to: events[events.length - 1].ms } : null,
    };
  }
  let cache = { name: null, revision: null, model: null };
  function open(run, name, revision) {
    if (cache.model && revision !== undefined && revision !== null && cache.name === name && cache.revision === revision) return cache.model;
    cache = { name, revision, model: build(run) };
    adopt(cache.model.zone);
    return cache.model;
  }

  // Axis marks for a span of time on the case clock: clock times within days, then days, months, years.
  const STEPS = [MINUTE, 5 * MINUTE, 15 * MINUTE, 30 * MINUTE, HOUR, 3 * HOUR, 6 * HOUR, 12 * HOUR, DAY, 2 * DAY, 7 * DAY];
  function ticks(t0, span, plot) {
    const want = span / Math.max(2, Math.floor(plot / 92)), end = t0 + span, list = [];
    const fixed = STEPS.find((step) => step >= want);
    if (fixed) {
      for (let w = Math.ceil(wall(t0) / fixed) * fixed; w <= wall(end); w += fixed) {
        const t = unwall(w), midnight = w % DAY === 0, date = new Date(w), newYear = midnight && date.getUTCMonth() === 0 && date.getUTCDate() === 1;
        if (t < t0 || t > end) continue;
        if (fixed < DAY) list.push({ t, label: F.clock.format(t), major: midnight, sub: midnight ? F.day.format(t) : "" });
        else list.push({ t, label: F.short.format(t), major: newYear, sub: newYear ? F.year.format(t) : "" });
      }
      return { list, context: fixed < DAY ? F.day.format(t0) : F.year.format(t0) };
    }
    const size = [1, 3, 6, 12, 24, 60, 120, 240].find((months) => months * 30.44 * DAY >= want) || 600, first = new Date(wall(t0));
    for (let k = Math.ceil((first.getUTCFullYear() * 12 + first.getUTCMonth()) / size) * size; ; k += size) {
      const t = unwall(Date.UTC(Math.floor(k / 12), ((k % 12) + 12) % 12, 1));
      if (t > end) break;
      if (t >= t0) list.push({ t, label: size >= 12 ? F.year.format(t) : F.month.format(t), major: k % 12 === 0, sub: "" });
    }
    return { list, context: "" };
  }
  const dot = (lane) => el("i", "dot c" + lane);
  CONAN.story = {
    LANES, UTC, open, build, adopt, describe, clip, lower, ticks, dot, number, wall, unwall, zoneNote, DAY, HOUR, MINUTE,
    get F() { return F; }, get zone() { return zone; },
  };

  // ---- the timeline view -----------------------------------------------------
  const LEFT = 152, RIGHT = 14, TOP = 6, LANE = 46, AXIS = 42, COLUMN = 3, LIST_MAX = 200;
  const view = {
    model: null, name: null, off: new Set(), query: "", keyOnly: true, t0: 0, span: 0, width: 0,
    lanes: [], shown: [], times: [], selected: null, parts: null, frame: 0, tween: 0, listTimer: 0, drag: null,
  };
  const still = () => typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function refilter() {
    const model = view.model, query = view.query;
    view.shown = model ? model.events.filter((record) => !view.off.has(record.lane) && (!query || record.text.includes(query))) : [];
    view.times = view.shown.map((record) => record.ms);
    view.lanes = model ? model.lanes.map((count, index) => ({ index, items: [], ms: [], marked: [], markedMs: [] })).filter((lane) => model.lanes[lane.index].events && !view.off.has(lane.index)) : [];
    const byIndex = new Map(view.lanes.map((lane) => [lane.index, lane]));
    for (const record of view.shown) {
      const lane = byIndex.get(record.lane);
      lane.items.push(record); lane.ms.push(record.ms);
      if (record.marked) { lane.marked.push(record); lane.markedMs.push(record.ms); }
    }
  }
  function chips() {
    const host = $("timeline-lanes"), model = view.model;
    host.replaceChildren();
    if (!model) return;
    model.lanes.forEach((count, index) => {
      if (!count.events) return;
      const chip = el("button", "chip");
      chip.type = "button";
      chip.setAttribute("aria-pressed", String(!view.off.has(index)));
      chip.title = "Show or hide " + LANES[index].name;
      chip.append(dot(index), LANES[index].name, el("small", "", number.format(count.events)));
      chip.addEventListener("click", () => {
        if (view.off.has(index)) view.off.delete(index); else view.off.add(index);
        chips(); refilter(); layout(); schedule();
      });
      host.append(chip);
    });
  }

  function clamp(t0, span) {
    const range = view.model && view.model.range;
    if (!range) return { t0, span };
    const full = Math.max(10 * MINUTE, range.to - range.from);
    span = Math.max(MINUTE, Math.min(full * 1.3, span));
    return { t0: Math.max(range.from - span * 0.92, Math.min(range.to - span * 0.08, t0)), span };
  }
  function around(from, to) {
    const span = Math.max(10 * MINUTE, to - from) * 1.12;
    return clamp((from + to) / 2 - span / 2, span);
  }
  function go(target, animate) {
    cancelAnimationFrame(view.tween);
    const next = clamp(target.t0, target.span);
    if (!animate || still() || !view.span) { view.t0 = next.t0; view.span = next.span; return schedule(); }
    const from = { centre: view.t0 + view.span / 2, log: Math.log(view.span) }, to = { centre: next.t0 + next.span / 2, log: Math.log(next.span) }, began = performance.now();
    const step = (now) => {
      const p = Math.min(1, (now - began) / 280), ease = 1 - Math.pow(1 - p, 3);
      view.span = Math.exp(from.log + (to.log - from.log) * ease);
      view.t0 = from.centre + (to.centre - from.centre) * ease - view.span / 2;
      draw();
      if (p < 1) view.tween = requestAnimationFrame(step);
    };
    view.tween = requestAnimationFrame(step);
  }
  const mainView = () => (view.model.main ? around(view.model.main.from, view.model.main.to) : null);
  const allView = () => (view.model.range ? around(view.model.range.from, view.model.range.to) : null);
  function zoomAt(factor, px, animate) {
    const plot = view.width - LEFT - RIGHT, share = Math.max(0, Math.min(1, (px - LEFT) / plot)), at = view.t0 + share * view.span, span = view.span / factor;
    go({ t0: at - share * span, span }, animate);
  }

  function layout() {
    const root = $("timeline"), model = view.model, empty = $("timeline-empty");
    view.parts = null;
    root.replaceChildren();
    const none = !model || !model.events.length;
    empty.hidden = !none && view.lanes.length > 0;
    root.style.display = empty.hidden ? "" : "none";
    if (!empty.hidden) {
      empty.replaceChildren(el("h3", "", none ? "No dated records yet" : "Every kind of activity is hidden"),
        el("p", "", none ? "The timeline fills in once findings that cite dated records pass the checker." : "Turn a kind of activity back on above."));
      $("timeline-range").textContent = "";
      return;
    }
    if (!view.width) return;
    const plot = view.width - LEFT - RIGHT, bottom = TOP + view.lanes.length * LANE, height = bottom + AXIS;
    root.setAttribute("width", view.width); root.setAttribute("height", height); root.setAttribute("viewBox", "0 0 " + view.width + " " + height);
    const window_ = svg("clipPath", { id: "timeline-clip" }), defs = svg("defs", {});
    window_.append(svg("rect", { x: LEFT, y: 0, width: Math.max(0, plot), height }));
    defs.append(window_);
    const axis = svg("g", { class: "axis" }), body = svg("g", { "clip-path": "url(#timeline-clip)" });
    const cursor = svg("line", { class: "cursor", y1: TOP, y2: bottom, visibility: "hidden" });
    const picked = svg("g", { class: "picked", visibility: "hidden" });
    picked.append(svg("line", { y1: 0, y2: LANE }), svg("circle", { r: 8 }));
    root.append(defs);
    view.lanes.forEach((lane, i) => {
      const y = TOP + i * LANE;
      lane.count = svg("text", { class: "lane-count", x: 26, y: y + 36 }, "");
      root.append(svg("rect", { class: "lane-bg" + (i % 2 ? " alt" : ""), x: 0, y, width: view.width, height: LANE }),
        svg("circle", { class: "lane-dot c" + lane.index, cx: 14, cy: y + 18, r: 4.5 }),
        svg("text", { class: "lane-name", x: 26, y: y + 22 }, LANES[lane.index].name), lane.count);
      const group = svg("g", { class: "c" + lane.index });
      lane.paths = [1, 2, 3].map((level) => svg("path", { class: "ticks t" + level }));
      lane.dots = svg("g", {});
      group.append(...lane.paths, lane.dots);
      body.append(group);
    });
    root.append(axis, body, cursor, picked);
    view.parts = { axis, cursor, picked, plot, bottom };
  }

  function schedule() { if (!view.frame) view.frame = requestAnimationFrame(draw); }
  function draw() {
    view.frame = 0;
    const parts = view.parts;
    if (!parts || !view.model || !view.span) return;
    const { plot, bottom } = parts, scale = plot / view.span, end = view.t0 + view.span;
    const marks = ticks(view.t0, view.span, plot), axis = [];
    let dated = false;
    for (const mark of marks.list) {
      const x = LEFT + (mark.t - view.t0) * scale;
      axis.push(svg("line", { class: "grid" + (mark.major ? " major" : ""), x1: x, x2: x, y1: TOP, y2: bottom + 5 }), svg("text", { class: "axis-label", x, y: bottom + 18 }, mark.label));
      // A date sits under the midnight it starts at; near the left edge it begins at its own mark.
      if (mark.sub) { axis.push(svg("text", { class: "axis-label major" + (x < LEFT + 60 ? " start" : ""), x, y: bottom + 34 }, mark.sub)); if (x < LEFT + 190) dated = true; }
    }
    // With no midnight near the left edge, say which date the view starts in.
    if (marks.context && !dated) axis.push(svg("text", { class: "axis-label major start", x: LEFT + 2, y: bottom + 34 }, marks.context));
    axis.push(svg("text", { class: "axis-label start", x: 12, y: bottom + 18 }, zone.local ? "Case local time" : "Time in UTC"));
    if (zone.local) axis.push(svg("text", { class: "axis-label start", x: 12, y: bottom + 34 }, zone.name));
    parts.axis.replaceChildren(...axis);
    let inView = 0, keys = 0;
    view.lanes.forEach((lane, i) => {
      const y = TOP + i * LANE, ms = lane.ms, a = lower(ms, view.t0), b = lower(ms, end);
      // One line per three-pixel column; a darker line means more records share that moment.
      const d = ["", "", ""];
      let column = -1, n = 0;
      const flush = () => { if (n) d[n === 1 ? 0 : n <= 5 ? 1 : 2] += "M" + (LEFT + column * COLUMN + 1) + " " + (y + 24) + "v16"; };
      for (let j = a; j < b; j += 1) {
        const c = Math.floor(((ms[j] - view.t0) * scale) / COLUMN);
        if (c !== column) { flush(); column = c; n = 0; }
        n += 1;
      }
      flush();
      lane.paths.forEach((path, level) => path.setAttribute("d", d[level]));
      // Key events sit above the lines; neighbours closer than a dot's width share one badge with a count.
      const ka = lower(lane.markedMs, view.t0), kb = lower(lane.markedMs, end), groups = [];
      let group = null;
      for (let j = ka; j < kb; j += 1) {
        const x = LEFT + (lane.markedMs[j] - view.t0) * scale;
        if (group && x - group.last < 13) { group.last = x; group.n += 1; } else groups.push((group = { first: x, last: x, n: 1 }));
      }
      // Badges are wider than dots: join any that would still overlap.
      const wide = (n) => (n === 1 ? 11 : 12 + String(n).length * 6.5), joined = [];
      for (let item of groups) {
        while (joined.length) {
          const before = joined[joined.length - 1];
          if ((item.first + item.last) / 2 - wide(item.n) / 2 >= (before.first + before.last) / 2 + wide(before.n) / 2 + 2) break;
          joined.pop();
          item = { first: before.first, last: item.last, n: before.n + item.n };
        }
        joined.push(item);
      }
      lane.dots.replaceChildren(...joined.map((item) => {
        const x = (item.first + item.last) / 2, cy = y + 13;
        if (item.n === 1) return svg("circle", { class: "mark", cx: x, cy, r: 4.5 });
        const width = wide(item.n), badge = svg("g", { class: "cluster" });
        badge.append(svg("rect", { x: x - width / 2, y: cy - 7.5, width, height: 15, rx: 7.5 }), svg("text", { x, y: cy + 3.5 }, item.n));
        return badge;
      }));
      lane.count.textContent = number.format(b - a) + (b - a === 1 ? " record in view" : " in view");
      inView += b - a; keys += kb - ka;
    });
    const chosen = view.selected, lane = chosen ? view.lanes.findIndex((item) => item.index === chosen.lane) : -1;
    const x = chosen && chosen.ms !== null ? LEFT + (chosen.ms - view.t0) * scale : -1;
    if (lane >= 0 && x >= LEFT && x <= LEFT + plot) {
      parts.picked.setAttribute("visibility", "visible");
      parts.picked.setAttribute("transform", "translate(" + x + "," + (TOP + lane * LANE) + ")");
      parts.picked.lastChild.setAttribute("cy", chosen.marked ? 13 : 32);
    } else parts.picked.setAttribute("visibility", "hidden");
    $("timeline-range").textContent = F.minute.format(view.t0) + " – " + F.minute.format(end) + " " + zoneNote() + " · "
      + number.format(inView) + (inView === 1 ? " record" : " records") + " in view, " + number.format(keys) + (keys === 1 ? " key event" : " key events");
    clearTimeout(view.listTimer);
    view.listTimer = setTimeout(list, 90);
  }

  // The same records as a table: what is in view, in time order.
  function list() {
    const host = $("timeline-list");
    if (!view.model || !view.span) { host.replaceChildren(); return; }
    const a = lower(view.times, view.t0), b = lower(view.times, view.t0 + view.span), rows = [];
    let total = 0;
    for (let i = a; i < b; i += 1) {
      const record = view.shown[i];
      if (view.keyOnly && !record.marked) continue;
      total += 1;
      if (rows.length < LIST_MAX) rows.push(record);
    }
    $("timeline-list-title").textContent = (view.keyOnly ? "Key events" : "Records") + " in view";
    $("timeline-list-count").textContent = number.format(total) + (total > rows.length ? " · showing the first " + rows.length + " — zoom in to narrow the list" : "");
    if (!rows.length) {
      host.replaceChildren(el("p", "timeline-none", view.keyOnly ? "No key events in this stretch of time. Untick “Key events only” to list every record." : "No records in this stretch of time."));
      return;
    }
    host.replaceChildren(...rows.map((record) => {
      const row = el("button", "tl-row" + (record === view.selected ? " selected" : "")), kind = el("span", "kind");
      row.type = "button";
      kind.append(dot(record.lane), record.one);
      row.append(el("span", "time", F.short.format(record.ms) + " " + F.seconds.format(record.ms)), kind,
        el("span", "what", clip(record.obj, 140) + (record.aux ? " — " + clip(record.aux, 70) : "")), el("span", "from", record.exhibit));
      row.addEventListener("click", () => select(record));
      return row;
    }));
  }

  function select(record) {
    view.selected = record;
    schedule();
    const app = CONAN.app;
    if (!app || !record) return;
    const identity = el("div", "finding-identity"), used = el("div", "link-list"), total = record.findings.length;
    identity.append(dot(record.lane), el("span", "", LANES[record.lane].name));
    used.append(el("p", "proof-heading", total === 1 ? "Used by 1 finding that passed the checker" : "Used by " + number.format(total) + " findings that passed the checker"));
    record.findings.slice(0, 12).forEach((finding) => {
      const button = el("button", "text-button", String(finding.finding_id) + " — " + clip(show(finding.english), 120));
      button.type = "button";
      button.addEventListener("click", () => app.openFinding(finding));
      used.append(button);
    });
    if (total > 12) used.append(el("p", "detail-intro", "and " + number.format(total - 12) + " more; search the Findings table for record " + show(record.row.id) + "."));
    const when = record.ms === null ? "This record carries no event time."
      : F.full.format(record.ms) + " " + zoneNote() + (zone.local ? " · " + UTC.full.format(record.ms) + " UTC" : "") + (record.meaning ? " · what this time means: " + record.meaning : "");
    app.inspect("Record #" + app.present(record.row.id), [identity, el("p", "statement", describe(record, 400)), el("p", "detail-intro", when), used], [app.recordCard(record.row)], null);
  }

  // ---- pointer, wheel and keys -----------------------------------------------
  function nearest(items, times, at, reach, max) {
    const a = lower(times, at - reach), b = lower(times, at + reach), out = [];
    let left = lower(times, at) - 1, right = left + 1;
    while (out.length < max && (left >= a || right < b)) {
      if (right >= b || (left >= a && at - times[left] <= times[right] - at)) { out.push(items[left]); left -= 1; } else { out.push(items[right]); right += 1; }
    }
    return { count: b - a, items: out };
  }
  function hit(px, py) {
    const parts = view.parts;
    if (!parts || px < LEFT || px > LEFT + parts.plot || py < TOP) return null;
    const index = Math.floor((py - TOP) / LANE), lane = view.lanes[index];
    if (!lane) return null;
    const each = view.span / parts.plot, at = view.t0 + (px - LEFT) * each;
    let found = py - TOP - index * LANE < 23 ? nearest(lane.marked, lane.markedMs, at, 9 * each, 5) : { count: 0, items: [] };
    if (!found.count) found = nearest(lane.items, lane.ms, at, 4 * each, 5);
    return { at, lane, ...found };
  }
  const local = (event) => { const box = $("timeline-host").getBoundingClientRect(); return { x: event.clientX - box.left, y: event.clientY - box.top, width: box.width }; };
  function hover(event) {
    const tip = $("timeline-tip"), parts = view.parts, at = local(event), found = hit(at.x, at.y);
    if (!parts) return;
    const inside = at.x >= LEFT && at.x <= LEFT + parts.plot && at.y >= TOP && at.y <= parts.bottom;
    parts.cursor.setAttribute("visibility", inside ? "visible" : "hidden");
    parts.cursor.setAttribute("x1", at.x); parts.cursor.setAttribute("x2", at.x);
    if (!found || !found.count) { tip.hidden = true; return; }
    tip.replaceChildren(el("strong", "", (view.span < 3 * HOUR ? F.full : F.minute).format(found.at) + (zone.local ? " local time" : " UTC")));
    found.items.slice().sort((a, b) => a.ms - b.ms).forEach((record) => {
      const line = el("div", "tip-line");
      line.append(dot(record.lane), el("span", "tip-time", F.seconds.format(record.ms)), el("span", "", describe(record, 54)));
      tip.append(line);
    });
    if (found.count > found.items.length) tip.append(el("div", "tip-more", "and " + number.format(found.count - found.items.length) + " more here — zoom in to separate them"));
    tip.hidden = false;
    tip.style.left = Math.max(8, Math.min(at.width - tip.offsetWidth - 8, at.x + 14)) + "px";
    tip.style.top = at.y + 16 + "px";
  }
  function wire() {
    const host = $("timeline-host");
    host.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || !view.parts) return;
      const at = local(event);
      view.drag = { x: at.x, t0: view.t0, moved: false };
      try { host.setPointerCapture(event.pointerId); } catch (_) { /* a pointer that is already gone */ }
      cancelAnimationFrame(view.tween);
    });
    host.addEventListener("pointermove", (event) => {
      const drag = view.drag, at = local(event);
      if (!drag) return hover(event);
      if (Math.abs(at.x - drag.x) > 3) { drag.moved = true; host.classList.add("dragging"); $("timeline-tip").hidden = true; }
      if (drag.moved) go({ t0: drag.t0 - ((at.x - drag.x) / view.parts.plot) * view.span, span: view.span });
    });
    const release = (event) => {
      const drag = view.drag;
      view.drag = null;
      host.classList.remove("dragging");
      if (!drag || drag.moved || event.type !== "pointerup") return;
      const at = local(event), found = hit(at.x, at.y);
      if (found && found.items.length) select(found.items[0]);
    };
    host.addEventListener("pointerup", release);
    host.addEventListener("pointercancel", release);
    host.addEventListener("pointerleave", () => { $("timeline-tip").hidden = true; if (view.parts) view.parts.cursor.setAttribute("visibility", "hidden"); });
    host.addEventListener("dblclick", (event) => { if (view.parts) zoomAt(2.5, local(event).x, true); });
    host.addEventListener("wheel", (event) => {
      if (!view.parts) return;
      event.preventDefault();
      // Sideways moves along time; up and down (or a pinch) zooms around the pointer.
      if (!event.ctrlKey && Math.abs(event.deltaX) > Math.abs(event.deltaY)) go({ t0: view.t0 + (event.deltaX / view.parts.plot) * view.span, span: view.span });
      else zoomAt(Math.exp(-event.deltaY * (event.ctrlKey ? 0.012 : 0.0028)), local(event).x);
      $("timeline-tip").hidden = true;
    }, { passive: false });
    host.addEventListener("keydown", (event) => {
      if (!view.parts) return;
      const centre = LEFT + view.parts.plot / 2;
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") go({ t0: view.t0 + (event.key === "ArrowLeft" ? -0.2 : 0.2) * view.span, span: view.span }, true);
      else if (event.key === "+" || event.key === "=") zoomAt(1.8, centre, true);
      else if (event.key === "-" || event.key === "_") zoomAt(1 / 1.8, centre, true);
      else if (event.key === "Home") go(mainView() || view, true);
      else return;
      event.preventDefault();
    });
    $("timeline-zoom-in").addEventListener("click", () => { if (view.parts) zoomAt(1.8, LEFT + view.parts.plot / 2, true); });
    $("timeline-zoom-out").addEventListener("click", () => { if (view.parts) zoomAt(1 / 1.8, LEFT + view.parts.plot / 2, true); });
    $("timeline-main").addEventListener("click", () => { if (view.model && view.model.main) go(mainView(), true); });
    $("timeline-all").addEventListener("click", () => { if (view.model && view.model.range) go(allView(), true); });
    $("timeline-search").addEventListener("input", (event) => { view.query = event.target.value.trim().toLowerCase(); refilter(); layout(); schedule(); });
    $("timeline-key-only").addEventListener("change", (event) => { view.keyOnly = event.target.checked; list(); });
    if (typeof ResizeObserver === "function") new ResizeObserver(() => measure()).observe(host);
  }
  function measure() {
    const width = Math.floor($("timeline-host").clientWidth);
    if (!width || width === view.width) return;
    view.width = width;
    layout();
    draw();
  }

  CONAN.timeline = {
    /** A case was opened or re-read. The view is kept while the same case is on screen. */
    render(model, name) {
      if (model === view.model && name === view.name) return;
      const fresh = name !== view.name || !view.span;
      view.model = model; view.name = name; view.selected = null;
      if (fresh) { view.off = new Set(); view.query = ""; $("timeline-search").value = ""; }
      chips(); refilter();
      const start = fresh && model ? mainView() : null;
      if (start) { view.t0 = start.t0; view.span = start.span; }
      if (!model || !model.range) view.span = 0;
      layout(); draw();
    },
    activate() { measure(); schedule(); },
    /** Open the timeline at a stretch of time, optionally with one kind of activity or one record chosen. */
    show(options = {}) {
      if (!view.model) return;
      if (CONAN.app) CONAN.app.switchTab("timeline");
      const wanted = options.lane !== undefined ? new Set(LANES.map((lane, index) => index).filter((index) => index !== options.lane)) : null;
      if (wanted) view.off = wanted;
      if (options.select) view.off.delete(options.select.lane);
      if (wanted || options.select) { view.query = ""; $("timeline-search").value = ""; chips(); refilter(); layout(); }
      measure();
      if (options.from !== undefined && options.to !== undefined) go(around(options.from, options.to), true);
      else if (wanted) go(mainView() || view, true);
      if (options.select) select(options.select); else schedule();
    },
  };
  wire();
})();
