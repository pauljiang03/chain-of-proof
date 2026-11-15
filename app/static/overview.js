/* CONAN-F summary: what the records behind the verified findings show, in plain sentences.
   The server writes the sentences from those records alone. This page adds no finding of its own. */
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
  const state = { model: null, narrative: null, painted: false };

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
    host.append(hero, box);
  }

  CONAN.overview = {
    render(model, run, brief, evidence, narrative) {
      if (state.painted && model === state.model) return;   // the same stored run: nothing to redraw
      state.model = model; state.narrative = narrative; state.painted = true;
      paint();
    },
    activate() { /* nothing here is drawn to measure */ },
  };
})();
