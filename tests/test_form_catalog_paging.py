"""V3 static catalog pages are exact, complete, bounded and arm-neutral."""
from collections import defaultdict
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from agent import form_catalog_views as views
from agent.answer_projection import tool_catalog


def all_rows(section, **filters):
    rows, offset, token, pages = [], 0, None, 0
    while True:
        result = views.forms_page(section=section, offset=offset, page_size=100, state_token=token, **filters)
        assert len(json.dumps(result).encode('utf-8')) <= 64000
        page = result['page']; rows.extend(page['items']); pages += 1
        assert page['returned'] == len(page['items'])
        if page['next_offset'] is None:
            assert len(rows) == page['total']
            return rows, result, pages
        assert page['next_offset'] == offset + page['returned'] and page['returned'] > 0
        offset, token = page['next_offset'], result['state_token']


def reconstruct(rows):
    values, fragments = [], defaultdict(list)
    for row in rows:
        if 'value' in row:
            values.append((row['path'], row['value']))
        else:
            fragments[tuple(row['path'])].append(row)
    for path, parts in fragments.items():
        offset, text = 0, ''
        for row in sorted(parts, key=lambda part: part['offset']):
            assert row['offset'] == offset and row['length'] == len(row['fragment'])
            text += row['fragment']; offset += row['length']
        assert offset == parts[0]['total_length']
        values.append((list(path), json.loads(text)))
    result = {}
    for path, value in values:
        node = result
        for index, token in enumerate(path):
            last = index == len(path) - 1
            if isinstance(node, list):
                while len(node) <= token: node.append(None)
                if last: node[token] = value
                elif node[token] is None: node[token] = [] if type(path[index + 1]) is int else {}
            elif last: node[token] = value
            else: node.setdefault(token, [] if type(path[index + 1]) is int else {})
            if not last: node = node[token]
    return result


class FormCatalogPaging(unittest.TestCase):
    def test_all_sections_reconstruct_every_signature_selector_role_and_metadata(self):
        claim, answer = views._catalogs()
        expected = {'claim_forms': {'forms': claim['forms']}, 'answer_fields': {'forms': answer['forms']},
                    'attribute_roles': {'attribute_roles': answer['attribute_roles']},
                    'metadata': {source: {key: value for key, value in catalog.items()
                                         if key not in ('forms', 'attribute_roles')}
                                 for source, catalog in (('claim_catalog', claim), ('answer_catalog', answer))}}
        for section in views.SECTIONS:
            rows, response, _ = all_rows(section)
            self.assertEqual(reconstruct(rows), expected[section])
            self.assertEqual(response['counts'][section], len(rows))
        self.assertEqual(len(expected['attribute_roles']['attribute_roles']), views.forms_page()['attribute_role_count'])

    def test_named_lookup_and_tokens_bind_section_filter_and_full_catalog(self):
        for form in ('attributeTuple', 'filesystemSetDeleted'):
            rows, _, _ = all_rows('claim_forms', form=form)
            self.assertTrue(rows)
            self.assertTrue(all(row['path'][1] == form for row in rows))
            rows, _, _ = all_rows('answer_fields', form=form)
            self.assertEqual(reconstruct(rows), {'forms': {form: tool_catalog()['forms'][form]}})
        role = next(iter(tool_catalog()['attribute_roles']))
        rows, _, _ = all_rows('attribute_roles', role=role)
        self.assertEqual(reconstruct(rows), {'attribute_roles': {role: tool_catalog()['attribute_roles'][role]}})
        first = views.forms_page(section='answer_fields', page_size=1)
        for request in [dict(section='metadata'), dict(section='answer_fields', form='attributeTuple')]:
            with self.assertRaisesRegex(ValueError, 'stale or belongs'):
                views.forms_page(state_token=first['state_token'], **request)
        claim, answer = views._catalogs(); claim['how'] += ' Static metadata revision.'
        with patch.object(views, '_catalogs', return_value=(claim, answer)), self.assertRaisesRegex(ValueError, 'stale'):
            views.forms_page(section='answer_fields', offset=1, state_token=first['state_token'])

    def test_exact_oversize_scalar_fragments_are_not_preview_descriptors(self):
        claim, answer = views._catalogs()
        role = next(iter(answer['attribute_roles']))
        meaning = ('Synthetic semantic "definition" \\ with Unicode snowman \u2603. ' * 1000)
        answer['attribute_roles'][role]['meaning'] = meaning
        with patch.object(views, '_catalogs', return_value=(claim, answer)):
            rows, response, pages = all_rows('attribute_roles', role=role)
        self.assertGreater(pages, 1)
        self.assertTrue(any(row.get('encoding') == 'json-ascii-fragment' for row in rows))
        self.assertEqual(reconstruct(rows)['attribute_roles'][role]['meaning'], meaning)
        self.assertNotIn('omitted_oversize_value', json.dumps(response))

    def test_requests_and_unbounded_static_definitions_fail_explicitly(self):
        for kwargs in [dict(section='other'), dict(section=[]), dict(offset=True), dict(offset=-1),
                       dict(page_size=True), dict(page_size=0), dict(page_size=101), dict(state_token='x' * 64),
                       dict(offset=1), dict(form=''), dict(form=[]), dict(role='unknown'), dict(form='unknown'),
                       dict(form='attributeTuple', role='os.product_name'),
                       dict(section='metadata', form='attributeTuple')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): views.forms_page(**kwargs)
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            views.forms_page(offset=100000, state_token=views.forms_page()['state_token'])
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            views._fragments(['metadata'], 'x' * 1048577)
        self.assertEqual(views.forms_page(offset=views.forms_page()['page']['total'],
            state_token=views.forms_page()['state_token'])['page']['items'], [])
