"""Reviewed signed source integers are distinct from nonnegative count attributes."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from checker import check as checker, claims
from checker.catalog import ROLES, VALUE_TYPES, decode_value
from checker.facts import JsonFacts, KINDS
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify


class SignedAttributes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ev = Evidence()
        self.identities = {}
        self.roles = {}
        values = (
            ('bias', 'os.time_zone.bias_minutes', -60),
            ('standard', 'os.time_zone.standard_bias_minutes', 0),
            ('daylight', 'os.time_zone.daylight_bias_minutes', -60),
            ('active', 'os.time_zone.active_bias_minutes', 330),
            ('count', 'account.count', 2),
            ('title', 'document.ole.title', 'Literal title'),
            ('filetime', 'document.ole.created_filetime', 133000000000000000),
        )
        for key, role, value in values:
            self.roles[key] = role
            self.identities[key] = emit_attribute(self.ev, 'synthetic-image:base:source', role,
                value, 1000000, artifact='synthetic configuration', field=key)
        self.path = self.root / 'facts.json'
        self.ev.write_json(self.path, {})
        self.source = JsonFacts(self.path)
        self.sequence = 0

    def attribute(self, key):
        spec = ROLES[self.roles[key]]
        rows = {f.kind: f.id for f in self.source.all() if self.source.string(f.obj) == self.identities[key]}
        return {'attributeRecorded': [rows['attributeSubject'], rows[spec.kind], rows[spec.value_kind], spec.name]}

    def certify(self, raw, accepted=True):
        self.sequence += 1
        with patch.object(checker, 'run_kernel', wraps=checker.run_kernel) as kernel:
            result = checker.check(raw, f'Signed{self.sequence}', self.source, out_dir=self.root)
        self.assertTrue(kernel.called)
        self.assertEqual(result['status'], 'verified' if accepted else 'rejected', result)
        if accepted:
            self.assertEqual(result['axioms'], [])
            self.assertEqual(result['trust_tier'], 'kernel')
            self.assertEqual(verify(result, self.source), [])
        return result

    def replace_value_kind(self, key, kind):
        data = json.loads(self.path.read_text())
        value_id = self.attribute(key)['attributeRecorded'][2]
        next(f for f in data['facts'] if f['id'] == value_id)['kind'] = kind
        self.path.write_text(json.dumps(data))
        self.source = JsonFacts(self.path)

    def test_negative_zero_positive_and_unsigned_filetime_certify_and_replay(self):
        for key in self.roles:
            cert = self.certify(self.attribute(key))
            if key == 'bias':
                self.assertIn('-60', cert['english'])
                self.assertIn('not measured clock accuracy', cert['english'])

    def test_signed_unsigned_and_text_values_cannot_cross_fixed_types(self):
        claim = self.attribute('active')
        self.replace_value_kind('active', 'attributeIntegerValue')
        self.certify(claim, False)
        self.ev.write_json(self.path, {})
        self.source = JsonFacts(self.path)
        claim = self.attribute('count')
        self.replace_value_kind('count', 'attributeSignedIntegerValue')
        self.certify(claim, False)
        self.ev.write_json(self.path, {})
        self.source = JsonFacts(self.path)
        claim = self.attribute('bias')
        claim['attributeRecorded'][3] = 'os.time_zone.active_bias_minutes'
        self.certify(claim, False)

    def test_signed_values_work_in_atomic_same_subject_tuple(self):
        rows = [self.attribute(key)['attributeRecorded'] for key in self.roles]
        self.certify({'attributeTuple': rows})
        wrong = list(rows[0])
        wrong[2] = rows[4][2]
        self.certify({'attributeTuple': [wrong, rows[1]]}, False)

    def test_emitter_requires_native_int_and_only_reviewed_signed_roles_allow_negative(self):
        class IntSubclass(int):
            pass
        for bad in (True, False, -60.0, 1.0, '-60', None, IntSubclass(-60)):
            with self.subTest(value=repr(bad)), self.assertRaises(ValueError):
                emit_attribute(Evidence(), 'subject', 'os.time_zone.bias_minutes', bad,
                               1000000, artifact='fixture')
        for name, spec in ROLES.items():
            if spec.value_type == 'integer':
                with self.subTest(role=name), self.assertRaises(ValueError):
                    emit_attribute(Evidence(), 'subject', name, -1, 1000000, artifact='fixture')
        self.assertEqual(ROLES['account.count'].value_kind, 'attributeIntegerValue')
        self.assertEqual(ROLES['os.time_zone.bias_minutes'].value_kind, 'attributeSignedIntegerValue')

    def test_canonical_signed_encoding_is_exact(self):
        for text in ('-2147483648', '-60', '0', '60', '2147483647'):
            value = decode_value(text, 'signed_integer')
            self.assertIs(type(value), int)
            self.assertEqual(json.dumps(value), text)
        for bad in ('-0', '+1', '01', '-01', '1.0', '-1.0', '1e2', ' 1', '1\n',
                    'true', 'false', 'null', '"-60"', '', 1, True):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                decode_value(bad, 'signed_integer')
        with self.assertRaises(ValueError):
            decode_value('-1', 'integer')

    def test_malformed_signed_evidence_refuses_before_kernel_and_replay_fails_closed(self):
        raw = self.attribute('bias')
        cert = self.certify(raw)
        original = json.loads(self.path.read_text())
        value_id = raw['attributeRecorded'][2]
        aux = next(f for f in original['facts'] if f['id'] == value_id)['aux']
        for malformed in ('-0', '-060', '"-60"', '-60.0', 'false'):
            data = json.loads(json.dumps(original))
            data['strings'][str(aux)] = malformed
            self.path.write_text(json.dumps(data))
            self.source = JsonFacts(self.path)
            with patch.object(checker, 'run_kernel') as kernel:
                result = checker.check(raw, 'Malformed', self.source, out_dir=self.root)
            kernel.assert_not_called()
            self.assertEqual(result['status'], 'rejected')
            self.assertIn('not canonically encoded', result['reason'])
            self.assertTrue(verify(cert, self.source))

    def test_catalog_and_exact_kind_order_preserve_historical_prefix(self):
        self.assertEqual(hashlib.sha256(json.dumps(list(KINDS[:148]), separators=(',', ':')).encode()).hexdigest(),
                         '17f14463d440ccc27900e9cefbb3f4f5d1fdffcce8243d75ba77674a7090f6de')
        self.assertEqual(KINDS[148], 'attributeSignedIntegerValue')
        root = Path(__file__).resolve().parents[1]
        lean = (root/'lean/ChainOfProof/Facts.lean').read_text().split('inductive Kind where',1)[1].split('deriving DecidableEq',1)[0]
        lean_kinds = re.findall(r'\|\s*([A-Za-z][A-Za-z0-9_]*)', re.sub(r'--[^\n]*', '', lean))
        sql = (root/'extractor/schema.sql').read_text().split('CHECK (kind IN (',1)[1].split('))',1)[0]
        self.assertEqual(list(KINDS), lean_kinds)
        self.assertEqual(list(KINDS), re.findall(r"'([^']+)'", sql))
        self.assertEqual(len(KINDS), len(set(KINDS)))
        self.assertEqual(VALUE_TYPES['attributeSignedIntegerValue'], 'signed_integer')
        self.assertEqual(ROLES['document.container.path'].meaning, 'exact path of the validated OOXML document package')
        self.assertEqual(ROLES['document.container.format'].meaning,
                         'format identified by the validated OOXML package structure; not application execution')
        self.assertNotEqual(ROLES['document.source.path'].kind, ROLES['document.container.path'].kind)

    def test_recovered_mail_roles_preserve_literal_text_without_deletion_claim(self):
        self.ev = Evidence()
        keys = []
        for key, role, value in (
                ('recovered_subject', 'mail.recovered.subject_unicode', 'Recovered literal subject'),
                ('recovered_body', 'mail.recovered.body_unicode', '')):
            self.roles[key] = role
            keys.append(key)
            self.identities[key] = emit_attribute(self.ev, 'image:base:parser-recovery:item-17',
                role, value, 1000000, artifact='synthetic recovered PST item',
                source_snapshot='base-volume', source_variant='parser-recovery')
        self.ev.write_json(self.path, {})
        self.source = JsonFacts(self.path)
        rows = [self.attribute(key)['attributeRecorded'] for key in keys]
        certificate = self.certify({'attributeTuple': rows})
        self.assertIn('not proof of deletion, purge', certificate['english'])
        self.assertIn("''", certificate['english'])
        for record in certificate['cited_facts']:
            self.assertEqual(record['prov']['source_variant'], 'parser-recovery')
        wrong = list(rows[0])
        wrong[3] = 'mail.message.subject_unicode'
        self.certify({'attributeRecorded': wrong}, False)


if __name__ == '__main__':
    unittest.main()
