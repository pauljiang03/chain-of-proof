/* CONAN-F summary: the case at a glance, in numbers and pictures rather than paragraphs.
   It counts and draws what the stored run holds. It adds no finding of its own. */
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
  const state = { model: null, run: null, range: "main", bins: null, hot: -1, painted: false };
  const go = (tab) => () => { if (CONAN.app) CONAN.app.switchTab(tab, true); };

  // Whole hours, days, weeks, months or years: the finest step that keeps the chart to about 130 columns.
  function edges(from, to) {
    const S = CONAN.story;
    for (const [size, name] of [[S.HOUR, "hour"], [3 * S.HOUR, "3 hours"], [6 * S.HOUR, "6 hours"], [S.DAY, "day"], [7 * S.DAY, "week"]]) {
      const a = Math.floor(from / size) * size, b = Math.floor(to / size) * size + size;
      if ((b - a) / size > 130) continue;
      const list = [];
      for (let t = a; t <= b; t += size) list.push(t);
      return { list, name };
    }
    for (const [months, name] of [[1, "month"], [3, "quarter"], [12, "year"], [60, "5 years"], [120, "10 years"]]) {
      const first = new Date(from), list = [];
      for (let k = Math.floor((first.getUTCFullYear() * 12 + first.getUTCMonth()) / months) * months; ; k += months) {
        const t = Date.UTC(Math.floor(k / 12), ((k % 12) + 12) % 12, 1);
        list.push(t);
        if (t > to || list.length > 400) break;
      }
      if (list.length <= 131 || months === 120) return { list, name };
    }
    return { list: [from, to], name: "period" };
  }
  function nice(max) {
    if (max <= 4) return Math.max(1, max);
    const power = Math.pow(10, Math.floor(Math.log10(max))), lead = max / power;
    return (lead <= 1 ? 1 : lead <= 2 ? 2 : lead <= 5 ? 5 : 10) * power;
  }
  function when(bin) {
    const S = CONAN.story, F = S.F, a = state.bins.list[bin], b = state.bins.list[bin + 1], name = state.bins.name;
    if (name === "hour" || name === "3 hours" || name === "6 hours") return F.day.format(a) + ", " + F.clock.format(a) + "–" + F.clock.format(b) + " UTC";
    if (name === "day") return F.day.format(a) + " (UTC)";
    if (name === "week") return F.day.format(a) + " – " + F.day.format(b - S.DAY);
    if (name === "month") return F.month.format(a);
    if (name === "quarter") return F.month.format(a) + " – " + F.month.format(b - S.DAY);
    return name === "year" ? F.year.format(a) : F.year.format(a) + "–" + F.year.format(b - S.DAY);
  }

  function tile(label, value, note, action) {
    const box = el(action ? "button" : "div", "tile");
    if (action) { box.type = "button"; box.addEventListener("click", action); }
    box.append(el("span", "tile-label", label), el("span", "tile-value", value), el("span", "tile-note", note));
    return box;
  }
  function card(title, note, extra) {
    const box = el("section", "card"), head = el("div", "card-head");
    head.append(el("h3", "", title), el("p", "", note));
    if (extra) head.append(el("span", "spacer"), extra);
    box.append(head);
    return box;
  }
  function barRow(lane, name, value, max, title, action) {
    const row = el(action ? "button" : "div", "bar-row"), label = el("span", "bar-name"), track = el("span", "bar-track"), fill = el("span", "bar-fill" + (lane === null ? "" : " c" + lane));
    if (action) { row.type = "button"; row.addEventListener("click", action); row.title = title; }
    if (lane !== null) label.append(CONAN.story.dot(lane));
    label.append(name);
    fill.style.width = (max ? Math.max(0.6, (value / max) * 100) : 0) + "%";
    track.append(fill);
    row.append(label, track, el("span", "bar-value", CONAN.story.number.format(value)));
    return row;
  }

  function paint() {
    const host = $("overview"), model = state.model, S = CONAN.story;
    host.replaceChildren();
    state.bins = null;
    if (!S || !model || !model.findings.length) {
      const empty = el("div", "empty-state");
      empty.append(el("h3", "", "No findings have passed the checker yet"), el("p", "", "This page fills in as findings are accepted. Refused proposals are listed under Not established."));
      host.append(empty);
      return;
    }
    const n = S.number, run = state.run || {}, findings = model.findings, firm = findings.filter((finding) => finding.strength !== "heuristic").length;
    const refused = array(run.rejections).length, opinions = array(run.conclusions).length, dated = model.events.length;
    const exhibits = new Map();
    model.records.forEach((record) => { const item = exhibits.get(record.exhibit) || { count: 0, image: record.image }; item.count += 1; exhibits.set(record.exhibit, item); });
    const devices = [...exhibits.keys()].filter(Boolean).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

    const hero = el("header", "ov-hero");
    hero.append(el("h2", "", n.format(findings.length) + (findings.length === 1 ? " finding passed the proof checker" : " findings passed the proof checker")),
      el("p", "", "Each one is tied to records read from the disk images. Anything the checker refused is kept apart and never shown as a finding."));

    const tiles = el("div", "ov-tiles");
    tiles.append(
      tile("Findings that passed", n.format(findings.length), n.format(firm) + " firm · " + n.format(findings.length - firm) + " likely (rule of thumb)", go("findings")),
      tile("Refused by the checker", n.format(refused), refused ? "Listed under Not established" : "Nothing was refused in this run", go("needs")),
      tile("Evidence records used", n.format(model.records.length), n.format(dated) + " carry an event time", () => CONAN.timeline && CONAN.timeline.show({})),
      tile("Devices examined", n.format(devices.length), devices.length ? S.clip(devices.join(", "), 44) : "No device named in the records"));
    if (model.main) {
      const days = Math.floor(model.main.to / S.DAY) - Math.floor(model.main.from / S.DAY) + 1, same = days === 1;
      const first = new Date(model.main.from), last = new Date(model.main.to), month = first.getUTCFullYear() === last.getUTCFullYear() && first.getUTCMonth() === last.getUTCMonth();
      tiles.append(tile("Busiest period", same ? S.F.short.format(model.main.from) : month ? first.getUTCDate() + "–" + S.F.short.format(model.main.to) : S.F.short.format(model.main.from) + " – " + S.F.short.format(model.main.to),
        S.F.year.format(model.main.to) + " · " + n.format(model.main.count) + " records in " + n.format(days) + (same ? " day" : " days"),
        () => CONAN.timeline && CONAN.timeline.show({ from: model.main.from, to: model.main.to })));
    }
    host.append(hero, tiles);
    if (opinions) host.append(el("p", "ov-note", n.format(opinions) + (opinions === 1 ? " interpretation by the investigator is" : " interpretations by the investigator are") + " recorded as not checked. They are under Findings, never counted above."));

    if (model.range) {
      const pick = el("span", "segmented");
      [["main", "Busiest period"], ["all", "All dates"]].forEach(([key, label]) => {
        const button = el("button", "", label);
        button.type = "button";
        button.setAttribute("aria-pressed", String(state.range === key));
        button.addEventListener("click", () => { state.range = key; pick.querySelectorAll("button").forEach((other) => other.setAttribute("aria-pressed", String(other === button))); chart(); });
        pick.append(button);
      });
      const timing = card("When it happened", "", pick), chartHost = el("div", "chart-host");
      timing.querySelector(".card-head p").id = "ov-when-note";
      chartHost.id = "ov-when";
      chartHost.append(svg("svg", { class: "chart", id: "ov-when-chart", role: "img", "aria-label": "Evidence records over time" }), Object.assign(el("div", "chart-tip"), { id: "ov-when-tip", hidden: true }));
      timing.append(chartHost, el("p", "card-foot", "Click a column to open that stretch of time in the Timeline."));
      host.append(timing);
      chartHost.addEventListener("pointermove", point);
      chartHost.addEventListener("pointerleave", () => { $("ov-when-tip").hidden = true; light(-1); });
      chartHost.addEventListener("click", (event) => { const bin = binAt(event); if (bin >= 0 && state.bins.counts[bin]) CONAN.timeline.show({ from: state.bins.list[bin], to: state.bins.list[bin + 1] }); });
      if (typeof ResizeObserver === "function") new ResizeObserver(() => chart()).observe(chartHost);
    }

    const split = el("div", "ov-split");
    const kinds = card("What kind of activity", "Evidence records by kind"), top = Math.max(...model.lanes.map((lane) => lane.records));
    model.lanes.map((lane, index) => ({ index, ...lane })).filter((lane) => lane.records).sort((a, b) => b.records - a.records)
      .forEach((lane) => kinds.append(barRow(lane.index, S.LANES[lane.index].name, lane.records, top, "Show " + S.LANES[lane.index].name + " on the Timeline",
        lane.events ? () => CONAN.timeline.show({ lane: lane.index }) : null)));
    const sources = card("Where the records came from", "Evidence records by examined device"), most = Math.max(...[...exhibits.values()].map((item) => item.count));
    [...exhibits.entries()].sort((a, b) => b[1].count - a[1].count)
      .forEach(([name, item]) => sources.append(barRow(null, name ? name + (item.image ? " · " + S.clip(item.image, 22) : "") : "Not tied to one device", item.count, most)));
    split.append(kinds, sources);
    host.append(split);

    if (model.main) host.append(days());

    const how = el("div", "how");
    [["1", "Tools read the disk images into records"], ["2", "The AI investigator proposes findings"], ["3", "The proof checker keeps only what the records support"]].forEach(([step, text], index) => {
      if (index) how.append(el("span", "how-arrow", "→"));
      const item = el("span", "how-step");
      item.append(el("b", "", step), text);
      how.append(item);
    });
    host.append(how);
    chart();
  }

  // Day by day: for each day of the busiest period, the mix of activity and the key events.
  function days() {
    const S = CONAN.story, model = state.model, n = S.number, byDay = new Map();
    const a = S.lower(model.times, model.main.from), b = S.lower(model.times, model.main.to + 1);
    for (let i = a; i < b; i += 1) {
      const record = model.events[i], key = Math.floor(record.ms / S.DAY);
      let day = byDay.get(key);
      if (!day) byDay.set(key, (day = { key, total: 0, lanes: S.LANES.map(() => 0), kinds: new Map() }));
      day.total += 1; day.lanes[record.lane] += 1;
      if (!record.marked) continue;
      const group = day.kinds.get(record.kind);
      if (group) { group.count += 1; group.to = record.ms; } else day.kinds.set(record.kind, { first: record, count: 1, from: record.ms, to: record.ms });
    }
    let list = [...byDay.values()];
    const all = list.length;
    if (all > 8) list = list.sort((x, y) => y.total - x.total).slice(0, 8);
    list.sort((x, y) => x.key - y.key);
    const box = card("Day by day", all > list.length ? "The " + list.length + " busiest of " + all + " days · UTC" : "Key events of the busiest period · UTC"), grid = el("div", "days");
    list.forEach((day) => {
      const item = el("article", "day"), head = el("div", "day-head"), mix = el("div", "mix");
      head.append(el("h4", "", S.F.day.format(day.key * S.DAY)), el("span", "day-count", n.format(day.total) + " records"));
      mix.setAttribute("role", "img");
      mix.setAttribute("aria-label", day.lanes.map((count, lane) => (count ? S.LANES[lane].name + " " + count : "")).filter(Boolean).join(", "));
      day.lanes.forEach((count, lane) => { if (!count) return; const part = el("i", "c" + lane); part.style.flexGrow = String(count); part.title = S.LANES[lane].name + ": " + n.format(count); mix.append(part); });
      item.append(head, mix);
      const groups = [...day.kinds.values()].sort((x, y) => x.from - y.from);
      if (!groups.length) item.append(el("p", "day-none", "No key events on this day."));
      groups.forEach((group) => {
        const row = el("button", "day-row"), text = el("span", "day-what"), record = group.first;
        row.type = "button";
        row.title = "Open on the Timeline";
        text.append(el("strong", "", group.count === 1 ? record.one : n.format(group.count) + " " + record.many), el("small", "", (group.count === 1 ? "" : "first: ") + S.clip(record.obj, 60)));
        row.append(S.dot(record.lane), text, el("span", "day-time", S.F.clock.format(group.from) + (group.to - group.from >= S.MINUTE ? "–" + S.F.clock.format(group.to) : "")));
        row.addEventListener("click", () => CONAN.timeline.show({ from: group.from, to: group.to, select: record }));
        item.append(row);
      });
      grid.append(item);
    });
    box.append(grid, el("p", "card-foot", "Key events are picked by record type — a device connection, an e-mail, a deletion — not by AI judgment. Every other record is on the Timeline."));
    return box;
  }

  // ---- "When it happened": records per step of time ---------------------------
  const M = { left: 46, right: 10, top: 10, bottom: 40 }, HEIGHT = 210;
  function chart() {
    const host = $("ov-when"), model = state.model, S = CONAN.story;
    if (!host || !model || !model.range) return;
    const width = Math.floor(host.clientWidth);
    if (!width) return;
    const span = state.range === "main" && model.main ? model.main : model.range, bins = edges(span.from, span.to), root = $("ov-when-chart");
    bins.counts = bins.list.slice(0, -1).map((edge, i) => S.lower(model.times, bins.list[i + 1]) - S.lower(model.times, edge));
    bins.width = width;
    state.bins = bins;
    state.hot = -1;
    const plot = width - M.left - M.right, tall = HEIGHT - M.top - M.bottom, top = nice(Math.max(1, ...bins.counts)), step = plot / bins.counts.length;
    const from = bins.list[0], total = bins.list[bins.list.length - 1] - from, x = (t) => M.left + ((t - from) / total) * plot;
    root.setAttribute("width", width); root.setAttribute("height", HEIGHT); root.setAttribute("viewBox", "0 0 " + width + " " + HEIGHT);
    const parts = [];
    [0, top / 2, top].forEach((value) => {
      const y = M.top + tall - (value / top) * tall;
      parts.push(svg("line", { class: "grid", x1: M.left, x2: width - M.right, y1: y, y2: y }), svg("text", { class: "axis-label end", x: M.left - 8, y: y + 4 }, S.number.format(value)));
    });
    const marks = S.ticks(from, total, plot);
    marks.list.forEach((mark) => {
      parts.push(svg("line", { class: "tick", x1: x(mark.t), x2: x(mark.t), y1: M.top + tall, y2: M.top + tall + 5 }), svg("text", { class: "axis-label", x: x(mark.t), y: M.top + tall + 18 }, mark.label));
      if (mark.sub && x(mark.t) > M.left + 110) parts.push(svg("text", { class: "axis-label major", x: x(mark.t), y: M.top + tall + 34 }, mark.sub));
    });
    if (marks.context) parts.push(svg("text", { class: "axis-label major start", x: M.left, y: M.top + tall + 34 }, marks.context));
    const gap = step >= 6 ? 2 : step >= 3 ? 1 : 0, bar = Math.max(1, step - gap);
    bins.bars = bins.counts.map((count, i) => {
      if (!count) return null;
      const h = Math.max(2, (count / top) * tall), left = M.left + i * step + gap / 2, r = Math.min(4, bar / 2, h), base = M.top + tall;
      const node = svg("path", { class: "bar", d: "M" + left + " " + base + "v" + (r - h) + "q0 " + -r + " " + r + " " + -r + "h" + (bar - 2 * r) + "q" + r + " 0 " + r + " " + r + "v" + (h - r) + "z" });
      parts.push(node);
      return node;
    });
    root.replaceChildren(...parts);
    $("ov-when-note").textContent = "Evidence records per " + bins.name + " · " + (state.range === "main" && model.main ? "busiest period" : "all dates") + " · UTC";
  }
  function binAt(event) {
    const bins = state.bins, host = $("ov-when");
    if (!bins || !host) return -1;
    const box = host.getBoundingClientRect(), px = event.clientX - box.left, plot = bins.width - M.left - M.right;
    const index = Math.floor(((px - M.left) / plot) * bins.counts.length);
    return index >= 0 && index < bins.counts.length ? index : -1;
  }
  function light(bin) {
    const bins = state.bins;
    if (!bins || bin === state.hot) return;
    if (bins.bars[state.hot]) bins.bars[state.hot].classList.remove("hot");
    if (bins.bars[bin]) bins.bars[bin].classList.add("hot");
    state.hot = bin;
  }
  function point(event) {
    const bin = binAt(event), tip = $("ov-when-tip"), bins = state.bins, S = CONAN.story, model = state.model;
    light(bin);
    if (bin < 0 || !bins.counts[bin]) { tip.hidden = true; return; }
    const a = S.lower(model.times, bins.list[bin]), b = S.lower(model.times, bins.list[bin + 1]), lanes = S.LANES.map(() => 0);
    for (let i = a; i < b; i += 1) lanes[model.events[i].lane] += 1;
    tip.replaceChildren(el("strong", "", when(bin)), el("div", "tip-total", S.number.format(b - a) + (b - a === 1 ? " record" : " records")));
    lanes.map((count, lane) => ({ count, lane })).filter((item) => item.count).sort((x, y) => y.count - x.count).slice(0, 4).forEach((item) => {
      const line = el("div", "tip-line");
      line.append(S.dot(item.lane), el("span", "", S.LANES[item.lane].name), el("span", "tip-count", S.number.format(item.count)));
      tip.append(line);
    });
    tip.hidden = false;
    const box = $("ov-when").getBoundingClientRect(), px = event.clientX - box.left;
    tip.style.left = Math.max(4, Math.min(box.width - tip.offsetWidth - 4, px + 14)) + "px";
    tip.style.top = Math.max(0, event.clientY - box.top - tip.offsetHeight - 10) + "px";
  }

  function wire() { /* the page is built when a case is rendered */ }
  CONAN.overview = {
    render(model, run) {
      if (state.painted && model === state.model) return;   // the same stored run: nothing to redraw
      state.model = model; state.run = run; state.range = "main"; state.painted = true;
      paint();
    },
    activate() { chart(); },
  };
  wire();
})();
