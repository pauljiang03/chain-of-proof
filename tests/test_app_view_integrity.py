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
    def run_js(self, asset, checks):
        source = (ASSETS / asset).read_text()
        # Expose the actual closure to the test and skip DOM event wiring only.
        # Graph layout/model code remains the production implementation.
        tail = '  wire();\n})();'
        self.assertEqual(source.count(tail), 1)
        if asset == 'graph.js':
            probe = ('  scopes = () => {}; rebuild = () => build();\n'
                     '  CONAN.probe = {state, prepare, build, selection};\n})();')
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

    def test_snapshot_scope_and_conflicting_rows_within_one_finding(self):
        self.run_js('graph.js', r'''
const rows = ['first', 'second'].map(snapshot => ({id: 7, obj_text: snapshot,
  prov: {image: 'image.E01', exhibit: 'PC', snapshot_id: snapshot, artifact: 'registry'}}));
state.run = {findings: [{finding_id: 'F1', status: 'verified', cited_facts: rows}]};
api.probe.prepare(); api.probe.build();
assert.equal([...state.model.nodes.values()].filter(n => n.column === 'record').length, 2);
assert.equal([...state.model.nodes.values()].filter(n => n.column === 'exhibit').length, 2);
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


if __name__ == '__main__':
    unittest.main()
