"""Reviewed row identities and normalization, without any history dependencies."""

import csv
import unittest

from tests import test_parquet as helpers


@unittest.skipUnless(helpers.AVAILABLE, 'install the parquet extra')
class LiveNormalizationTests(unittest.TestCase):
    setUp = helpers.ParquetTests.setUp
    record = helpers.ParquetTests.record
    source = helpers.ParquetTests.source
    read = helpers.ParquetTests.read

    def convert(self, dataset, rows, **options):
        return helpers.convert(dataset, self.source(dataset, rows),
                               self.root/f'{dataset}.parquet', **options)

    def test_removed_key_fields_cannot_hide_conflicting_attributes(self):
        cases = {
            'parliament_constituencies': ('parliament_constituency_code', 'state_code'),
            'assembly_constituencies': ('assembly_constituency_code', 'parliament_constituency_code'),
            'district_panchayats': ('district_panchayat_code', 'state_code'),
            'gp_mapping': ('village_code', 'subdistrict_code'),
            'pincode_villages': ('village_code', 'district_code'),
            'pincode_urban': ('local_body_code', 'state_code'),
            'invalidated_census_villages': ('village_code', 'state_code'),
            'state_orgs': ('organization_code', 'state_code'),
            'state_org_units': ('organization_unit_code', 'organization_code'),
            'central_org_units': ('organization_unit_code', 'organization_code'),
            'org_unit_details': ('organization_unit_code', 'organization_code'),
            'state_admin_depts': ('administrative_unit_level_code', 'state_code'),
            'central_admin_dept_units': ('administrative_unit_code', 'administrative_unit_level_code'),
            'state_admin_dept_units': ('administrative_unit_code', 'state_code'),
            'constituencies_mapping_urban': ('ward_code', 'local_body_code'),
        }
        for dataset, (identity, attribute) in cases.items():
            with self.subTest(dataset=dataset):
                row = self.record(dataset)
                result = self.convert(dataset, [row, row, row | {identity: '002'}])
                self.assertEqual((result['rows'], result['collapsed_rows']), (2, 1))
                output = self.root/f'{dataset}.parquet'
                before = output.read_bytes()
                with self.assertRaisesRegex(ValueError, 'conflicting attributes'):
                    self.convert(dataset, [row, row | {attribute: '002'}])
                self.assertEqual(output.read_bytes(), before)

    def test_designation_level_names_distinguish_assignments_but_organization_does_not(self):
        for dataset in ('state_org_designations', 'central_org_designations'):
            with self.subTest(dataset=dataset):
                row = self.record(dataset)
                result = self.convert(dataset, [row, row | {'organization_level_name': 'Other level'}])
                self.assertEqual(result['rows'], 2)
                with self.assertRaisesRegex(ValueError, 'conflicting attributes'):
                    self.convert(dataset, [row, row | {'organization_code': '002'}])

    def test_coverage_conflicts_preserve_original_claims_as_evidence(self):
        for dataset, flags in (('constituency_coverage', ('Fully Covered', 'Partly Covered')),
                               ('parliament_constituencies_lb_mapping', ('F', 'P'))):
            with self.subTest(dataset=dataset):
                row = self.record(dataset, coverage_type=flags[0])
                result = self.convert(dataset, [row, row, row | {'coverage_type': flags[1]}])
                self.assertEqual((result['rows'], result['collapsed_rows'],
                                  result['conflicting_coverage_rows']), (1, 2, 1))
                self.assertEqual(self.connection.execute('SELECT coverage_type FROM read_parquet(?)',
                    [result['output']['path']]).fetchall(), [(None,)])
                self.assertEqual(set(self.connection.execute(
                    'SELECT coverage_type FROM read_parquet(?)',
                    [result['discrepancy_evidence']['path']]).fetchall()), {(flag,) for flag in flags})
                attribute = 'state_code' if dataset.endswith('lb_mapping') else 'parliament_constituency_code'
                with self.assertRaisesRegex(ValueError, 'conflicting attributes'):
                    self.convert(dataset, [row, row | {attribute: '002'}])
        row = self.record('parliament_constituencies_lb_mapping', coverage_type='')
        with self.assertRaisesRegex(ValueError, 'Blank coverage conflicts'):
            self.convert('parliament_constituencies_lb_mapping', [row, row | {'coverage_type': 'F'}])

    def test_typed_constituency_keys_keep_parliament_only_and_assembly_links(self):
        for dataset in ('constituency_coverage', 'constituencies_mapping_pri'):
            with self.subTest(dataset=dataset):
                row = self.record(dataset)
                result = self.convert(dataset, [row, row | {'assembly_constituency_code': '',
                                                             'assembly_constituency_name': ''}])
                actual = self.connection.execute('SELECT constituency_level,constituency_code '
                    'FROM read_parquet(?) ORDER BY ALL', [result['output']['path']]).fetchall()
                self.assertEqual(actual, [('assembly', '001'), ('parliament', '001')])

    def test_placeholder_rows_are_counted_but_not_entities(self):
        for dataset, blanks in (
            ('gp_mapping', dict(village_code='', village_name='', village_census_2001_code='',
                                village_census_2011_code='', local_body_code='', local_body_name='')),
            ('assembly_constituencies', dict(assembly_constituency_code='', assembly_constituency_name='')),
        ):
            with self.subTest(dataset=dataset):
                row = self.record(dataset)
                result = self.convert(dataset, [row, row | blanks])
                self.assertEqual((result['rows'], result['ignored_source_rows'], result['collapsed_rows']), (1, 1, 0))

    def test_ignored_columns_do_not_split_otherwise_identical_records(self):
        for dataset, headers in (
            ('tlb_villages', ['Gram Panchayat/ TLB Census 2011 Code']),
            ('villages_by_blocks', ['District Code of Development Block',
                                   'District Name of Development Block (In English)']),
        ):
            with self.subTest(dataset=dataset):
                row = self.record(dataset)
                source = self.source(dataset, [row, row])
                with source.open(newline='') as stream:
                    values = list(csv.reader(stream))
                values[0].extend(headers)
                values[1].extend(['10'] * len(headers))
                values[2].extend(['20'] * len(headers))
                with source.open('w', newline='') as stream:
                    csv.writer(stream).writerows(values)
                result = helpers.convert(dataset, source, self.root/f'{dataset}.parquet')
                self.assertEqual((result['rows'], result['collapsed_rows']), (1, 1))
                self.assertEqual(len(result['omitted_source_fields']), len(headers))

    def test_pri_mapping_name_conflict_requires_and_uses_a_dated_register(self):
        dataset = 'constituencies_mapping_pri'
        row = self.record(dataset)
        rows = [row, row | {'local_body_name': 'Alternate spelling'}]
        with self.assertRaisesRegex(ValueError, 'dated --pri-reference'):
            self.convert(dataset, rows)
        reference = self.convert('pri_local_bodies', [self.record('pri_local_bodies', local_body_name='Registered name')])
        result = self.convert(dataset, rows, observed_on='2022-01-30',
            pri_reference=reference['output']['path'], reference_observed_on='2022-01-30')
        self.assertEqual((result['rows'], result['collapsed_rows']), (1, 1))
        self.assertEqual(result['discrepancy_evidence']['rows'], 2)
        self.assertEqual(self.connection.execute('SELECT local_body_name FROM read_parquet(?)',
            [result['output']['path']]).fetchall(), [('Registered name',)])


if __name__ == '__main__':
    unittest.main()
