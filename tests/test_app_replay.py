"""Replay event regression with the real event handlers, drawing and camera logic.

A small DOM supplies geometry. No replay functions are replaced. Browser/native
visual review complements these tests; this harness does not emulate a browser.
"""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

NODE = shutil.which('node')
GRAPH = Path(__file__).resolve().parents[1] / 'app' / 'static' / 'graph.js'


@unittest.skipUnless(NODE, 'Node.js is required for client interaction tests')
class ReplayInteraction(unittest.TestCase):
    def run_graph(self, checks):
        source = GRAPH.read_text().replace('  wire();\n})();',
            '  CONAN.probe = {state, motion};\n  wire();\n})();')
        harness = r'''
const vm = require('node:vm'), assert = require('node:assert/strict');
const nodes = new Map(), timers = new Map(), frames = new Map();
let timerId = 0, frameId = 0;
const host = {width: 660, height: 480, top: 0, left: 0, bottom: 480};
function element(id = '') {
  const attrs = {}, listeners = new Map(), classes = new Set();
  return {id, attrs, listeners, children: [], textContent: '', value: '', disabled: false,
    classList: {add: x => classes.add(x), remove: x => classes.delete(x),
      toggle(x, on) { if (on) classes.add(x); else classes.delete(x); }, contains: x => classes.has(x)},
    setAttribute(k,v) { attrs[k] = String(v); }, removeAttribute(k) { delete attrs[k]; },
    append(...items) { this.children.push(...items); }, replaceChildren(...items) { this.children = items; },
    addEventListener(name, fn) { if (!listeners.has(name)) listeners.set(name, []); listeners.get(name).push(fn); },
    fire(name, more = {}) { for (const fn of listeners.get(name) || []) fn({target: this, preventDefault() {}, stopPropagation() {}, ...more}); },
    getBoundingClientRect() { return host; }, setPointerCapture() {}, closest() { return null; }
  };
}
const get = id => { if (!nodes.has(id)) nodes.set(id, element(id)); return nodes.get(id); };
const sandbox = {window: {matchMedia: () => ({matches: false}), addEventListener() {}},
  document: {getElementById: get, createElement: () => element(), createElementNS: () => element(),
    querySelector: selector => ({getBoundingClientRect: () => selector === '.graph-toolbar'
      ? {bottom: 62} : {top: host.height - 94}})},
  setTimeout: () => 1, clearTimeout() {},
  setInterval(fn) { timers.set(++timerId, fn); return timerId; }, clearInterval(id) { timers.delete(id); },
  performance: {now: () => 0},
  requestAnimationFrame(fn) { frames.set(++frameId, fn); return frameId; }, cancelAnimationFrame(id) { frames.delete(id); }
};
vm.createContext(sandbox);
'''
        harness += '\nvm.runInContext(' + json.dumps(source) + ', sandbox);\n'
        harness += r'''
const api = sandbox.window.CONAN, state = api.probe.state;
function load(count) {
  const findings = Array.from({length:count}, (_,i) => ({finding_id:'F'+(i+1), status:'verified',
    english:'Exact statement '+(i+1), cited_facts:Array.from({length:i%7+1}, (_,j) => ({
      id:i*10+j, kind:'fileSeen', obj_text:'file-'+i+'-'+j,
      prov:{exhibit:'E1',image:'disk.E01',artifact:'source '+i}}))}));
  api.graph.render({findings}, [], 'case-'+count, String(count));
}
function currentFits() {
  const current = [...state.model.nodes.values()].find(n => n.column === 'finding' && n.birth === state.step-state.page*40);
  assert.ok(current, 'the replay position has a finding on this page');
  assert.ok(current.el.classList.contains('current'));
  const {x,y,k} = state.view;
  assert.ok(current.x*k+x >= 20-1e-6, 'left edge visible');
  assert.ok((current.x+current.w)*k+x <= host.width-20+1e-6, 'right edge visible');
  assert.ok((current.y-current.h/2)*k+y >= 86-1e-6, 'below toolbar');
  assert.ok((current.y+current.h/2)*k+y <= host.height-116+1e-6, 'above replay controls');
  assert.equal(frames.size, 0, 'replay must not wait for a camera animation');
  assert.equal(get('graph-step').value, String(state.step));
}
function input(value, type='input') { get('graph-step').value = String(value); get('graph-step').fire(type); }
'''
        result = subprocess.run([NODE, '-e', harness + checks], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_browsing_never_claims_the_whole_case_is_at_the_end(self):
        self.run_graph(r'''
load(473);
assert.equal(state.step,40); assert.equal(get('graph-step').max,'473');
assert.equal(get('graph-step-label').textContent,'Viewing 1–40 / 473');
get('graph-next').fire('click');
assert.equal(state.step,80); assert.equal(state.page,1);
get('graph-prev').fire('click');
assert.equal(state.step,40); assert.equal(state.page,0);
get('graph-end').fire('click');
assert.equal(state.step,473); assert.equal(state.page,11); currentFits();
assert.equal(get('graph-end').disabled,true);
get('graph-prev').fire('click');
assert.equal(state.step,440); assert.equal(state.page,10);
assert.equal(get('graph-end').disabled,false);
''')

    def test_slider_inputs_keyboard_and_zoom_reach_the_exact_endpoint(self):
        self.run_graph(r'''
load(473);
for (const value of [1,40,41,472,473,15,80,81,0,473]) {
  input(value); assert.equal(state.step,value);
  if (value) currentFits();
}
input(472, 'change'); get('graph-step').fire('keydown', {key:'End'});
assert.equal(state.step,473); currentFits();
get('graph-step').fire('keydown', {key:'Home'}); assert.equal(state.step,0);
state.view.k=2.5; host.width=340;
input(473); currentFits();
host.width=280; api.graph.resize(); currentFits();
''')

    def test_automatic_playback_pause_and_resume_finish_on_the_last_visible_finding(self):
        self.run_graph(r'''
load(473); get('graph-play').fire('click');
assert.equal(state.step,0); assert.equal(timers.size,1);
for(let i=0;i<77;i++) { [...timers.values()][0](); currentFits(); }
get('graph-play').fire('click');
assert.equal(timers.size,0); assert.match(get('graph-play').textContent,/Resume/);
assert.equal(get('graph-play').attrs['aria-label'],'Resume the graph');
get('graph-play').fire('click'); assert.equal(state.step,77);
let ticks=0;
while(timers.size && ticks++<500) { [...timers.values()][0](); currentFits(); }
assert.equal(state.step,473); assert.equal(state.page,11); assert.equal(timers.size,0);
assert.match(get('graph-step-label').textContent,/473 \/ 473.*F473/);
assert.match(get('graph-play').textContent,/Replay/);
get('graph-play').fire('click'); assert.equal(state.step,0);
get('graph-step').fire('pointerdown'); assert.equal(timers.size,0);
input(473); currentFits();
''')

    def test_empty_and_single_claim_replays(self):
        self.run_graph(r'''
load(0); assert.equal(get('graph-step').disabled,true);
get('graph-play').fire('click'); assert.equal(timers.size,0);
load(1); assert.equal(state.step,1); assert.equal(get('graph-end').disabled,false);
get('graph-end').fire('click'); currentFits();
get('graph-play').fire('click'); [...timers.values()][0]();
assert.equal(state.step,1); assert.equal(timers.size,0); currentFits();
''')
