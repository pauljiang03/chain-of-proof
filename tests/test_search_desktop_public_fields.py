"""Component-scoped Windows Search rows retain their native indexed meanings."""
from copy import deepcopy
import unittest

from agent.answer_requirements import check, parse
from agent.path_predicates import POLICY, matches_directory
from checker.catalog import ROLES

CONDITION = dict(role='search.index.item_path', policy=POLICY,
                 directory=r'\Users\informant\Desktop', include_directory=True, case_sensitive=False)
REQUIRED = ['search.index.item_path', 'search.index.date_created', 'search.index.container_path',
            'search.index.table', 'search.index.document_id']


class DesktopPathPredicate(unittest.TestCase):
    def test_component_matching_preserves_volume_qualification(self):
        for path in [r'\Users\informant\Desktop', r'\Users\informant\Desktop\a.txt',
                     r'C:\Users\informant\Desktop\a.txt', r'D:\USERS\INFORMANT\desktop\a.txt',
                     '\\Users\\informant\\Desktop\\', '\\Users\\informant\\Desktop\\Folder\\']:
            with self.subTest(path=path):
                self.assertTrue(matches_directory(path, CONDITION))
        self.assertFalse(matches_directory(r'\Users\informant\Desktop', dict(CONDITION, include_directory=False)))
        self.assertFalse(matches_directory(r'\Users\informant\desktop\a', dict(CONDITION, case_sensitive=True)))

    def test_rejects_lookalikes_traversal_namespaces_and_ambiguous_syntax(self):
        paths = [r'\Users\informant\Desktop2\a', r'\Users\other\Desktop\a',
                 r'\Users\informant\Desktop\..\a', r'\Users\informant\Desktop\.\a',
                 r'C:Users\informant\Desktop\a', r'\\server\Users\informant\Desktop\a',
                 r'\\?\C:\Users\informant\Desktop\a', r'\??\C:\Users\informant\Desktop\a',
                 r'\Users\informant\Desktop\a:stream', r'\Users\informant\Desktop\\a',
                 '\\Users\\informant\\Desktop\\\\', r'\Users\informant\Desktop\a.',
                 r'\Users\informant\Desktop\a ', r'\Users\informant\Desktop\NUL.txt',
                 '/Users/informant/Desktop/a', r'Users\informant\Desktop\a',
                 '\\Uſers\\informant\\Desktop\\a', '\\Users\\ınformant\\Desktop\\a',
                 r'\Users\informant\Desktop\*.txt', '\\Users\\informant\\Desktop\\a\x00']
        for path in paths:
            with self.subTest(path=path): self.assertFalse(matches_directory(path, CONDITION))

    def test_windows_superscript_device_aliases_are_rejected_in_every_component(self):
        for family in ('COM', 'LPT'):
            for digit in '¹²³':
                for name in (family + digit, (family + digit).lower()):
                    for suffix in ('', '.txt'):
                        for tail in ('', '\\child.txt', '\\'):
                            path = '\\Users\\informant\\Desktop\\' + name + suffix + tail
                            with self.subTest(path=path):
                                self.assertFalse(matches_directory(path, CONDITION))

    def test_requirement_validation_is_strict(self):
        base = dict(semantic_types=[ROLES[REQUIRED[0]].semantic_type], meaning='Indexed path.',
                    evidence_needed='Same source row.', attribute_path_conditions=[CONDITION])
        self.assertEqual(parse(base)['attribute_path_conditions'], [CONDITION])
        bad = [dict(CONDITION, policy='future'), dict(CONDITION, directory=r'C:\Users\informant\Desktop'),
               dict(CONDITION, directory=r'\Users\informant\Desktop\..'),
               dict(CONDITION, include_directory=1), dict(CONDITION, case_sensitive=0),
               dict(CONDITION, role='account.enabled'), dict(CONDITION, extra=True)]
        for condition in bad:
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                parse(dict(base, attribute_path_conditions=[condition]))
        with self.assertRaises(ValueError): parse(dict(base, attribute_path_conditions=[CONDITION, CONDITION]))

    def test_condition_requires_one_same_part_typed_path(self):
        raw = dict(semantic_types=[ROLES[REQUIRED[1]].semantic_type], meaning='Indexed DateCreated.',
                   evidence_needed='Same source row.', required_attribute_roles=REQUIRED,
                   attribute_path_conditions=[CONDITION])
        values = [r'C:\Users\informant\Desktop\a', '2001-02-03T00:00:00Z', '/native.edb', 'SystemIndex', 7]
        fields = {'value_'+str(i): dict(semantic_type=ROLES[role].semantic_type, value=value)
                  for i, (role, value) in enumerate(zip(REQUIRED, values))}
        def evaluate(offered):
            return check(raw, 'attributeTuple', 'value_1', ROLES[REQUIRED[1]].semantic_type, part_fields=offered)
        self.assertEqual(evaluate(fields)['status'], 'compatible')
        for offered in [{k:v for k,v in fields.items() if k != 'value_0'},
                        dict(fields, extra=deepcopy(fields['value_0'])),
                        dict(fields, value_0=dict(semantic_type=ROLES[REQUIRED[0]].semantic_type, value=42)),
                        dict(fields, value_0=dict(semantic_type=ROLES[REQUIRED[0]].semantic_type,
                                                 value=r'C:\Users\informant\Desktop2\a'))]:
            self.assertEqual(evaluate(offered)['status'], 'incompatible')


class DesktopPublicProjection(unittest.TestCase):
    def fixture(self, variant='valid'):
        import hashlib
        import json
        from pathlib import Path
        import tempfile
        from agent.answer_projection import claim_digest, project_answers
        from checker.facts import JsonFacts
        from eval.data_leakage_strict_draft.scope_contract import apply_data_leakage_scopes
        from extractor.attributes import emit_attribute
        from extractor.store import Evidence
        root = Path(__file__).resolve().parents[1]
        part = json.loads((root/'eval/data_leakage_strict_draft/parts/q41_60.json').read_text())
        q = next(q for q in part['questions'] if q['id'] == 'Q46')
        plan = json.loads((root/'eval/data_leakage_strict_draft/scope_plan.json').read_text())
        apply_data_leakage_scopes([q], plan)
        origin = deepcopy(q['answer_schema']['x-claim-scope']['origins'][0])
        if variant == 'foreign': origin.update(image='foreign.E01', exhibit='FOREIGN')
        roles = list(REQUIRED)
        values = [r'D:\Users\informant\Desktop\file.txt', '2001-02-03T00:00:00.1234567Z',
                  r'C:\ProgramData\Search\Windows.edb', 'SystemIndex_0A', 42]
        if variant == 'trailing': values[0] = 'D:\\Users\\informant\\Desktop\\Folder\\'
        if variant == 'lookalike': values[0] = r'D:\Users\informant\Desktop2\file.txt'
        if variant == 'modified': roles[1] = 'search.index.date_modified'
        evidence = Evidence(); identities = []
        for index, (role, value) in enumerate(zip(roles, values)):
            subject = 'container-B:row42' if variant == 'mixed' and index == 2 else 'container-A:row42'
            identities.append(emit_attribute(evidence, subject, role, value, 100,
                                            artifact='synthetic Search index', **origin))
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); output = Path(temp.name)
        evidence.write_json(output/'facts.json', {}); facts = JsonFacts(output/'facts.json')
        entries = []
        for identity, role in zip(identities, roles):
            records = {f.kind:f.id for f in facts.all() if facts.string(f.obj) == identity}
            spec = ROLES[role]
            entries.append([records['attributeSubject'], records[spec.kind], records[spec.value_kind], role])
        if variant == 'missing': entries.pop()
        if variant == 'duplicate': entries.append(deepcopy(entries[0]))
        row = {'candidate_id':'Search', 'claim':{'attributeTuple':entries}}
        bindings = [dict(candidate_id='Search', claim_sha256=claim_digest(row['claim']), question_id='Q46',
                         path=['records', 0, field], part=0, field='value_'+str(index))
                    for index, field in [(0, 'path'), (1, 'date_created')]]
        projected = project_answers({'schema_version':2, 'case_id':'synthetic-search', 'questions':[q]},
            [row], bindings, facts, require_claim_requirements=True, require_evidence_scope=True,
            evidence_facts_sha256=hashlib.sha256((output/'facts.json').read_bytes()).hexdigest())
        return projected, row, facts, output, values

    def test_actual_public_mapping_preserves_full_native_path_and_index_timestamp(self):
        from checker.check import check
        result, row, facts, root, values = self.fixture()
        self.assertFalse(result['unsupported'])
        self.assertEqual(result['submission']['answers'][0]['answer'],
                         {'records':[{'path':values[0], 'date_created':values[1]}]})
        cert = check(row['claim'], 'SearchValid', facts, out_dir=root)
        self.assertEqual(cert['status'], 'verified', cert)

    def test_single_terminal_directory_separator_is_preserved(self):
        result, _, _, _, values = self.fixture('trailing')
        self.assertFalse(result['unsupported'])
        self.assertEqual(result['submission']['answers'][0]['answer']['records'][0]['path'], values[0])
        self.assertTrue(values[0].endswith('\\'))

    def test_missing_duplicate_wrong_date_path_and_origin_fail_public_gate(self):
        for variant in ('missing', 'duplicate', 'modified', 'lookalike', 'foreign'):
            with self.subTest(variant=variant):
                result, _, _, _, _ = self.fixture(variant)
                self.assertFalse(result['leaves'])
                self.assertTrue(result['unsupported'])

    def test_cross_container_subject_cannot_certify(self):
        from checker.check import check
        _, row, facts, root, _ = self.fixture('mixed')
        cert = check(row['claim'], 'SearchMixed', facts, out_dir=root)
        self.assertNotEqual(cert['status'], 'verified', cert)
