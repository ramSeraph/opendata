"""Subdistrict queries preserve reported hierarchy, versions and ambiguity."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from lgd_query import Release, connect
from lgd_query import cli
from lgd_query.queries import subdistricts
from test_reader import INDEX, PublicFiles


ROWS = [
    ('100', 3, 'Central', '559', 'Kollam supplied', '32', 'Kerala supplied', '01', '00100'),
    ('101', 7, 'Central', '560', 'Kottayam supplied', '32', 'Kerala', '01', '00101'),
    ('102', 1, 'Central', '600', 'Elsewhere', '33', 'Tamil Nadu', '01', '00102'),
    ('103', 9, 'Kollam', '559', 'Kollam', '32', 'Kerala', '02', '00540'),
    ('104', 2, 'Kollan', '560', 'Kottayam', '32', 'Kerala', '02', '00541'),
    ('105', 2, 'Kollan', '600', 'Elsewhere', '33', 'Tamil Nadu', '02', '00542'),
    ('900', 1, "O'Brien_100%", '999', 'Absent district', '99', 'Absent state', None, None),
    ('901', 1, None, '559', None, '32', None, None, None),
]


def populate(db):
    db.sql('''CREATE TABLE subdistricts (
        subdistrict_code VARCHAR, subdistrict_version INTEGER, subdistrict_name VARCHAR,
        district_code VARCHAR, district_name VARCHAR, state_code VARCHAR,
        state_name VARCHAR, subdistrict_census_2001_code VARCHAR,
        subdistrict_census_2011_code VARCHAR)''')
    db.executemany('INSERT INTO subdistricts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', ROWS)
    db.fetchall()


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class SubdistrictQueriesTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.db = duckdb.connect()
        self.addCleanup(self.db.close)
        populate(self.db)

    def codes(self, relation):
        return [row[0] for row in relation.fetchall()]

    def test_both_parent_filters_apply_to_reported_codes(self):
        self.assertEqual(self.codes(subdistricts.list(self.db)), [r[0] for r in ROWS])
        self.assertEqual(self.codes(subdistricts.list(self.db, state_code=32)), ['100', '101', '103', '104', '901'])
        self.assertEqual(self.codes(subdistricts.list(self.db, district_code=559)), ['100', '103', '901'])
        self.assertEqual(self.codes(subdistricts.list(self.db, state_code='32', district_code='559')), ['100', '103', '901'])
        self.assertEqual(self.codes(subdistricts.list(self.db, state_code='33', district_code='559')), [])
        self.assertEqual(self.codes(subdistricts.list(self.db, district_code='404')), [])

    def test_version_and_parent_names_remain_as_supplied(self):
        self.db.sql("CREATE TABLE states AS SELECT '32' AS state_code, 'Different state' AS state_name")
        self.db.sql("""CREATE TABLE districts AS SELECT '559' AS district_code,
            '33' AS state_code, 'Different district' AS district_name""")
        self.assertEqual(subdistricts.by_code(self.db, '100').fetchall(), [ROWS[0]])
        self.assertEqual(subdistricts.by_code(self.db, 101).fetchall(), [ROWS[1]])
        self.assertEqual(subdistricts.by_code(self.db, '900').fetchall(), [ROWS[6]])
        self.assertEqual(len(subdistricts.list(self.db).columns), 9)
        self.assertEqual(len(subdistricts.list(self.db).fetchall()), len(ROWS))

    def test_census_namespaces_leading_zeros_and_ambiguous_codes(self):
        self.assertEqual(self.codes(subdistricts.by_code(self.db, '00100')), [])
        self.assertEqual(self.codes(subdistricts.by_census_code(self.db, '00100', year=2011)), ['100'])
        self.assertEqual(self.codes(subdistricts.by_census_code(self.db, 100, year=2011)), [])
        self.assertEqual(self.codes(subdistricts.by_census_code(self.db, '01', year=2001)), ['100', '101', '102'])
        self.assertEqual(self.codes(subdistricts.by_census_code(self.db, '01', year=2011)), [])
        self.assertEqual(self.codes(subdistricts.by_census_code(self.db, '01', year=2001, state_code='32')), ['100', '101'])
        self.assertEqual(self.codes(subdistricts.by_census_code(self.db, '01', year=2001, district_code='560')), ['101'])
        self.assertEqual(self.codes(subdistricts.by_census_code(self.db, '01', year=2001,
                                                               state_code='32', district_code='600')), [])

    def test_same_names_and_literal_searches_are_not_collapsed(self):
        self.assertEqual(self.codes(subdistricts.search(self.db, ' CENTRAL ', mode='exact')), ['100', '101', '102'])
        self.assertEqual(self.codes(subdistricts.search(self.db, 'central', state_code=32, district_code=560)), ['101'])
        self.assertEqual(self.codes(subdistricts.search(self.db, 'Cent', mode='prefix', district_code=559)), ['100'])
        self.assertEqual(self.codes(subdistricts.search(self.db, 'tral', mode='prefix')), [])
        for name in ("O'Brien", '_', '%'):
            self.assertEqual(self.codes(subdistricts.search(self.db, name)), ['900'])
        self.assertEqual(self.codes(subdistricts.search(self.db, "' OR TRUE --")), [])

    def test_both_parent_filters_and_threshold_precede_fuzzy_limit(self):
        result = subdistricts.search(self.db, 'Kollam', mode='fuzzy', state_code='32',
                                     district_code='560', limit=1).fetchall()
        self.assertEqual([(r[0], r[-1]) for r in result], [('104', 1)])
        self.assertEqual(subdistricts.search(self.db, 'Kollam', mode='fuzzy', state_code='32',
                                            district_code='560', limit=1, max_distance=0).fetchall(), [])
        self.assertEqual(subdistricts.search(self.db, 'Kollam', mode='fuzzy', state_code='33',
                                            district_code='560', limit=1).fetchall(), [])
        result = subdistricts.search(self.db, 'kolalm', district_code='559', mode='fuzzy',
                                     metric='damerau_levenshtein', max_distance=1).fetchall()
        self.assertEqual([(r[0], r[-1]) for r in result], [('103', 1)])

    def test_offline_helpers_work_with_only_subdistricts_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root/'source.parquet'
            self.db.sql('COPY subdistricts TO ? (FORMAT PARQUET)', params=[str(path)])
            server = PublicFiles()
            release = Release.from_dict(server.index({'subdistricts': server.dataset('subdistricts', path.read_bytes())}))
            dataset = release.dataset('subdistricts')
            cache = root/'cache'
            cache.mkdir()
            (cache/f'subdistricts.{dataset.parquet.sha256}.parquet').write_bytes(path.read_bytes())
            with patch('lgd_query._http.urlopen', side_effect=AssertionError('Unexpected network access')):
                with connect([dataset], cache_dir=cache) as db:
                    self.assertEqual(len(subdistricts.list(db).fetchall()), len(ROWS))
                    self.assertEqual(self.codes(subdistricts.by_code(db, '103')), ['103'])
                    self.assertEqual(self.codes(subdistricts.by_census_code(db, '01', year=2001)), ['100', '101', '102'])
                    self.assertEqual(self.codes(subdistricts.search(db, 'kolam', mode='fuzzy', district_code='559')), ['103'])
                    self.assertEqual(subdistricts.list(db).project('subdistrict_code').filter("subdistrict_code='100'").fetchall(), [('100',)])


class SubdistrictValidationTests(unittest.TestCase):
    def test_invalid_parent_filters_fail_before_sql(self):
        connection = Mock()
        for options in ({'district_code': True}, {'district_code': ''}, {'state_code': -1},
                        {'district_code': 'Kollam'}, {'state_code': '32', 'district_code': "559' OR TRUE"}):
            for operation in (
                lambda: subdistricts.list(connection, **options),
                lambda: subdistricts.by_census_code(connection, '01', year=2001, **options),
                lambda: subdistricts.search(connection, 'Central', **options),
            ):
                with self.subTest(options=options), self.assertRaises(ValueError):
                    operation()
        with self.assertRaises(ValueError):
            subdistricts.by_census_code(connection, '01', year=2021)
        with self.assertRaises(ValueError):
            subdistricts.by_code(connection, False)
        connection.sql.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class SubdistrictCLIIntegrationTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.server = PublicFiles()
        with duckdb.connect() as db:
            populate(db)
            path = self.root/'source.parquet'
            db.sql('COPY subdistricts TO ? (FORMAT PARQUET)', params=[str(path)])
        self.server.index({'subdistricts': self.server.dataset('subdistricts', path.read_bytes())})
        self.enterContext(patch('lgd_query._http.urlopen', side_effect=self.server.open))

    def run_cli(self, *args, format='json'):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(['--metadata-url', INDEX, 'subdistricts', *args,
                                       '--cache-dir', str(self.root/'cache'), '--format', format]), 0)
        return json.loads(output.getvalue()) if format == 'json' else output.getvalue()

    def test_all_commands_work_without_parent_datasets(self):
        result = self.run_cli('list', '--state-code', '32', '--district-code', '559')
        self.assertEqual([r[0] for r in result['rows']], ['100', '103', '901'])
        self.assertEqual(len(result['columns']), 9)
        self.assertEqual(self.run_cli('code', '101')['rows'][0][1], 7)
        result = self.run_cli('census-code', '01', '--year', '2001', '--district-code', '560')
        self.assertEqual([r[0] for r in result['rows']], ['101'])
        result = self.run_cli('search', 'kolam', '--state-code', '32', '--district-code', '559',
                              '--mode', 'fuzzy', '--limit', '1')
        self.assertEqual(result['columns'][-1], 'distance')
        self.assertEqual([(r[0], r[-1]) for r in result['rows']], [('103', 1)])
        self.assertEqual(self.server.requests.count(INDEX), 4)
        self.assertEqual(len(self.server.requests), 5)

    def test_mismatching_parent_filters_return_empty_and_freshness_is_checked(self):
        self.assertEqual(self.run_cli('list', '--state-code', '33', '--district-code', '559')['rows'], [])
        self.server.requests.clear()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            self.run_cli('list', '--observed-on', '2026-10-24')
        self.assertEqual(result.exception.code, 1)
        self.assertEqual(self.server.requests, [INDEX])

    @unittest.skipUnless(importlib.util.find_spec('rich'), 'Rich is optional')
    def test_table_output(self):
        self.assertIn('Kollam', self.run_cli('code', '103', format='table'))


if __name__ == '__main__':
    unittest.main()
