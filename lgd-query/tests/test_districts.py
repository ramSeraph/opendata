"""District parent filters, ambiguous identifiers and standalone query access."""

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
from lgd_query.queries import districts
from test_reader import INDEX, PublicFiles


# Synthetic rows deliberately repeat names/census codes across different states.
ROWS = [
    ('1', 'Same District', '32', 'Kerala as supplied', '01', '101'),
    ('2', 'Same District', '33', 'TAMIL NADU', '01', '102'),
    ('559', 'Kollam', '32', 'Kerala', '02', '600'),
    ('560', 'Kollan', '33', 'Tamil Nadu', '02', '601'),
    ('900', "O'Brien_100%", '99', 'Unresolved parent', None, None),
    ('901', None, '32', None, None, None),
]


def populate(db):
    db.sql('''CREATE TABLE districts (
        district_code VARCHAR, district_name VARCHAR, state_code VARCHAR,
        state_name VARCHAR, district_census_2001_code VARCHAR,
        district_census_2011_code VARCHAR)''')
    db.executemany('INSERT INTO districts VALUES (?, ?, ?, ?, ?, ?)', ROWS)
    db.fetchall()


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class DistrictQueriesTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.db = duckdb.connect()
        self.addCleanup(self.db.close)
        populate(self.db)

    def codes(self, result):
        return [row[0] for row in result.fetchall()]

    def test_list_filters_only_by_reported_lgd_state_code(self):
        self.assertEqual(self.codes(districts.list(self.db)), ['559', '560', '900', '1', '2', '901'])
        self.assertEqual(self.codes(districts.list(self.db, state_code=32)), ['559', '1', '901'])
        self.assertEqual(self.codes(districts.list(self.db, state_code='99')), ['900'])
        self.assertEqual(self.codes(districts.list(self.db, state_code='999')), [])
        self.assertEqual(len(districts.list(self.db).columns), 6)

    def test_parent_names_are_never_replaced_by_the_states_report(self):
        # A loaded parent dataset must not silently change or eliminate rows.
        self.db.sql("CREATE TABLE states AS SELECT '32' AS state_code, 'Different name' AS state_name")
        self.assertEqual(districts.by_code(self.db, 1).fetchall(), [ROWS[0]])
        self.assertEqual(districts.by_code(self.db, '900').fetchall(), [ROWS[4]])
        self.assertEqual(len(districts.list(self.db).fetchall()), len(ROWS))

    def test_lgd_and_census_codes_are_not_conflated_and_ambiguity_is_retained(self):
        self.assertEqual(self.codes(districts.by_code(self.db, '1')), ['1'])
        self.assertEqual(self.codes(districts.by_code(self.db, '01')), [])
        self.assertEqual(self.codes(districts.by_census_code(self.db, '01', year=2001)), ['1', '2'])
        self.assertEqual(self.codes(districts.by_census_code(self.db, '01', year=2001, state_code='33')), ['2'])
        self.assertEqual(self.codes(districts.by_census_code(self.db, '01', year=2011)), [])
        self.assertEqual(self.codes(districts.by_census_code(self.db, '101', year=2011)), ['1'])
        self.assertEqual(self.codes(districts.by_census_code(self.db, '101', year=2011, state_code='33')), [])

    def test_exact_search_keeps_all_namesakes_and_uses_literal_text(self):
        self.assertEqual(self.codes(districts.search(self.db, ' SAME DISTRICT ', mode='exact')), ['1', '2'])
        self.assertEqual(self.codes(districts.search(self.db, 'same', mode='prefix', state_code=33)), ['2'])
        self.assertEqual(self.codes(districts.search(self.db, 'district', state_code=32)), ['1'])
        self.assertEqual(self.codes(districts.search(self.db, 'district', mode='prefix')), [])
        for name in ("O'Brien", '_', '%'):
            self.assertEqual(self.codes(districts.search(self.db, name)), ['900'])
        self.assertEqual(self.codes(districts.search(self.db, "' OR TRUE --")), [])
        self.assertEqual(len(districts.search(self.db, 'a', limit=None).fetchall()), 4)

    def test_parent_filter_and_distance_threshold_precede_limit(self):
        rows = districts.search(self.db, 'Kollam', mode='fuzzy', state_code='33', limit=1).fetchall()
        self.assertEqual([(r[0], r[-1]) for r in rows], [('560', 1)])
        self.assertEqual(districts.search(self.db, 'Kollam', mode='fuzzy', state_code='33',
                                          max_distance=0, limit=1).fetchall(), [])
        rows = districts.search(self.db, 'kolalm', mode='fuzzy', metric='damerau_levenshtein',
                                max_distance=1).fetchall()
        self.assertEqual([(r[0], r[-1]) for r in rows], [('559', 1)])
        rows = districts.search(self.db, 'kollam', mode='fuzzy').fetchall()
        self.assertEqual([(r[0], r[-1]) for r in rows], [('559', 0), ('560', 1)])

    def test_offline_connection_with_only_districts_supports_all_helpers(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            source = root/'source.parquet'
            self.db.sql('COPY districts TO ? (FORMAT PARQUET)', params=[str(source)])
            server = PublicFiles()
            release = Release.from_dict(server.index({'districts': server.dataset('districts', source.read_bytes())}))
            dataset = release.dataset('districts')
            cache = root/'cache'
            cache.mkdir()
            (cache/f'districts.{dataset.parquet.sha256}.parquet').write_bytes(source.read_bytes())
            with patch('lgd_query._http.urlopen', side_effect=AssertionError('Unexpected network access')):
                with connect([dataset], cache_dir=cache) as db:
                    self.assertEqual(len(districts.list(db).fetchall()), len(ROWS))
                    self.assertEqual(self.codes(districts.by_code(db, '559')), ['559'])
                    self.assertEqual(self.codes(districts.by_census_code(db, '01', year=2001)), ['1', '2'])
                    self.assertEqual(self.codes(districts.search(db, 'kolam', mode='fuzzy', state_code='32')), ['559'])
                    self.assertEqual(districts.list(db).project('district_code').filter("district_code='1'").fetchall(), [('1',)])


class DistrictValidationTests(unittest.TestCase):
    def test_bad_parent_codes_and_search_options_fail_before_sql(self):
        connection = Mock()
        cases = [
            lambda: districts.list(connection, state_code=True),
            lambda: districts.by_code(connection, -1),
            lambda: districts.by_census_code(connection, '01', year=2010),
            lambda: districts.by_census_code(connection, '01', year=2001, state_code='Kerala'),
            lambda: districts.search(connection, 'Kollam', state_code="32' OR TRUE"),
            lambda: districts.search(connection, ''),
            lambda: districts.search(connection, 'Kollam', limit=0),
            lambda: districts.search(connection, 'Kollam', max_distance=-1),
            lambda: districts.search(connection, 'Kollam', metric='unknown'),
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                case()
        connection.sql.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class DistrictCLIIntegrationTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.server = PublicFiles()
        with duckdb.connect() as db:
            populate(db)
            path = self.root/'source.parquet'
            db.sql('COPY districts TO ? (FORMAT PARQUET)', params=[str(path)])
        # Discovery deliberately contains no states dataset.
        self.server.index({'districts': self.server.dataset('districts', path.read_bytes())})
        self.enterContext(patch('lgd_query._http.urlopen', side_effect=self.server.open))

    def run_cli(self, *args, format='json'):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(['--metadata-url', INDEX, 'districts', *args,
                                       '--cache-dir', str(self.root/'cache'), '--format', format]), 0)
        return json.loads(output.getvalue()) if format == 'json' else output.getvalue()

    def test_all_commands_work_without_a_states_dataset(self):
        self.assertEqual([r[0] for r in self.run_cli('list', '--state-code', '32')['rows']], ['559', '1', '901'])
        self.assertEqual(self.run_cli('code', '559')['rows'][0][1], 'Kollam')
        self.assertEqual(self.run_cli('census-code', '01', '--year', '2001', '--state-code', '33')['rows'][0][0], '2')
        result = self.run_cli('search', 'kolam', '--mode', 'fuzzy', '--state-code', '32', '--limit', '1')
        self.assertEqual(result['columns'][-1], 'distance')
        self.assertEqual([(r[0], r[-1]) for r in result['rows']], [('559', 1)])
        self.assertEqual(self.server.requests.count(INDEX), 4)
        self.assertEqual(len(self.server.requests), 5)

    def test_freshness_guard_precedes_district_download(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            self.run_cli('list', '--observed-on', '2026-10-24')
        self.assertEqual(result.exception.code, 1)
        self.assertEqual(self.server.requests, [INDEX])

    @unittest.skipUnless(importlib.util.find_spec('rich'), 'Rich is optional')
    def test_table_and_empty_search_output(self):
        self.assertIn('Kollam', self.run_cli('code', '559', format='table'))
        self.assertEqual(self.run_cli('search', 'absent', '--mode', 'exact')['rows'], [])


if __name__ == '__main__':
    unittest.main()
