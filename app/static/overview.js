/* CONAN-F summary: what the records behind the verified findings show, in plain sentences,
   then the counts of the run. The server writes the sentences from those records alone.
   This page adds no finding of its own. */
(() => {
  "use strict";
  const CONAN = (window.CONAN = window.CONAN || {});
  const $ = (id) => document.getElementById(id);
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  };
  const array = (value) => (Array.isArray(value) ? value : []);
  const clip = (value, max) => (value.length > max ? value.slice(0, max - 1) + "…" : value);
  const DEVICE = [["item", "Item"], ["device", "Device"], ["serial", "Serial number"], ["label", "Volume label"],
    ["first", "First connection"], ["last", "Last connection"]];
  const state = { model: null, run: null, brief: null, narrative: null, painted: false };
  const go = (tab) => () => { if (CONAN.app) CONAN.app.switchTab(tab, true); };

  function tile(label, value, note, action) {
    const box = el(action ? "button" : "div", "tile");
    if (action) { box.type = "button"; box.addEventListener("click", action); }
    box.append(el("span", "tile-label", label), el("span", "tile-value", value), el("span", "tile-note", note));
    return box;
  }
  // The counts of the run. A tile that leads somewhere opens the tab that shows what it counts.
  function tiles(model) {
    const S = CONAN.story, n = S.number, run = state.run || {}, findings = model.findings, row = el("div", "ov-tiles");
    const direct = findings.filter((finding) => finding.strength === "strong").length;
    const heuristic = findings.filter((finding) => finding.strength === "heuristic").length, other = findings.length - direct - heuristic;
    const refused = array(run.rejections).length, items = array(state.brief && state.brief.exhibits);
    const exhibits = items.length ? items.map((item) => String(item.label))
      : [...new Set(model.records.map((record) => record.exhibit).filter(Boolean))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
    row.append(
      tile("Findings that passed", n.format(findings.length), n.format(direct) + " without heuristics · " + n.format(heuristic) + " with heuristics"
        + (other ? " · " + n.format(other) + " not specified" : ""), go("findings")),
      tile("Refused by the checker", n.format(refused), refused ? "Not shown as findings" : "Nothing was refused in this run"),
      tile("Evidence records used", n.format(model.records.length), n.format(model.events.length) + " carry a source timestamp", () => CONAN.timeline && CONAN.timeline.show({})),
      tile("Evidence exhibits", n.format(exhibits.length), exhibits.length ? S.clip(exhibits.join(", "), 44) : "No exhibit named in the records"));
    if (model.main) {
      const days = Math.floor(S.wall(model.main.to) / S.DAY) - Math.floor(S.wall(model.main.from) / S.DAY) + 1, same = days === 1;
      const first = new Date(S.wall(model.main.from)), last = new Date(S.wall(model.main.to));
      const month = first.getUTCFullYear() === last.getUTCFullYear() && first.getUTCMonth() === last.getUTCMonth();
      row.append(tile("Busiest period", same ? S.F.short.format(model.main.from) : month ? first.getUTCDate() + "–" + S.F.short.format(model.main.to)
        : S.F.short.format(model.main.from) + " – " + S.F.short.format(model.main.to),
      S.F.year.format(model.main.to) + " · " + n.format(model.main.count) + " records in " + n.format(days) + (same ? " day" : " days"),
      () => CONAN.timeline && CONAN.timeline.show({ from: model.main.from, to: model.main.to })));
    }
    return row;
  }

  function devices(list) {
    const table = el("table", "key-table"), top = el("thead"), head = el("tr"), rows = el("tbody");
    DEVICE.forEach(([, name]) => { const cell = el("th", "", name); cell.scope = "col"; head.append(cell); });
    list.forEach((device) => {
      const line = el("tr");
      DEVICE.forEach(([key]) => line.append(el("td", "", clip(String((device && device[key]) || "—"), 60))));
      rows.append(line);
    });
    top.append(head);
    table.append(top, rows);
    return table;
  }

  function paint() {
    const host = $("overview"), model = state.model, story = state.narrative;
    host.replaceChildren();
    const found = Boolean(model && model.findings.length);
    const points = array(story && story.points).filter((point) => point && array(point.sentences).length);
    if (!found || !points.length) {
      const empty = el("div", "empty-state");
      empty.append(el("h3", "", found ? "No key findings to show" : "No findings have passed the checker yet"),
        el("p", "", found ? "Open Findings to read what was verified." : "This page fills in as findings are accepted."));
      host.append(empty);
      return;
    }
    const hero = el("header", "ov-hero"), box = el("section", "card key-findings");
    hero.append(el("h2", "", "Key findings"));
    points.forEach((point) => {
      const row = el("div", "key-row"), body = el("div", "key-body");
      body.append(el("p", "", array(point.sentences).map(String).join(" ")));
      if (point.key === "devices" && array(story.devices).length) body.append(devices(array(story.devices)));
      row.append(el("h3", "", String(point.title)), body);
      box.append(row);
    });
    host.append(hero, box, tiles(model));
  }

  CONAN.overview = {
    render(model, run, brief, evidence, narrative) {
      if (state.painted && model === state.model) return;   // the same stored run: nothing to redraw
      state.model = model; state.run = run; state.brief = brief; state.narrative = narrative; state.painted = true;
      paint();
    },
    activate() { /* nothing here is drawn to measure */ },
  };
})();
