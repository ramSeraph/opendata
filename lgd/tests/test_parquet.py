"""Standalone report conversion tests: runnable with only the parquet extra."""

import csv
from datetime import date
import gzip
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from parquet.registry import SCHEMAS

AVAILABLE = importlib.util.find_spec('duckdb') is not None
if AVAILABLE:
    import duckdb
    from parquet import archive
    from parquet.convert import convert, write_parquet


class SchemaDocumentationTests(unittest.TestCase):
    def test_every_schema_has_an_accurate_field_table(self):
        directory = Path(__file__).resolve().parents[1]/'parquet/datasets'
        for dataset, fields in SCHEMAS.items():
            with self.subTest(dataset=dataset):
                document = (directory/f'{dataset}.md').read_text()
                rows = [line.split('|')[1:5] for line in document.splitlines()
                        if line.startswith('| ') and line.split('|')[1].strip().isdigit()]
                actual = [(int(i.strip()), n.strip().strip('`'), t.strip().strip('`'), h.strip().strip('`'))
                          for i, n, t, h in rows]
                self.assertEqual(actual, list(fields))


@unittest.skipUnless(AVAILABLE, 'install the parquet extra')
class ParquetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.connection = duckdb.connect(config={'threads': 1})
        self.addCleanup(self.connection.close)

    def record(self, dataset, **overrides):
        row = {name: ('2' if kind == 'INTEGER' else
                     '001' if name.endswith('_code') or name == 'transaction_id' else
                     'Name, "quoted"\nతెలుగు')
               for _, name, kind, _ in SCHEMAS[dataset]}
        if dataset == 'constituency_coverage':
            row.update(entity_type='Village', coverage_type='Fully Covered')
        if dataset == 'org_unit_details':
            row.update(entity_type='-1', organization_unit_specific_code='OMP BO')
        if dataset == 'org_unit_coverage':
            row.update(covered_entity_type='Village', coverage_type='F',
                       coverage_details_reported='true', organization_unit_specific_code='00123/BO')
        if dataset == 'changes':
            row.update(report_serial='1,003', report_date='04-03-2011')
        if dataset == 'transactions':
            row.update(transaction_date='30-Jan-2020')
        return row | overrides

    def source(self, dataset, rows, *, omitted=(), name=None, headers=None):
        fields = [field for field in SCHEMAS[dataset] if field[1] not in omitted]
        path = self.root / (name or f'{dataset}.csv')
        no_serial = dataset in ('changes', 'transactions', 'org_unit_coverage')
        with path.open('w', newline='') as output:
            writer = csv.writer(output)
            writer.writerow(([] if no_serial else ['S.No.']) +
                            [headers.get(f[3], f[3]) if headers else f[3] for f in fields])
            for number, row in enumerate(rows, 1):
                writer.writerow(([] if no_serial else [number]) + [row[f[1]] for f in fields])
        return path

    def read(self, output):
        return self.connection.execute('SELECT * FROM read_parquet(?)', [str(output)]).fetchall()

    def test_all_39_schemas_round_trip_values_types_and_field_ids(self):
        self.assertEqual(len(SCHEMAS), 39)
        for dataset, fields in SCHEMAS.items():
            with self.subTest(dataset=dataset):
                row = self.record(dataset)
                output = self.root / f'{dataset}.parquet'
                result = convert(dataset, self.source(dataset, [row]), output)
                expected = tuple(int(row[name]) if kind == 'INTEGER' else
                                 date(2011, 3, 4) if name == 'report_date' else
                                 date(2020, 1, 30) if name == 'transaction_date' else row[name]
                                 for _, name, kind, _ in fields)
                self.assertEqual(self.read(output), [expected])
                schema = self.connection.execute('DESCRIBE SELECT * FROM read_parquet(?)',
                                                 [str(output)]).fetchall()
                self.assertEqual([(r[0], r[1]) for r in schema], [(n, t) for _, n, t, _ in fields])
                identities = self.connection.execute('SELECT name, field_id FROM parquet_schema(?) '
                                                      'WHERE field_id IS NOT NULL', [str(output)]).fetchall()
                self.assertEqual(identities, [(n, i) for i, n, _, _ in fields])
                self.assertEqual((result['rows'], result['source_rows']), (1, 1))

    def test_optional_missing_fields_differ_from_supplied_blanks(self):
        output = self.root / 'states.parquet'
        row = self.record('states', state_name_local='')
        convert('states', self.source('states', [row]), output)
        self.assertEqual(self.read(output)[0][3], '')
        convert('states', self.source('states', [row], omitted={'state_name_local'}), output)
        self.assertIsNone(self.read(output)[0][3])

    def test_village_versions_categories_and_conflicts(self):
        row = self.record('villages', village_version='1', village_category='Rural')
        rows = [row, row | {'village_version': '2'}, row | {'village_category': 'Urban'}]
        output = self.root / 'villages.parquet'
        result = convert('villages', self.source('villages', rows), output)
        self.assertEqual((result['rows'], result['source_rows'], result['collapsed_rows']), (2, 3, 1))
        self.assertEqual({(r[1], r[5]) for r in self.read(output)}, {(2, 'Rural'), (1, 'Urban')})
        before = output.read_bytes()
        with self.assertRaisesRegex(ValueError, 'conflicting attributes'):
            convert('villages', self.source('villages', [row, row | {'village_name': 'Different'}]), output)
        self.assertEqual(output.read_bytes(), before)

    def test_pri_wards_keep_different_reported_parent_and_name_variants(self):
        row = self.record('pri_local_body_wards')
        rows = [row, row | {'local_body_name': 'Alternative body'}, row]
        output = self.root / 'wards.parquet'
        result = convert('pri_local_body_wards', self.source('pri_local_body_wards', rows), output)
        self.assertEqual((result['rows'], result['collapsed_rows']), (2, 1))

    def test_events_preserve_duplicates_and_conflicting_claims(self):
        for dataset in ('changes', 'transactions'):
            row = self.record(dataset)
            output = self.root / f'{dataset}.parquet'
            result = convert(dataset, self.source(dataset, [row, row]), output)
            self.assertEqual((result['rows'], result['collapsed_rows']), (2, 0))
            self.assertEqual(self.read(output)[0], self.read(output)[1])

    def test_organization_coverage_preserves_claims_placeholders_variants_and_duplicates(self):
        row = self.record('org_unit_coverage', covered_entity_name='Kathaghar "A", Colony\nతెలుగు',
                          entity_code='0', state_code='0', state_name='India')
        placeholder = row | dict(covered_entity_code='', covered_entity_name='', covered_entity_type='',
                                 coverage_type='', coverage_details_reported='false')
        incomplete = row | dict(covered_entity_name='', covered_entity_type='')
        alternative = row | dict(coverage_type='P', organization_unit_name='Alternative source label')
        another_selection = row | dict(report_organization_level_code='002')
        rows = [row, row, placeholder, incomplete, alternative, another_selection]
        output = self.root/'coverage.parquet'
        result = convert('org_unit_coverage', self.source('org_unit_coverage', rows), output)
        self.assertEqual((result['rows'], result['source_rows'], result['collapsed_rows']), (6, 6, 0))
        from collections import Counter
        expected = [tuple(row[n] for _, n, _, _ in SCHEMAS['org_unit_coverage']) for row in rows]
        self.assertEqual(Counter(self.read(output)), Counter(expected))

    def test_organization_coverage_rejects_inconsistent_claims_and_incomplete_schemas(self):
        row = self.record('org_unit_coverage')
        output = self.root/'coverage.parquet'
        convert('org_unit_coverage', self.source('org_unit_coverage', [row]), output)
        before = output.read_bytes()
        for change in ({'coverage_details_reported': 'false'}, {'coverage_details_reported': 'True'},
                       {'covered_entity_code': ''}, {'covered_entity_code': 'missing'},
                       {'coverage_type': ''}, {'coverage_type': 'Unknown'},
                       {'organization_unit_code': ''}, {'state_code': 'unknown'},
                       {'report_organization_level_code': ''}, {'entity_code': 'unknown'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                convert('org_unit_coverage', self.source('org_unit_coverage', [row | change]), output)
            self.assertEqual(output.read_bytes(), before)
        for omitted in ('covered_entity_type', 'report_organization_level_code'):
            with self.subTest(omitted=omitted), self.assertRaisesRegex(ValueError, 'Missing'):
                convert('org_unit_coverage', self.source('org_unit_coverage', [row], omitted={omitted}), output)
        with self.assertRaisesRegex(ValueError, 'Unknown or duplicate'):
            convert('org_unit_coverage', self.source('org_unit_coverage', [row],
                    headers={'Covered Entity Type': 'Unexpected Type'}), output)
        with self.assertRaisesRegex(ValueError, 'Unknown or duplicate'):
            convert('org_unit_coverage', self.source('org_unit_coverage', [row],
                    headers={'Covered Entity Type': 'Coverage Type'}), output)
        with self.assertRaisesRegex(ValueError, 'Empty organization coverage'):
            convert('org_unit_coverage', self.source('org_unit_coverage', []), output)
        self.assertEqual(output.read_bytes(), before)

    def test_organization_coverage_handles_quotes_after_an_unquoted_csv_prefix(self):
        row = {n: ('001' if n.endswith('_code') else 'Name') for _, n, _, _ in SCHEMAS['org_unit_coverage']}
        row.update(coverage_type='', coverage_details_reported='false', covered_entity_code='',
                   covered_entity_name='', covered_entity_type='')
        # The real report first needs CSV quoting after DuckDB's sniffing sample.
        # Repeated rows also exercise intentional preservation of multiplicity.
        claim = row | dict(coverage_details_reported='true', coverage_type='F', covered_entity_code='002',
                           covered_entity_type='Village', covered_entity_name='Joshi Colony, "A"\nతెలుగు')
        source = self.source('org_unit_coverage', [row]*25000 + [claim])
        output = self.root/'coverage.parquet'
        result = convert('org_unit_coverage', source, output)
        self.assertEqual(result['rows'], 25001)
        self.assertEqual(self.connection.execute('SELECT covered_entity_name FROM read_parquet(?) '
                         "WHERE coverage_details_reported='true'", [str(output)]).fetchall(),
                         [('Joshi Colony, "A"\nతెలుగు',)])

    def test_missing_constituency_prefix_is_reported_without_inventing_rows(self):
        source = self.source('parliament_constituencies', [self.record('parliament_constituencies')])
        with source.open(newline='') as stream:
            rows = list(csv.reader(stream))
        rows[1][0] = '81'
        with source.open('w', newline='') as stream:
            csv.writer(stream).writerows(rows)
        result = convert('parliament_constituencies', source, self.root/'pc.parquet')
        self.assertEqual(result['rows'], 1)
        self.assertEqual(result['source_layout']['missing_prefix_rows'], 80)

    def test_rejected_headers_and_values_preserve_previous_output(self):
        output = self.root/'states.parquet'
        row = self.record('states')
        convert('states', self.source('states', [row]), output)
        before = output.read_bytes()
        for source in (self.source('states', [row], name='bad-header.csv', headers={'State Code': 'Unknown'}),
                       self.source('states', [row | {'state_version': '1.5'}], name='fraction.csv'),
                       self.source('states', [], name='empty.csv')):
            with self.subTest(source=source), self.assertRaises(ValueError):
                convert('states', source, output)
            self.assertEqual(output.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.lgd-parquet-*')), [])

    def test_interrupted_write_preserves_existing_parquet_and_cleans_temporary(self):
        output = self.root/'states.parquet'
        output.write_bytes(b'previous generation')

        class BrokenConnection:
            def execute(self, sql):
                # Simulate an output having been created before COPY fails.
                import re
                path = re.search(r" TO '([^']+)'", sql)[1]
                Path(path).write_bytes(b'incomplete')
                raise OSError('disk full')

        with self.assertRaisesRegex(OSError, 'disk full'):
            write_parquet(BrokenConnection(), 'states', 'entity_incoming', output)
        self.assertEqual(output.read_bytes(), b'previous generation')
        self.assertEqual(list(self.root.glob('.*.tmp')), [])

    def test_gzip_and_plain_reports_have_same_logical_source_and_values(self):
        source = self.source('transactions', [self.record('transactions')])
        compressed = source.with_suffix('.csv.gz')
        with gzip.open(compressed, 'wb') as stream:
            stream.write(source.read_bytes())
        a = convert('transactions', source, self.root/'a.parquet')
        b = convert('transactions', compressed, self.root/'b.parquet')
        self.assertEqual(a['source']['csv_sha256'], b['source']['csv_sha256'])
        self.assertEqual(self.read(self.root/'a.parquet'), self.read(self.root/'b.parquet'))

    def test_nonseekable_csv_preserves_quoted_records_across_batches(self):
        from parquet.csv_input import report

        class Fragmented(io.RawIOBase):
            def __init__(self, data):
                self.data = io.BytesIO(data)

            def readable(self):
                return True

            def readinto(self, buffer):
                # Split UTF-8 code points, quotes and line endings across reads.
                chunk = self.data.read(min(3, len(buffer)))
                buffer[:len(chunk)] = chunk
                return len(chunk)

        rows = [('001', ''), ('002', 'Name, "quoted"\nతెలుగు'), ('001', ''),
                ('003', 'x' * 150000)]
        text = io.StringIO(newline='')
        writer = csv.writer(text, delimiter=';')
        writer.writerow(['Code', 'Name'])
        writer.writerows(rows)
        with io.BufferedReader(Fragmented(text.getvalue().encode('utf-8-sig'))) as stream:
            with patch('parquet.csv_input.BATCH_ROWS', 2), report(stream) as source:
                source.load(self.connection, 'streamed')
        self.assertEqual(self.connection.execute('SELECT * FROM streamed').fetchall(), rows)

    def test_bad_csv_after_a_complete_batch_preserves_previous_output(self):
        output = self.root/'states.parquet'
        source = self.source('states', [self.record('states')]*3)
        convert('states', source, output)
        before = output.read_bytes()
        original = source.read_bytes()
        for tail in (b'1,too,few\n', b'1,"unterminated\n'):
            source.write_bytes(original + tail)
            with patch('parquet.csv_input.BATCH_ROWS', 2), self.assertRaises(ValueError):
                convert('states', source, output)
            self.assertEqual(output.read_bytes(), before)
            self.assertEqual(list(self.root.glob('.lgd-parquet-*')), [])

    @unittest.skipUnless(shutil.which('7z'), '7z required')
    def test_multi_member_archive_requires_selection_and_checks_crc(self):
        first = self.source('states', [self.record('states')], name='states.01Jan2024.csv')
        second = self.source('states', [self.record('states', state_code='002')], name='states.02Jan2024.csv')
        source = self.root/'states.Jan2024.7z'
        subprocess.run(['7z', 'a', str(source), first.name, second.name],
                       cwd=self.root, check=True, capture_output=True)
        output = self.root/'states.parquet'
        with self.assertRaisesRegex(ValueError, 'several reports'):
            convert('states', source, output)
        # Archive conversion must never create or read a gzip intermediate.
        with patch('gzip.open', side_effect=AssertionError('Unexpected gzip staging')):
            result = convert('states', source, output, member=second.name)
        self.assertEqual(self.read(output)[0][0], '002')
        self.assertEqual(result['source']['member'], second.name)
        entries = archive.members(source)
        before = output.read_bytes()
        for size_delta, crc_mask in ((0, 1), (1, 0), (-1, 0)):
            corrupted = [(name, size + size_delta, crc ^ crc_mask) for name, size, crc in entries]
            with patch('parquet.archive.members', return_value=corrupted):
                with self.assertRaisesRegex(ValueError, 'corrupt archive|extra archive data'):
                    convert('states', source, output, member=second.name)
            self.assertEqual(output.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.lgd-parquet-*')), [])

        # A complete-looking CSV is insufficient if the extractor exits badly.
        popen = subprocess.Popen
        def failing_extractor(args, **kwargs):
            return popen([sys.executable, '-c',
                          'import pathlib,sys; sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes()); '
                          'sys.exit(2)', str(second)], **kwargs)
        with patch('parquet.archive.subprocess.Popen', side_effect=failing_extractor), \
                patch('parquet.archive.members', return_value=entries), \
                self.assertRaisesRegex(ValueError, 'corrupt archive'):
            convert('states', source, output, member=second.name)
        self.assertEqual(output.read_bytes(), before)

    def test_cli_runs_without_history_iceberg_or_pyarrow(self):
        isolated = self.root/'isolated'
        isolated.mkdir()
        package = Path(__file__).resolve().parents[1]/'parquet'
        shutil.copytree(package, isolated/'parquet', ignore=shutil.ignore_patterns('__pycache__'))
        script = '''
import importlib.abc, runpy, sys
class BlockHistory(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('history', 'pyiceberg', 'pyarrow'):
            raise ImportError('Standalone converter must not import ' + fullname)
sys.meta_path.insert(0, BlockHistory())
sys.path.insert(0, sys.argv.pop(1))
sys.argv = ['parquet', *sys.argv[1:]]
runpy.run_module('parquet', run_name='__main__')
'''
        for dataset in ('states', 'org_unit_coverage'):
            with self.subTest(dataset=dataset):
                source = self.source(dataset, [self.record(dataset)])
                result = subprocess.run([sys.executable, '-I', '-c', script, str(isolated),
                                         dataset, str(source), str(self.root/'isolated.parquet')],
                                        cwd=isolated, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['rows'], 1)


if __name__ == '__main__':
    unittest.main()
