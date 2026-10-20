import unittest

import common
import constants
from test_division_reports import entity, item


class ClaimTests(unittest.TestCase):
    def test_item_relationships_skip_ended_and_unknown_claims(self):
        readers = {
            'P31': common.get_instance_of_ids,
            'P131': common.get_located_in_ids,
            'P150': common.get_contains_ids,
            'P3403': common.get_coextensive_ids,
            'P3179': common.get_overlap_ids,
        }
        for prop, reader in readers.items():
            with self.subTest(prop=prop):
                record = entity('Q1', 'Example', {prop: [item(10), item(11), item(12)]})
                claims = record['claims'][prop]
                claims[1]['qualifiers'] = {
                    'P582': [{'datavalue': {'value': {'time': '+2000-01-01T00:00:00Z'}}}]
                }
                claims[2]['qualifiers'] = {'P582': [{'snaktype': 'novalue'}]}
                claims.extend(
                    [
                        {'rank': 'normal', 'mainsnak': {'snaktype': 'somevalue'}},
                        {'rank': 'normal', 'mainsnak': {'snaktype': 'novalue'}},
                    ]
                )
                self.assertEqual(reader(record), [10, 12])
                for inactive_prop in ['P576', 'P1366']:
                    record['claims'][inactive_prop] = []
                    self.assertEqual(reader(record), [])
                    del record['claims'][inactive_prop]

    def test_instance_filter_rejects_missing_proposed_and_ended_types(self):
        self.assertFalse(common.is_current_instance_of({}, [constants.STATE_ID]))
        record = entity('Q1', 'Example', {'P31': [item(constants.STATE_ID)]})
        self.assertTrue(common.is_current_instance_of(record, [constants.STATE_ID]))
        record['claims']['P31'][0]['qualifiers'] = {
            'P582': [{'datavalue': {'value': {'time': '+2000-01-01T00:00:00Z'}}}],
        }
        self.assertFalse(common.is_current_instance_of(record, [constants.STATE_ID]))
        record = entity(
            'Q1',
            'Example',
            {
                'P31': [item(constants.STATE_ID), item(constants.PROPOSED_ENTITY)],
            },
        )
        self.assertFalse(common.is_current_instance_of(record, [constants.STATE_ID]))

    def test_lgd_codes_use_the_selected_property_and_skip_unknown_values(self):
        record = entity('Q1', 'Example', {'P12746': ['123'], 'P6425': ['456']})
        record['claims']['P12746'].append({'mainsnak': {'snaktype': 'somevalue'}})
        self.assertEqual(common.get_lgd_codes(record, 'district'), ['123'])
        self.assertEqual(common.get_lgd_codes(record), ['456'])
        self.assertEqual(common.get_lgd_codes({}, 'state'), [])
        with self.assertRaisesRegex(ValueError, 'unknown LGD type'):
            common.get_lgd_codes(record, 'typo')

    def test_reverse_mapping_only_resolves_unique_codes(self):
        self.assertEqual(
            common.invert_lgd_mapping(
                {
                    'Q1': '9',
                    'Q2': '6',
                    'Q3': '6',
                    'Q4': 'NA',
                    'Q5': 'NA',
                }
            ),
            {'9': 'Q1'},
        )

    def test_coordinates_include_latitude(self):
        record = entity('Q1', 'Example', {'P625': [{'longitude': 77.2, 'latitude': 28.6}]})
        self.assertEqual(common.get_coordinates(record), [[77.2, 28.6]])

if __name__ == '__main__':
    unittest.main()
