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
  const DEVICE = [["record", "Record"], ["item", "Source"], ["device", "Recorded name"], ["serial", "USB identifier"],
    ["volume", "Volume serial"], ["recorded_time", "Record timestamp"]];
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
    const refusalsSupplied = Array.isArray(run.rejections), refused = array(run.rejections).length, items = array(state.brief && state.brief.exhibits);
    const exhibits = items.length ? items.map((item) => String(item.label))
      : [...new Set(model.records.map((record) => record.exhibit).filter(Boolean))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
    row.append(
      tile("Recorded accepted findings", n.format(findings.length), n.format(direct) + " without heuristics · " + n.format(heuristic) + " with heuristics"
        + (other ? " · " + n.format(other) + " not specified" : ""), go("findings")),
      tile("Recorded refusals", refusalsSupplied ? n.format(refused) : "Not supplied", refused ? "Not shown as findings" : "No refusal entries supplied"),
      tile("Distinct cited records", n.format(model.records.length), n.format(model.events.length) + " carry a source timestamp", () => CONAN.timeline && CONAN.timeline.show({})),
      tile("Recorded exhibit labels", n.format(exhibits.length), exhibits.length ? S.clip(exhibits.join(", "), 44) : "No exhibit named in the records"));
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

  // Evidence examined: each item the records name, with the identifiers and hash values that are themselves cited records.
  function evidence(items, brief) {
    const S = CONAN.story, n = S.number, box = card("Evidence examined", "Items named by the evidence records");
    const text = (value) => (typeof value === "string" ? value : "");
    if (!items.length) { box.append(el("p", "card-foot", "The evidence records name no examined item.")); return box; }
    const most = Math.max(1, ...items.map((item) => Number(item.records) || 0));
    items.forEach((item) => {
      const row = el("div", "ov-item"), head = el("div", "item-head"), track = el("span", "bar-track"), fill = el("span", "bar-fill");
      const label = text(item.label), count = Number(item.records) || 0;
      head.append(el("strong", "", label), el("span", "item-image", array(item.images).map(text).join(", ")),
        el("span", "item-count", n.format(count) + (count === 1 ? " record · " : " records · ") + n.format(Number(item.findings) || 0) + " findings"));
      fill.style.width = Math.max(0.6, (count / most) * 100) + "%";
      track.append(fill);
      row.append(head, track);
      const identity = array(item.devices).map(text).filter(Boolean).map((value) => "Device " + value)
        .concat(array(item.volumes).map(text).filter(Boolean).map((value) => "Volume serial " + value),
          array(item.system).map((fact) => text(fact && fact.label) + ": " + array(fact && fact.values).map(text).join(", ")));
      if (identity.length) row.append(el("p", "item-facts", identity.join(" · ")));
      const digests = array(item.digests).filter((digest) => digest && text(digest.value));
      if (digests.length) {
        const line = el("p", "item-hash");
        digests.forEach((digest, index) => {
          const value = text(digest.value), mark = el("span", "", text(digest.algorithm) + " " + (value.length > 20 ? value.slice(0, 8) + "…" + value.slice(-8) : value));
          mark.title = text(digest.algorithm) + " " + value + (text(digest.stored_by) ? " — stored by " + text(digest.stored_by) : "");
          if (index) line.append(" · ");
          line.append(mark);
        });
        row.append(line);
      }
      box.append(row);
    });
    const loose = Number(brief.unlabelled) || 0;
    if (loose) box.append(el("p", "card-foot", n.format(loose) + (loose === 1 ? " record names" : " records name") + " no item."));
    return box;
  }

  function statistics(model) {
    const S = CONAN.story, info = state.brief || {}, split = el("div", "ov-split");
    const kinds = card("Evidence types", "Cited records by category"), top = Math.max(1, ...model.lanes.map((lane) => lane.records));
    model.lanes.map((lane, index) => ({ index, ...lane })).filter((lane) => lane.records).sort((a, b) => b.records - a.records)
      .forEach((lane) => kinds.append(barRow(lane.index, S.LANES[lane.index].name, lane.records, top,
        "Show dated " + S.LANES[lane.index].name + " records on the Timeline",
        lane.events ? () => CONAN.timeline.show({ lane: lane.index }) : null)));
    kinds.append(el("p", "card-foot", S.number.format(model.events.length) + " records carry a source timestamp; "
      + S.number.format(model.undatedCount) + " have no event time. Counts refer to records, which can describe the same event."));
    split.append(kinds, evidence(array(info.exhibits), info));
    return split;
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
      empty.append(el("h3", "", found ? "No supported summary for these record types" : "No findings have passed the checker yet"),
        el("p", "", found ? "Open Findings to read the exact statements and cited records." : "This page fills in as findings are accepted."));
      host.append(empty);
      if (model) host.append(tiles(model));
      if (found) host.append(statistics(model));
      return;
    }
    const hero = el("header", "ov-hero"), box = el("section", "card key-findings");
    hero.append(el("h2", "", "Overview"));
    const lead = array(story.lead).map(String).join(" ");
    if (lead) hero.append(el("p", "ov-lead", lead));
    const overview = story.investigator_overview;
    if (overview && overview.status === "unverified" && typeof overview.text === "string") {
      const interpretation = card("Investigator overview (unverified)", "");
      interpretation.append(el("p", "ov-lead exact-value", overview.text));
      hero.append(interpretation);
    }
    points.forEach((point) => {
      const row = el("div", "key-row"), body = el("div", "key-body");
      body.append(el("p", "", array(point.sentences).map(String).join(" ")));
      if (point.key === "devices" && array(story.devices).length) body.append(devices(array(story.devices)));
      row.append(el("h3", "", String(point.title)), body);
      box.append(row);
    });
    host.append(hero, box, tiles(model), statistics(model));
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
