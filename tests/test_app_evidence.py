"""Evidence browsing must retain source scope, copied values and exact finding identity."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')


@unittest.skipUnless(NODE, 'Node.js is required for client regressions')
class EvidenceOverview(unittest.TestCase):
    def run_js(self, checks):
        source = (ROOT / 'app/static/evidence.js').read_text()
        script = "const vm=require('node:vm'),assert=require('node:assert/strict'); const sandbox={window:{},URL}; vm.createContext(sandbox);\n"
        script += 'vm.runInContext(' + json.dumps(source) + ',sandbox); const api=sandbox.window.CONAN.evidence;\n'
        script += "const finding=(rows,extra={})=>({status:'verified',finding_id:'DUP',cited_facts:rows,...extra});\n"
        result = subprocess.run([NODE, '-e', script + checks], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_same_names_keep_image_user_and_snapshot_scopes(self):
        self.run_js(r'''
const base={id:7,kind:'fileSeen',obj_text:'C:\\plan.xlsx',prov:{image:'a.E01',exhibit:'PC',user:'maya',snapshot_id:'one'}};
const variants=[base, {...base,prov:{...base.prov,image:'b.E01'}}, {...base,prov:{...base.prov,user:'dana'}}, {...base,prov:{...base.prov,snapshot_id:'two'}}];
const model=api.build({findings:variants.map(row=>finding([row]))});
assert.equal(model.groups.length,4); assert.equal(model.records.length,4);
for(const group of model.groups) assert.equal(group.findings.size,1);
''')

    def test_duplicate_rows_and_labels_preserve_conflicting_properties_and_finding_occurrences(self):
        self.run_js(r'''
const row={id:7,kind:'fileSeen',obj_text:'C:\\plan.xlsx',prov:{image:'a.E01',size:10}};
const reordered={prov:{size:10,image:'a.E01'},obj_text:'C:\\plan.xlsx',kind:'fileSeen',id:7};
const changed={...row,prov:{...row.prov,size:20}};
const model=api.build({findings:[finding([row,reordered]),finding([changed]),finding([row],{status:'proposed'}),null]});
assert.equal(model.findings.length,2); assert.equal(model.records.length,2); assert.equal(model.groups.length,1);
assert.equal(model.groups[0].findings.size,2);
const sizes=model.groups[0].properties.filter(p=>p.label==='Size (bytes)');
assert.deepEqual(Array.from(sizes,p=>p.value),['10','20']);
assert.equal(sizes[0].entry.row,row); assert.equal(sizes[1].entry.row,changed);
assert.deepEqual(Array.from(sizes[0].entry.findings),[0]); assert.deepEqual(Array.from(sizes[1].entry.findings),[1]);
''')

    def test_time_excludes_examination_and_unknown_meaning_and_keeps_source_timestamp(self):
        self.run_js(r'''
const row={t:1781024400000000,prov:{time_meaning:'browser history visit time'}};
assert.equal(api.time(row),'2026-06-09T17:00:00.000Z');
for(const prov of [{}, {time_meaning:'unspecified record timestamp'}, {time_meaning:'file observed when the image was examined'},
 {time_meaning:'when this source attribute was examined'}, {timestamp_semantics:'examination_observation',time_meaning:'visit time'}]) assert.equal(api.time({...row,prov}),'');
assert.equal(api.time({...row,t:0}),'');
assert.equal(api.time({...row,prov:{timestamp_semantics:'journal_observation'}}),'2026-06-09T17:00:00.000Z');
''')

    def test_website_grouping_does_not_cross_users_and_keeps_full_urls(self):
        self.run_js(r'''
const row=(id,url,user)=>({id,kind:'webVisit',obj_text:url,aux_text:'Chrome',prov:{image:'a.E01',user}});
const a=row(1,'https://example.test/a','maya'),b=row(2,'https://example.test/b','maya'),c=row(3,'https://example.test/a','dana');
const model=api.build({findings:[finding([a,b,c])]});
assert.equal(model.groups.length,2); assert.ok(model.groups.every(g=>g.title==='example.test'));
const group=model.groups.find(g=>g.records.length===2);
assert.deepEqual(Array.from(group.properties.filter(p=>p.label==='URL'),p=>p.value),[a.obj_text,b.obj_text]);
''')

    def test_optional_properties_keep_zero_false_and_omit_missing_values(self):
        self.run_js(r'''
const props=api.properties({kind:'emailSent',obj_text:'Review',aux_text:'(none)',prov:{attachments:0,recovered:false,sender_address:'maya@example.test'}});
assert.equal(props.find(p=>p.label==='Attachment count').value,'0');
assert.equal(props.find(p=>p.label==='Recovered entry').value,'false');
assert.equal(props.find(p=>p.label==='Sender').value,'maya@example.test');
assert.ok(!props.some(p=>p.value==='(none)'||p.value==='undefined'));
''')

    def test_combined_claim_titles_do_not_rewrite_sentences(self):
        self.run_js(r'''
const f=finding([{id:1,kind:'fileRenamed',obj_text:'C:\\draft.txt',aux_text:'C:\\review.txt'}],
 {question:'Combined certified findings',english:'VERBATIM CLAIM',claim:{both:[{renamed:[1]},{before:[1,2]}]}});
assert.match(api.title(f),/^2 related statements/); assert.equal(f.english,'VERBATIM CLAIM');
assert.equal(api.title({...f,question:'Q2: Which file was renamed?'}),'Which file was renamed?');
''')

    def test_synthetic_demo_exposes_useful_topics_and_supporting_finding_links(self):
        run = json.loads((ROOT / 'app/sample/run.json').read_text())
        self.assertTrue(run['case']['sample'])
        self.assertEqual(len(run['findings']), 32)
        self.assertEqual(len(run['rejections']), 1)
        self.run_js('const run=' + json.dumps(run) + r''';
const model=api.build(run),categories=new Set(model.groups.map(g=>g.category));
for(const key of ['devices','files','web','messages','programs','accounts','system']) assert.ok(categories.has(key),key);
assert.ok(model.groups.some(g=>g.title==='Atlas Pocket Drive'));
assert.ok(model.groups.some(g=>g.title==='HARBOR-LAPTOP'));
assert.ok(model.groups.some(g=>g.search.includes('maya@example.test')));
assert.ok(model.groups.some(g=>g.search.includes('demo-project-042')));
assert.ok(model.groups.every(g=>g.records.length&&g.findings.size));
assert.ok(model.groups.every(g=>g.records.every(entry=>[...entry.findings].every(i=>model.findings[i].cited_facts.some(row=>JSON.stringify(row)===JSON.stringify(entry.row))))));
''')

if __name__ == '__main__':
    unittest.main()
