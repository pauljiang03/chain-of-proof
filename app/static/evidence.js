/* Readable evidence browsing. Groups copied records for navigation, never invents a claim.
   Every displayed property retains its own record and every finding remains verbatim. */
(() => {
  "use strict";
  const CONAN = (window.CONAN = window.CONAN || {});
  const array = value => Array.isArray(value) ? value : [];
  const object = value => value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const text = value => value === undefined || value === null || value === "(none)" ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
  const stable = value => value && typeof value === "object" ? Array.isArray(value) ? "[" + value.map(stable).join(",") + "]" : "{" + Object.keys(value).sort().map(key => JSON.stringify(key) + ":" + stable(value[key])).join(",") + "}" : JSON.stringify(value);
  const basename = value => text(value).split(/[\\/]/).filter(Boolean).pop() || text(value);
  const categories = [
    {key: "devices", label: "Devices & volumes", lane: 0}, {key: "files", label: "Files & folders", lane: 1},
    {key: "web", label: "Web & searches", lane: 2}, {key: "messages", label: "Messages & cloud", lane: 3},
    {key: "programs", label: "Programs", lane: 4}, {key: "accounts", label: "Accounts & sign-ins", lane: 5},
    {key: "system", label: "Computer & notes", lane: 6}, {key: "other", label: "Other records", lane: 7},
  ];
  // Category, readable source type, object label, related-value label.
  const types = {
    usbInsert: ["devices", "USB connection", "Device serial", "Related value"],
    volumeMount: ["devices", "Volume mount", "Device serial", "Volume serial"],
    volumeOnDevice: ["devices", "Examined volume", "Device serial", "Volume serial"],
    volumeSeen: ["devices", "Recorded volume", "Volume serial", "Volume label"],
    volumeRecorded: ["devices", "Volume descriptor", "Device", "Volume serial"],
    unallocatedOnDevice: ["devices", "Unallocated space", "Device serial", "Storage"],
    cdBurn: ["devices", "Optical-disc trace", "Trace", "Device / detail"],
    fileCreated: ["files", "Created", "Path", "Volume / storage"],
    fileModified: ["files", "Modified", "Path", "Volume / storage"],
    fileDeleted: ["files", "Recycle Bin record", "Path", "Volume / storage"],
    fileRenamed: ["files", "Renamed", "Original path", "New path"],
    fileSeen: ["files", "File inventory", "Path", "Volume / storage"],
    fileContent: ["files", "Content digest", "Path", "Recorded digest"],
    fileRemoved: ["files", "Removal flag", "Path", "Volume / storage"],
    fileCreationRecorded: ["files", "Creation flag", "Path", "Volume / storage"],
    lnkTarget: ["files", "Shortcut target", "Target path", "Volume / share"],
    folderOpened: ["files", "Folder record", "Folder", "Related value"],
    journalName: ["files", "Journal name", "File identity", "Recorded name"],
    journalPath: ["files", "Journal path", "File identity", "Recorded path"],
    journalRemoval: ["files", "Journal removal flag", "File identity", "Recorded name"],
    webVisit: ["web", "Page visit", "URL", "Browser"],
    webSearch: ["web", "Search query", "Search", "Browser"],
    localSearch: ["web", "Computer search", "Search", "Search location"],
    fileDownloaded: ["web", "Download", "Downloaded file", "Source URL"],
    emailSent: ["messages", "Email", "Subject", "Participants"],
    cloudFile: ["messages", "Cloud record", "File", "Recorded activity"],
    programRun: ["programs", "Application artifact", "Application", "Path"],
    programInstalled: ["programs", "Software registration", "Application", "Version"],
    accountSeen: ["accounts", "Account record", "Account", "Account type"],
    sessionEvent: ["accounts", "Sign-in / session", "Event", "Account"],
    systemSetting: ["system", "Computer property", "Property", "Value"],
    shadowCopy: ["system", "Backup snapshot", "Snapshot", "Volume"],
    noteText: ["system", "Note", "File", "Note text"],
    tag: ["other", "Recorded label", "Subject", "Label"],
  };
  const spec = row => types[text(row.kind)] || ["other", text(row.kind) || "Record", "Subject", "Value"];
  function deviceName(value) {
    const match = text(value).match(/Ven_([^&]+)&Prod_([^&]+)/i);
    return match ? (match[1] + " " + match[2]).replace(/_/g, " ") : text(value);
  }
  function domain(value) { try { const url = new URL(value); return /^https?:$/.test(url.protocol) ? url.hostname : ""; } catch (_) { return ""; } }
  function scope(row) {
    const p = object(row.prov);
    return [p.exhibit, p.image, p.snapshot_id, p.user || p.mailbox_user, p.subject_scope, p.volume_identity].map(text);
  }
  function entity(row) {
    const p = object(row.prov), type = spec(row), obj = text(row.obj_text), aux = text(row.aux_text);
    let identity = obj || "record:" + stable(row), title = obj || type[1], family = type[0];
    if (row.kind === "webVisit" && domain(obj)) { identity = domain(obj); title = identity; family = "website"; }
    else if (type[0] === "web") { family = row.kind; if (row.kind === "fileDownloaded") title = basename(obj); }
    else if (type[0] === "files" || row.kind === "noteText" || row.kind === "cloudFile") title = basename(obj);
    else if (["usbInsert", "volumeMount", "volumeOnDevice", "unallocatedOnDevice"].includes(row.kind)) { family = "device"; title = deviceName(p.device) || obj; }
    else if (row.kind === "systemSetting") { family = row.kind; title = aux || obj; }
    else if (row.kind === "sessionEvent") { family = row.kind; identity = stable([obj, aux]); }
    else if (type[0] === "messages") { family = row.kind; identity = stable([obj, p.message_id || p.artifact || "", aux]); }
    else if (type[0] === "other") family = row.kind;
    return {key: stable([family, identity, ...scope(row)]), title, category: type[0]};
  }
  function time(row) {
    if (!Number.isSafeInteger(row.t) || row.t <= 0) return "";
    const p = object(row.prov), meaning = text(p.time_meaning), semantics = text(p.timestamp_semantics);
    if (semantics === "examination_observation" || /\bwhen (?:the image|this source attribute) was examined\b/i.test(meaning)) return "";
    if (!["journal_observation", "destlist_entry_update"].includes(semantics) && (!meaning || /^(unknown|unspecified|not recorded|unavailable|none|n\/a)\b/i.test(meaning))) return "";
    const date = new Date(row.t / 1000);
    if (!Number.isFinite(date.getTime())) return "";
    const S = CONAN.story;
    return S ? S.F.full.format(date) + " · " + (S.zone.local ? S.zone.name : "UTC") : date.toISOString();
  }
  function properties(row) {
    const p = object(row.prov), type = spec(row), values = [];
    const add = (label, value) => { const v = text(value); if (v !== "") values.push({label, value: v}); };
    add(type[2], row.obj_text); add(type[3], row.aux_text);
    for (const [key, label] of [
      ["device", "Device model"], ["volume_label", "Volume label"], ["drive_letter", "Drive letter"], ["filesystem", "File system"],
      ["user", "User named in record"], ["sender_address", "Sender"], ["recipient_address", "Recipient"],
      ["attachment_names", "Attachment names"], ["attachments", "Attachment count"], ["mailbox_user", "Mailbox user"],
      ["size", "Size (bytes)"], ["run_count", "Recorded run count"], ["source", "Source type"],
      ["profile_path", "Profile path"], ["groups", "Groups"], ["last_logon", "Last logon as recorded"], ["sid", "Account SID"],
      ["publisher", "Publisher"], ["service", "Service"], ["url", "URL"], ["volume_serial", "Volume serial"],
      ["recovered", "Recovered entry"], ["event", "Event"], ["event_id", "Event ID"], ["stored_by", "Digest origin"],
    ]) if (p[key] !== undefined) add(label, key === "device" ? deviceName(p[key]) : p[key]);
    add("Recorded time", time(row));
    if (time(row)) add("Time meaning", p.time_meaning || p.timestamp_semantics);
    add("Evidence item", p.exhibit); add("Image", p.image); add("Snapshot", p.snapshot_id);
    return values;
  }
  function build(run) {
    const findings = array(object(run).findings).filter(f => object(f).status === "verified"), records = new Map(), groups = new Map();
    findings.forEach((finding, index) => array(finding.cited_facts).forEach(raw => {
      if (raw !== object(raw)) return;
      const key = stable(raw);
      if (!records.has(key)) records.set(key, {row: raw, findings: new Set()});
      records.get(key).findings.add(index);
    }));
    for (const entry of records.values()) {
      const meta = entity(entry.row);
      if (!groups.has(meta.key)) groups.set(meta.key, {...meta, records: [], findings: new Set(), kinds: new Set()});
      const group = groups.get(meta.key);
      group.records.push(entry); group.kinds.add(spec(entry.row)[1]);
      entry.findings.forEach(index => group.findings.add(index));
      const model = deviceName(object(entry.row.prov).device);
      if (model && group.category === "devices") group.title = model;
    }
    const list = [...groups.values()];
    list.forEach(group => {
      group.properties = [];
      const seen = new Set();
      group.records.forEach(entry => properties(entry.row).forEach(property => {
        const key = stable([property.label, property.value]);
        if (!seen.has(key)) { seen.add(key); group.properties.push({...property, entry}); }
      }));
      group.scope = [...new Set(scope(group.records[0].row).filter(Boolean))].join(" · ");
      group.search = [group.title, group.scope, ...group.kinds, ...group.properties.map(p => p.label + " " + p.value),
        ...[...group.findings].map(i => text(findings[i].finding_id))].join(" ").toLocaleLowerCase();
      // Put explicit identity and changed-file records before bulk inventories, without ranking evidentiary importance.
      group.priority = Math.min(...group.records.map(e => ["computer name", "operating system", "registered owner"].includes(text(e.row.obj_text).toLowerCase()) && e.row.kind === "systemSetting" ? -1 : e.row.kind === "systemSetting" && /^image (md5|sha)/i.test(text(e.row.obj_text)) ? 3 : ["systemSetting", "usbInsert", "volumeMount", "accountSeen", "webSearch", "emailSent", "fileRenamed", "fileDeleted", "lnkTarget", "noteText"].includes(e.row.kind) ? 0 : e.row.kind === "fileSeen" ? 2 : 1));
    });
    list.sort((a,b) => a.priority - b.priority || a.title.localeCompare(b.title, undefined, {numeric: true}) || a.key.localeCompare(b.key));
    return {findings, records: [...records.values()], groups: list};
  }
  function title(finding) {
    const question = text(finding.question).replace(/^Q\d+:\s*/i, "");
    if (question && !/^(combined certified findings|all findings|findings|combined findings)$/i.test(question)) return question;
    const parts = array(finding.parts), rows = array(finding.cited_facts).filter(r => r === object(r));
    const names = [...new Set(rows.map(r => entity(r).title))];
    const kind = Object.keys(object(finding.claim))[0];
    if (kind === "both") return (parts.length || array(finding.claim.both).length) + " related statements" + (names.length ? " · " + names.slice(0, 2).join(" / ") : "");
    if (kind === "before") return "Recorded time order" + (names.length ? " · " + names.slice(0, 2).join(" / ") : "");
    if (kind && kind.startsWith("exactly")) return "Record count · " + (rows[0] ? spec(rows[0])[1] : "evidence");
    return (rows[0] ? spec(rows[0])[1] + " · " + names[0] : "Checked statement");
  }
  const el = (...args) => CONAN.app.element(...args);
  function button(label, action, className="button") {
    const node = el("button", className, label); node.type="button"; node.addEventListener("click", action); return node;
  }
  function recordDetails(entry, model) {
    const row = entry.row, summary = [el("p", "statement", entity(row).title), el("p", "detail-intro", spec(row)[1])];
    const details = el("dl", "entity-properties source-properties");
    properties(row).forEach(property => {
      const pair = el("div");
      pair.append(el("dt", "", property.label), el("dd", "", property.value));
      details.append(pair);
    });
    const links = el("div", "evidence-links");
    entry.findings.forEach(index => { const f = model.findings[index]; links.append(button(text(f.finding_id) + " · exact statement & proof", () => CONAN.app.openFinding(f), "text-button")); });
    const findings = el("details", "entity-details"), source = el("details", "entity-details");
    findings.append(el("summary", "", "Supporting findings (" + entry.findings.size + ")"), links);
    source.append(el("summary", "", "Full source record & provenance"), CONAN.app.recordCard(row));
    CONAN.app.inspect("Source record #" + text(row.id), summary, [details, findings, source], null);
    CONAN.app.switchTab("findings");
  }
  function propertyList(values, model, compact=false) {
    const dl = el("dl", "entity-properties" + (compact ? " compact" : ""));
    values.forEach(p => {
      const pair = el("div"), value = el("dd");
      const source = button(p.value, () => recordDetails(p.entry, model), "property-value");
      source.title = p.value + " — inspect source record #" + text(p.entry.row.id);
      value.append(source); pair.append(el("dt", "", p.label), value); dl.append(pair);
    });
    return dl;
  }
  function previewProperties(group, limit=4) {
    const useful = group.properties.filter(p => !["Image", "Snapshot", "Evidence item", "Time meaning"].includes(p.label)
      && !(p.label === "Source type" && p.value === "deterministic"));
    const labels = new Set(), output = [];
    for (const property of useful) if (!labels.has(property.label)) { labels.add(property.label); output.push(property); }
    const stamp = output.find(p => p.label === "Recorded time");
    return stamp && output.length > limit ? [...output.filter(p => p !== stamp).slice(0, limit - 1), stamp] : output.slice(0, limit);
  }
  function card(group, model) {
    const category = categories.find(c => c.key === group.category), article = el("article", "entity-card c" + category.lane);
    article.append(el("p", "entity-type", [...group.kinds].join(" · ")), el("h3", "", group.title), el("p", "entity-scope", group.scope || "Source item not named"));
    article.append(propertyList(previewProperties(group), model, true));
    const more = el("details", "entity-details"), summary = el("summary", "", "Inspect " + group.records.length + " source record" + (group.records.length === 1 ? "" : "s") + " · " + group.findings.size + " finding" + (group.findings.size === 1 ? "" : "s"));
    more.append(summary);
    more.addEventListener("toggle", () => {
      if (!more.open || more.childElementCount > 1) return;
      const records = el("div", "entity-records");
      let shown = 0;
      const next = button("More source records", () => appendRecords());
      function appendRecords() {
        group.records.slice(shown, shown + 12).forEach(entry => {
          const item = el("details", "entity-record"), p = object(entry.row.prov);
          item.append(el("summary", "", "#" + text(entry.row.id) + " · " + spec(entry.row)[1] + (time(entry.row) ? " · " + time(entry.row) : "")));
          item.addEventListener("toggle", () => { if (item.open && item.childElementCount === 1) {
            item.append(propertyList(properties(entry.row).map(prop => ({...prop, entry})), model), el("p", "entity-scope", text(p.artifact)),
              button("Open full record", () => recordDetails(entry, model), "text-button"));
          }});
          records.append(item);
        });
        shown += 12; next.hidden = shown >= group.records.length;
      }
      appendRecords(); more.append(records, next);
      const claims = el("details", "entity-claims");
      claims.append(el("summary", "", "Exact supporting statements (" + group.findings.size + ")"));
      claims.addEventListener("toggle", () => { if (claims.open && claims.childElementCount === 1) {
        const list = el("div", "evidence-links");
        group.findings.forEach(index => { const finding = model.findings[index]; list.append(button(text(finding.finding_id) + " · " + title(finding), () => CONAN.app.openFinding(finding), "text-button")); });
        claims.append(list);
      }});
      more.append(claims);
    });
    article.append(more); return article;
  }
  function render(host, model, topic, query) {
    host.replaceChildren();
    const filtered = model.groups.filter(g => (!topic || topic === "all" || g.category === topic) && (!query || g.search.includes(query.toLocaleLowerCase())));
    if (!filtered.length) { host.append(el("p", "empty-state", "No evidence items match. Try a filename, user, device serial, website, or finding ID.")); return; }
    categories.forEach(category => {
      const matches = filtered.filter(g => g.category === category.key);
      if (!matches.length) return;
      const section = el("section", "evidence-topic"), heading = el("div", "evidence-topic-head"), grid = el("div", "entity-grid");
      heading.append(el("h2", "", category.label), el("span", "small-mono", matches.length + " item" + (matches.length === 1 ? "" : "s")));
      section.append(heading, grid);
      let shown = 0;
      const more = button("Show more " + category.label.toLocaleLowerCase(), () => append());
      function append() { matches.slice(shown, shown + 6).forEach(group => grid.append(card(group, model))); shown += 6; more.hidden = shown >= matches.length; }
      append(); section.append(more); host.append(section);
    });
  }
  function highlights(model) {
    const section = el("section", "evidence-highlights");
    const heading = el("div", "card-head"); heading.append(el("h3", "", "Explore the evidence"), el("p", "", "Recorded properties, grouped by topic. Select a value to inspect its source."));
    section.append(heading);
    const grid = el("div", "highlight-grid");
    categories.forEach(category => {
      const groups = model.groups.filter(g => g.category === category.key).sort((a, b) => a.priority - b.priority || b.findings.size - a.findings.size || a.title.localeCompare(b.title));
      if (!groups.length) return;
      const box = el("section", "highlight-card c" + category.lane), header = el("div", "highlight-head");
      header.append(el("h4", "", category.label), el("span", "", String(groups.length)));
      box.append(header);
      // Named values lead the case summary rather than a certificate counter.
      // Root directories remain in the full inventory; named files lead the preview.
      const named = groups.filter(group => category.key !== "files" || !/^(?:[\\/]+|[a-z]:[\\/]?)$/i.test(group.title));
      (named.length ? named : groups).slice(0, 3).forEach(group => {
        const line = el("div", "highlight-item");
        line.append(button(group.title, () => CONAN.app.browseEvidence(category.key, text(group.records[0].row.obj_text)), "text-button"));
        const p = group.properties.find(p => ["Device serial", "Sender", "Profile path", "Property", "Original path", "Path", "Browser"].includes(p.label) && p.value !== group.title) || previewProperties(group, 2).find(p => p.value !== group.title);
        if (p) line.append(el("span", "", p.label + ": " + p.value));
        box.append(line);
      });
      box.append(button("Explore " + category.label.toLocaleLowerCase() + " →", () => CONAN.app.browseEvidence(category.key), "text-button"));
      grid.append(box);
    });
    section.append(grid); return section;
  }
  let revision, cached;
  CONAN.evidence = {categories, types, build, properties, title, time, entity, render, highlights,
    open(run, key) { if (!cached || revision !== key) { cached = build(run); revision = key; } return cached; }};
})();
