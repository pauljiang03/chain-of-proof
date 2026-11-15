"""Synthetic graph and report-state regressions; no browser, network, or model calls."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


ASSETS = Path(__file__).resolve().parents[1] / 'app' / 'static'
NODE = shutil.which('node')


@unittest.skipUnless(NODE, 'Node.js is required for the buildless client regressions')
class AppViewIntegrity(unittest.TestCase):
    def test_summary_stats_survive_unsupported_typed_topics_and_missing_refusal_data(self):
        source = (ASSETS / 'overview.js').read_text()
        harness = r'''
const vm = require('node:vm'), assert = require('node:assert/strict');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.ownText = ''; }
  set textContent(value) { this.ownText = String(value); }
  get textContent() { return this.ownText + this.children.map(child => child.textContent).join(' '); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; this.ownText = ''; }
  addEventListener() {}
}
const host = new Element('div');
const sandbox = {window: {CONAN: {story: {number: new Intl.NumberFormat('en-US'), clip: (s) => s}}},
 document: {createElement: tag => new Element(tag), getElementById: () => host}};
vm.createContext(sandbox);
'''
        harness += '\nvm.runInContext(' + json.dumps(source) + ', sandbox);\n'
        harness += r'''
const model = {findings: [{status: 'verified', strength: 'strong'}],
 records: [{kind: 'roleUsbDeviceInstanceId', exhibit: 'PC'}], events: [], main: null};
const view = sandbox.window.CONAN.overview;
view.render(model, {}, null, null, {points: [], devices: []});
assert.ok(host.textContent.includes('No supported summary for these record types'));
assert.ok(host.textContent.includes('does not establish absence of evidence'));
assert.ok(host.textContent.includes('Recorded accepted findings 1'));
assert.ok(host.textContent.includes('Recorded refusals Not supplied'));
assert.ok(!host.textContent.includes('Nothing was refused'));
view.render({...model}, {rejections: []}, null, null, {points: [], devices: []});
assert.ok(host.textContent.includes('Recorded refusals 0'));
assert.ok(host.textContent.includes('No refusal entries supplied'));
'''
        result = subprocess.run([NODE, '-e', harness], text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def run_js(self, asset, checks):
        source = (ASSETS / asset).read_text()
        # Expose the actual closure to the test and skip DOM event wiring only.
        # Graph layout/model code remains the production implementation.
        tail = '  wire();\n})();'
        self.assertEqual(source.count(tail), 1)
        if asset == 'graph.js':
            probe = ('  scopes = () => {}; rebuild = () => build();\n'
                     '  draw = () => {}; fit = () => true; interrupt = () => {}; applyStep = () => {}; follow = () => {};\n'
                     '  CONAN.probe = {state, prepare, build, selection, seek, local, followTarget};\n})();')
        elif asset == 'timeline.js':
            probe = '  CONAN.probe = {view, hit, nearest};\n})();'
        else:
            probe = '  CONAN.probe = {state, refresh};\n})();'
        source = source.replace(tail, probe)
        harness = r'''
const vm = require('node:vm'), assert = require('node:assert/strict');
const nodes = new Map();
const sandbox = {
  window: {matchMedia: () => ({matches: true})},
  document: {
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, {textContent: '', value: '', disabled: false,
        removeAttribute() {}, setAttribute() {}, replaceChildren() {}});
      return nodes.get(id);
    },
    querySelector: () => null,
    querySelectorAll: () => [],
  },
  localStorage: {getItem: () => null, setItem() {}},
  URLSearchParams, setTimeout: () => 1, clearTimeout() {},
};
vm.createContext(sandbox);
'''
        harness += '\nvm.runInContext(' + json.dumps(source) + ', sandbox);\n'
        harness += 'const api = sandbox.window.CONAN, state = api.probe.state;\n'
        harness += '(async () => {\n' + checks + '\n})().catch(error => {console.error(error); process.exitCode = 1;});'
        result = subprocess.run([NODE, '-e', harness], text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_conflicting_record_ids_and_image_labels_stay_separate(self):
        self.run_js('graph.js', r'''
const a = {id: 7, kind: 'fileSeen', obj_text: 'DEVICE A', prov: {exhibit: 'PC', image: 'IMAGE A', artifact: 'registry'}};
const b = {id: 7, kind: 'fileSeen', obj_text: 'DEVICE B', prov: {exhibit: 'PC', image: 'IMAGE B', artifact: 'registry'}};
// Different JSON key order alone does not make different evidence.
const aCopy = {prov: {artifact: 'registry', image: 'IMAGE A', exhibit: 'PC'}, obj_text: 'DEVICE A', kind: 'fileSeen', id: 7};
state.run = {findings: [a, b, aCopy].map((row, i) => ({finding_id: 'F' + (i + 1), status: 'verified', cited_facts: [row]}))};
api.probe.prepare(); api.probe.build();
const records = [...state.model.nodes.values()].filter(n => n.column === 'record');
assert.equal(records.length, 2);
assert.equal(records.find(n => n.row.obj_text === 'DEVICE A').outs.size, 2);
assert.equal(records.find(n => n.row.obj_text === 'DEVICE B').outs.size, 1);
assert.equal([...state.model.nodes.values()].filter(n => n.column === 'exhibit').length, 2);
assert.equal([...state.model.nodes.values()].filter(n => n.column === 'artifact').length, 2);
state.focus = state.items.find(item => item.id === 'F1').key;
assert.equal(api.probe.selection().map(item => item.id).join(','), 'F1,F3');
''')

    def test_duplicate_finding_labels_remain_distinct_claim_occurrences(self):
        self.run_js('graph.js', r'''
const first = {finding_id: 'DUP', status: 'verified', english: 'FIRST', cited_facts: [{id: 1}]};
const second = {finding_id: 'DUP', status: 'verified', english: 'SECOND', cited_facts: [{id: 2}]};
state.run = {findings: [first, second], rejections: [{finding_id: 'DUP', reason: 'REFUSED'}],
  conclusions: [{conclusion_id: 'C1', text: 'Ambiguous association', finding_ids: ['DUP']}]};
api.probe.prepare(); api.probe.build();
const claims = [...state.model.nodes.values()].filter(n => n.column === 'finding');
assert.equal(claims.length, 3);
assert.equal(new Set(claims.map(n => n.id)).size, 3);
assert.equal(claims.filter(n => !n.item.refused).map(n => n.item.data.english).join(','), 'FIRST,SECOND');
assert.equal([...state.model.nodes.values()].filter(n => n.column === 'judgment').length, 0);
api.graph.focusFinding('DUP'); assert.equal(state.focus, null); // label alone is ambiguous
api.graph.focusFinding('DUP', second);
assert.equal(api.probe.selection()[0].data.english, 'SECOND');
assert.equal(state.selected, state.items.find(item => item.data === second).key);
''')

    def test_timeline_places_only_dated_records_of_accepted_findings(self):
        self.run_js('timeline.js', r'''
const story = api.story, DAY = 86400000, at = (ms) => ms * 1000;
const base = Date.UTC(2015, 2, 22, 14, 0, 0);
const usb = {id: 1, kind: 'usbInsert', t: at(base), obj_text: 'SERIAL-1', aux_text: '(none)', prov: {exhibit: 'PC', time_meaning: 'first connection'}};
const mail = {id: 2, kind: 'emailSent', t: at(base + 3600000), obj_text: 'Subject', aux_text: 'from a to b', prov: {exhibit: 'PC', time_meaning: 'client submit time stored in the message'}};
const old = {id: 3, kind: 'programInstalled', t: at(Date.UTC(2009, 6, 14)), obj_text: 'Old program', prov: {exhibit: 'PC', time_meaning: 'last-write time of the uninstall key'}};
const examined = {id: 4, kind: 'fileContent', t: at(Date.UTC(2026, 10, 14)), obj_text: 'a.txt', prov: {exhibit: 'RM#1', time_meaning: 'when the image was examined'}};
const label = {id: 5, kind: 'tag', t: at(Date.UTC(2026, 10, 14)), obj_text: 'a.txt', aux_text: 'confidential'};
const unknown = {id: 6, kind: 'somethingNew', t: at(base + 60000), obj_text: 'x', prov: {exhibit: 'PC'}};
const copy = {...usb, obj_text: 'SERIAL-2'};                     // same id, different content
const reordered = {prov: usb.prov, aux_text: '(none)', obj_text: 'SERIAL-1', t: usb.t, kind: 'usbInsert', id: 1};
const model = story.build({findings: [
  {finding_id: 'F1', status: 'verified', strength: 'strong', cited_facts: [usb, mail, old, examined, label]},
  {finding_id: 'F2', status: 'verified', strength: 'heuristic', cited_facts: [usb, unknown, copy]},
  {finding_id: 'F3', status: 'refused', cited_facts: [{id: 9, kind: 'cdBurn', t: at(base)}]},
  {finding_id: 'F4', status: 'verified', cited_facts: [reordered]},
]});
assert.equal(model.findings.length, 3);                        // the refused proposal contributes nothing
assert.equal(model.records.length, 7);                         // conflicting copies stay apart
assert.equal(model.events.length, 4);                          // examination and unknown meanings are not activity
assert.equal(model.undatedCount, 3);
assert.deepEqual(Array.from(model.events, (r) => r.row.id), [3, 1, 1, 2]);
assert.equal(model.records.find((r) => r.obj === 'SERIAL-1').findings.length, 3);   // a reordered copy is the same record
assert.equal(model.main.count, 3);                             // the old install date is outside the busiest period
assert.equal(model.main.from, base); assert.equal(model.main.to, base + 3600000);
const lanes = Object.fromEntries(story.LANES.map((lane, i) => [lane.key, model.lanes[i]]));
assert.equal(lanes.devices.events, 2); assert.equal(lanes.messages.events, 1); assert.equal(lanes.other.records, 2); assert.equal(lanes.other.events, 0);
assert.equal(story.describe(model.events[1]), 'USB device connected: SERIAL-1');
assert.equal(story.describe(model.events[3]), 'E-mail: Subject — from a to b');
assert.equal(model.records.find((r) => r.kind === 'somethingNew').marked, false);
assert.equal(story.open({findings: []}, 'a', 'r1'), story.open({findings: [{status: 'verified', cited_facts: [usb]}]}, 'a', 'r1'));   // one model per stored revision
const marks = story.ticks(base, 2 * DAY, 920).list;
assert.ok(marks.length >= 4 && marks.every((mark, i) => !i || mark.t > marks[i - 1].t));
assert.equal(marks.filter((mark) => mark.major).length, 2);    // two UTC midnights in view
const near = api.probe.nearest(['a', 'b', 'c', 'd'], [10, 20, 30, 40], 24, 12, 2);
assert.equal(near.count, 2); assert.deepEqual(Array.from(near.items), ['b', 'c']);
''')

    def test_timeline_excludes_examination_and_unknown_times_without_losing_records(self):
        self.run_js('timeline.js', r'''
const t = Date.UTC(2026, 10, 14) * 1000;
// These are the actual attribute, inventory, and legacy media provenance forms.
const rows = [
  {id: 1, kind: 'attributeSubject', t, prov: {timestamp_semantics: 'examination_observation', time_meaning: 'when this source attribute was examined, not the described event'}},
  {id: 2, kind: 'fileSeen', t, prov: {timestamp_semantics: 'examination_observation', time_meaning: 'file observed when the image was examined; not application execution'}},
  {id: 3, kind: 'fileSeen', t, prov: {time_meaning: 'file observed when the image was examined; not application execution'}},
  {id: 4, kind: 'volumeOnDevice', t, prov: {time_meaning: 'when the image was examined, not an event on the device'}},
  {id: 5, kind: 'fileContent', t, prov: {timestamp_semantics: 'examination_observation'}},
  {id: 6, kind: 'fileSeen', t, prov: {timestamp_semantics: 'examination_observation', time_meaning: 'browser history visit time'}},
  {id: 7, kind: 'usbInsert', t: t - 1000000, prov: {}},
  {id: 8, kind: 'newKind', t: t - 1000000, prov: {timestamp_semantics: 'unrecognized_new_semantics'}},
  {id: 9, kind: 'programRun', t: t - 1000000, prov: {time_meaning: 'unspecified record timestamp'}},
  // Equality to an examination timestamp does not make a genuine source timestamp invalid.
  {id: 10, kind: 'webVisit', t, prov: {time_meaning: 'browser history visit time'}},
  {id: 11, kind: 'fileRemoved', t: t + 1000000, prov: {timestamp_semantics: 'journal_observation'}},
  {id: 12, kind: 'lnkTarget', t: t + 2000000, obj_text: 'target.txt', prov: {time_meaning: 'shortcut file last-modified time (last open via the shell)'}},
];
const model = api.story.build({findings: [{finding_id: 'F1', status: 'verified', cited_facts: rows}]});
assert.equal(model.records.length, rows.length);                 // inspector evidence is preserved
assert.equal(model.undatedCount, 9);
assert.deepEqual(Array.from(model.events, r => r.row.id), [10, 11, 12]);
assert.equal(model.main.count, 3);
for (let i = 0; i < 6; i++) {
  assert.equal(model.records[i].timeStatus, 'examination_observation');
  assert.equal(model.records[i].ms, null);
  assert.equal(model.records[i].row, rows[i]);
}
for (let i = 6; i < 9; i++) assert.equal(model.records[i].timeStatus, 'unknown');
assert.equal(api.story.describe(model.events[2]), 'Shortcut target: target.txt');
const observationsOnly = api.story.build({findings: [{status: 'verified', cited_facts: rows.slice(0, 9)}]});
assert.equal(observationsOnly.main, null);
assert.equal(observationsOnly.range, null);
assert.equal(observationsOnly.records.length, 9);
''')

    def test_times_use_the_zone_the_records_name_and_utc_otherwise(self):
        self.run_js('timeline.js', r'''
const story = api.story, DAY = 86400000, HOUR = 3600000;
const row = (id, ms, zone) => ({id, kind: 'usbInsert', t: ms * 1000, obj_text: 'S' + id, prov: zone ? {time_zone: zone} : {}});
const usb = Date.UTC(2015, 2, 23, 18, 31, 10);
// no zone named: UTC
story.open({findings: [{status: 'verified', cited_facts: [row(1, usb)]}]}, 'plain', 'r1');
assert.equal(story.zone.local, false); assert.equal(story.zoneNote(), 'UTC');
assert.equal(story.F.clock.format(usb), '18:31'); assert.equal(story.wall(usb), usb);
// the records name a zone: the most named one becomes the case clock
const model = story.open({findings: [{status: 'verified', cited_facts: [
  row(1, usb, 'local time, converted from America/New_York'), row(2, usb + 1000, 'FAT local time, converted from America/New_York'),
  row(3, usb + 2000, 'converted from Europe/Paris'), row(4, usb + 3000, 'UTC offset printed on the log line')]}]}, 'zoned', 'r1');
assert.equal(model.zone.name, 'America/New_York'); assert.equal(model.zone.records, 2);
assert.equal(story.zone.local, true); assert.equal(story.zoneNote(), 'local time (America/New_York)');
assert.equal(story.F.clock.format(usb), '14:31');                 // daylight time, four hours behind UTC
assert.equal(story.UTC.clock.format(usb), '18:31');               // the UTC time stays available
assert.equal(story.wall(usb) - usb, -4 * HOUR); assert.equal(story.unwall(story.wall(usb)), usb);
// day marks fall on the case's midnights, through the change to daylight time on 8 March 2015
const marks = story.ticks(Date.UTC(2015, 2, 7, 12), 3 * DAY, 920).list.filter((mark) => mark.major);
assert.deepEqual(Array.from(marks, (mark) => new Date(mark.t).toISOString().slice(5, 16)), ['03-08T05:00', '03-09T04:00', '03-10T04:00']);
assert.ok(marks.every((mark) => story.F.clock.format(mark.t) === '00:00'));
// a name this system does not know leaves UTC in place
story.adopt({name: 'America/Not_A_Zone', records: 9});
assert.equal(story.zone.local, false); assert.equal(story.F.clock.format(usb), '18:31');
''')

    def test_replay_runs_through_every_finding_not_only_one_page(self):
        self.run_js('graph.js', r'''
state.run = {findings: Array.from({length: 95}, (_, i) => ({finding_id: 'F' + (i + 1), status: 'verified', cited_facts: [{id: i}]}))};
api.probe.prepare(); api.probe.build();
assert.equal(state.steps, 95);                      // the slider spans the whole case
assert.equal(state.step, 40);                       // browsing starts at the end of the visible page
assert.equal(state.page, 0); assert.equal(api.probe.local(), 40);
api.probe.seek(41);                                 // the first finding of the second page
assert.equal(state.page, 1); assert.equal(api.probe.local(), 1);
api.probe.seek(40); assert.equal(state.page, 0); assert.equal(api.probe.local(), 40);
api.probe.seek(95); assert.equal(state.page, 2); assert.equal(api.probe.local(), 15);
assert.equal(state.model.shown[api.probe.local() - 1].id, 'F95');
api.probe.seek(0); assert.equal(state.page, 0); assert.equal(api.probe.local(), 0);
api.probe.seek(500); assert.equal(state.step, 95);  // never past the end
''')

    def test_replay_last_page_and_full_finding_fit_in_both_dimensions(self):
        self.run_js('graph.js', r'''
state.run = {findings: Array.from({length: 473}, (_, i) => ({finding_id: 'F' + (i + 1), status: 'verified', cited_facts: [{id: i}]}))};
api.probe.prepare(); api.probe.build();
api.probe.seek(472); assert.equal(state.page, 11);
api.probe.seek(473); assert.equal(state.step, 473); assert.equal(api.probe.local(), 33);
assert.equal(state.model.shown[api.probe.local() - 1].id, 'F473');
const item = {x: 1000, y: 6000, w: 304, h: 40};
const host = {width: 720, height: 500}, inset = {top: 70, bottom: 40};
const view = api.probe.followTarget(item, host, inset, {x: 20, y: 50, k: .72});
assert.ok(item.x * view.k + view.x >= 20);
assert.ok((item.x + item.w) * view.k + view.x <= host.width - 20);
assert.ok((item.y - item.h / 2) * view.k + view.y >= inset.top + 12);
assert.ok((item.y + item.h / 2) * view.k + view.y <= host.height - inset.bottom - 12);
''')

    def test_snapshot_scope_and_conflicting_rows_within_one_finding(self):
        self.run_js('graph.js', r'''
const rows = ['first', 'second'].map(snapshot => ({id: 7, obj_text: snapshot,
  prov: {image: 'image.E01', exhibit: 'PC', snapshot_id: snapshot, artifact: 'registry'}}));
state.run = {findings: [{finding_id: 'F1', status: 'verified', cited_facts: rows}]};
api.probe.prepare(); api.probe.build();
assert.equal([...state.model.nodes.values()].filter(n => n.column === 'record').length, 2);
assert.equal([...state.model.nodes.values()].filter(n => n.column === 'exhibit').length, 2);
''')

    def test_duplicate_conclusion_labels_keep_their_own_text_and_edges(self):
        self.run_js('graph.js', r'''
state.run = {
  findings: [1, 2].map(i => ({finding_id: 'F' + i, status: 'verified', cited_facts: [{id: i}]})),
  conclusions: [1, 2].map(i => ({conclusion_id: 'DUP', text: 'Judgment ' + i, finding_ids: ['F' + i]})),
};
api.probe.prepare(); api.probe.build();
const judgments = [...state.model.nodes.values()].filter(n => n.column === 'judgment');
assert.equal(judgments.length, 2);
assert.equal(new Set(judgments.map(n => n.id)).size, 2);
judgments.forEach((node, i) => {
  assert.equal(node.conclusion.conclusion_id, 'DUP');
  assert.equal(node.conclusion.text, 'Judgment ' + (i + 1));
  assert.equal(node.ins.size, 1);
  assert.equal(state.model.nodes.get([...node.ins][0]).item.id, 'F' + (i + 1));
});
''')

    def test_refusal_does_not_borrow_a_conflicting_copied_record(self):
        self.run_js('graph.js', r'''
state.run = {
  findings: ['COPY A', 'COPY B'].map((value, i) => ({finding_id: 'F' + i, status: 'verified', cited_facts: [{id: 7, obj_text: value}]})),
  rejections: [{finding_id: 'R1', proof_gap: {requirements: [{fact_ids: [7], observed: {records: [
    {id: 7, kind: 'fileSeen', obj: {text: 'DIAGNOSTIC VALUE'}, aux: {text: 'SERIAL'}}]}}]}}],
};
api.probe.prepare();
assert.equal(state.items.find(item => item.refused).rows[0].obj_text, 'DIAGNOSTIC VALUE');
''')

    def test_graph_refreshes_equal_size_changes_and_preserves_current_filters(self):
        self.run_js('graph.js', r'''
const run = {findings: [{finding_id: 'F1', status: 'verified', english: 'OLD', cited_facts: [{id: 1, obj_text: 'before'}]}]};
api.graph.render(run, [], 'case');
state.query = 'keep this query'; state.scope = 'keep this scope';
const next = JSON.parse(JSON.stringify(run));
next.findings[0].english = 'NEW'; next.findings[0].cited_facts[0].obj_text = 'after';
api.graph.render(next, [{sequence: 1, finding_id: 'F1'}], 'case');
assert.equal(state.items[0].data.english, 'NEW');
assert.equal(state.items[0].rows[0].obj_text, 'after');
assert.equal(state.query, 'keep this query'); assert.equal(state.scope, 'keep this scope');
assert.equal(state.events.length, 1);
next.findings[0].status = 'proposed';
api.graph.render(next, [], 'case');
assert.equal(state.items.length, 0); // previously accepted data must not survive a status change
''')

    def test_report_invalidates_same_count_changes_without_erasing_drafts(self):
        self.run_js('report.js', r'''
api.report.open('case', ['F1', 'F2'], 'before');
state.marked.add('F1'); state.scope = 'marked'; state.cover.examiner = 'Examiner draft';
state.stale = false; state.built = true;
const request = state.request;
api.report.open('case', ['F1', 'F2'], 'after');
assert.equal(state.stale, true); assert.equal(nodes.get('report-print').disabled, true);
assert.equal(state.request, request + 1);
assert.equal(state.cover.examiner, 'Examiner draft'); assert.equal(api.report.has('F1'), true);
assert.equal(state.scope, 'marked');
state.stale = false;
api.report.open('case', ['F1', 'F2'], 'after');
assert.equal(state.stale, false); // an unchanged refresh preserves the preview
api.report.open('case', ['F1', 'F3'], 'after');
assert.equal(state.stale, true); assert.equal(api.report.has('F1'), true);
''')

    def test_inflight_preview_is_discarded_when_the_case_contents_change(self):
        self.run_js('report.js', r'''
let resolveFetch;
sandbox.fetch = () => new Promise(resolve => {resolveFetch = resolve;});
api.report.open('case', ['F1'], 'before'); state.active = true;
const pending = api.probe.refresh();
api.report.open('case', ['F2'], 'after');
resolveFetch({ok: true, text: async () => '<p>Old report must never mount.</p>'});
await pending;
assert.equal(state.stale, true); assert.equal(state.built, false); assert.equal(state.shadow, null);
assert.equal(nodes.get('report-print').disabled, true);
''')


    def test_every_edge_between_panes_has_a_working_resize_handle(self):
        import re
        page, script, style = ((ASSETS / name).read_text() for name in ('index.html', 'app.js', 'style.css'))
        handles = dict(re.findall(r'<div class="resizer" id="([\w-]+)" role="separator" aria-orientation="vertical" tabindex="0" aria-controls="([\w-]+)"', page))
        self.assertEqual(handles, {'resize-side': 'sidebar', 'resize-insp': 'inspector', 'resize-report': 'report-form'})
        panes = re.findall(r'\{ handle: "([\w-]+)", pane: "([\w-]+)", name: "(--[\w-]+)", base: (\d+), min: (\d+), max: (\d+), sign: (-?1) \}', script)
        self.assertEqual({handle: pane for handle, pane, *_ in panes}, handles)
        for handle, pane, name, base, low, high, _ in panes:
            self.assertEqual(page.count('id="%s"' % pane), 1)            # the pane it resizes exists
            self.assertIn('var(%s, %spx)' % (name, base), style)         # the stylesheet reads the width, default first
            self.assertIn('#%s {' % handle, style)                       # and places the handle
            self.assertTrue(int(low) < int(base) < int(high))
        self.assertEqual(script.count('resizablePanes();'), 1)
        # A saved width is clamped by the stylesheet, so no pane can crowd out the middle of a small window.
        for clamp in ('min(var(--side-w, 208px), 30vw)', 'min(var(--insp-w, 380px), 45vw)', 'min(var(--report-w, 264px), 60%)'):
            self.assertIn(clamp, style)


if __name__ == '__main__':
    unittest.main()
