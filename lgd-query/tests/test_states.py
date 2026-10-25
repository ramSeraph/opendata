"""State query behavior, identifier namespaces and CLI integration."""

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
from lgd_query.queries import states
from test_reader import INDEX, PublicFiles


ROWS = [
    ('1', 1, 'Jammu and Kashmir', '', '01', '01', 'U'),
    ('7', 1, 'Delhi', None, '07', '07', 'U'),
    ('32', 1, 'Kerala', 'കേരളം', '032', '32', 'S'),
    ('33', 1, 'Tamil Nadu', 'தமிழ்நாடு', '33', '33', 'S'),
    ('90', 1, "O'Brien_100%", 'École', '99', '99', 'S'),
    ('91', 1, 'Keral', None, '99', '99', 'X'),
]


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class StateQueriesTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.db = duckdb.connect()
        self.addCleanup(self.db.close)
        self.db.sql('''CREATE TABLE states (
            state_code VARCHAR, state_version INTEGER, state_name VARCHAR,
            state_name_local VARCHAR, state_census_2001_code VARCHAR,
            state_census_2011_code VARCHAR, state_or_ut VARCHAR)''')
        self.db.executemany('INSERT INTO states VALUES (?, ?, ?, ?, ?, ?, ?)', ROWS)
        # DuckDB 2 requires execute() results to be consumed before later work.
        self.db.fetchall()

    def codes(self, relation):
        return [row[0] for row in relation.fetchall()]

    def test_list_keeps_original_columns_and_unknown_classification(self):
        relation = states.list(self.db)
        self.assertEqual(len(relation.columns), 7)
        self.assertEqual(self.codes(relation), ['7', '1', '91', '32', '90', '33'])
        self.assertEqual(self.codes(states.list(self.db, kind='state')), ['32', '90', '33'])
        self.assertEqual(self.codes(states.list(self.db, kind='ut')), ['7', '1'])
        self.assertEqual(self.codes(relation), ['7', '1', '91', '32', '90', '33'])

    def test_lgd_codes_and_census_years_are_separate_namespaces(self):
        self.assertEqual(states.by_code(self.db, 32).fetchall(), [ROWS[2]])
        self.assertEqual(self.codes(states.by_code(self.db, '01')), [])
        self.assertEqual(self.codes(states.by_code(self.db, '404')), [])
        self.assertEqual(self.codes(states.by_census_code(self.db, '01', year=2011)), ['1'])
        self.assertEqual(self.codes(states.by_census_code(self.db, '032', year=2001)), ['32'])
        self.assertEqual(self.codes(states.by_census_code(self.db, '032', year=2011)), [])
        self.assertEqual(self.codes(states.by_census_code(self.db, '99', year=2011)), ['91', '90'])

    def test_name_search_normalizes_comparison_but_preserves_source_text(self):
        result = states.search(self.db, ' KERALA ', mode='exact').fetchall()
        self.assertEqual(result, [ROWS[2]])
        self.assertEqual(self.codes(states.search(self.db, 'tamil', mode='prefix')), ['33'])
        self.assertEqual(self.codes(states.search(self.db, 'NADU')), ['33'])
        self.assertEqual(self.codes(states.search(self.db, 'nadu', mode='prefix')), [])
        self.assertEqual(self.codes(states.search(self.db, 'E\u0301COLE', mode='exact', field='local')), ['90'])
        self.assertEqual(self.codes(states.search(self.db, 'தமிழ்', field='local')), ['33'])
        self.assertEqual(self.codes(states.search(self.db, 'Delhi', field='local')), [])

    def test_literal_search_does_not_interpret_wildcards_or_sql(self):
        for term in ("O'Brien", '_', '%'):
            self.assertEqual(self.codes(states.search(self.db, term)), ['90'])
        self.assertEqual(self.codes(states.search(self.db, "' OR 1=1 --")), [])
        self.assertEqual(len(states.list(self.db).fetchall()), len(ROWS))

    def test_fuzzy_distance_threshold_metric_sorting_and_limits(self):
        result = states.search(self.db, 'kerla', mode='fuzzy').fetchall()
        self.assertEqual([(r[0], r[-1]) for r in result], [('32', 1), ('91', 2)])
        self.assertEqual(self.codes(states.search(self.db, 'kerla', mode='fuzzy', kind='state')), ['32'])
        self.assertEqual(self.codes(states.search(self.db, 'kerla', mode='fuzzy', limit=1)), ['32'])
        self.assertEqual(self.codes(states.search(self.db, 'Kerala', mode='fuzzy', max_distance=0)), ['32'])
        self.assertEqual(self.codes(states.search(self.db, 'delih', mode='fuzzy', max_distance=1)), [])
        result = states.search(self.db, 'delih', mode='fuzzy', max_distance=1,
                               metric='damerau_levenshtein').fetchall()
        self.assertEqual([(r[0], r[-1]) for r in result], [('7', 1)])
        self.assertEqual(len(states.search(self.db, 'a', limit=None).fetchall()), 4)

    def test_relations_remain_composable_and_do_not_close_callers_connection(self):
        relation = states.list(self.db, kind='state')
        self.assertEqual(relation.project('state_code').filter("state_code = '32'").fetchall(), [('32',)])
        self.assertEqual(self.db.sql('SELECT 1').fetchall(), [(1,)])

    def test_helpers_need_only_a_states_view_and_do_not_resolve_or_download(self):
        import duckdb
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            parquet = root/'states.parquet'
            self.db.sql('COPY states TO ? (FORMAT PARQUET)', params=[str(parquet)])
            server = PublicFiles()
            release = Release.from_dict(server.index({'states': server.dataset('states', parquet.read_bytes())}))
            dataset = release.dataset('states')
            cache = root/'cache'
            cache.mkdir()
            (cache/f'states.{dataset.parquet.sha256}.parquet').write_bytes(parquet.read_bytes())
            with patch('lgd_query._http.urlopen', side_effect=AssertionError('Unexpected network access')):
                with connect([dataset], cache_dir=cache) as db:
                    self.assertIsInstance(states.list(db), duckdb.DuckDBPyRelation)
                    self.assertEqual(self.codes(states.by_code(db, '32')), ['32'])
                    self.assertEqual(self.codes(states.search(db, 'delih', mode='fuzzy',
                                                            metric='damerau_levenshtein')), ['7'])


class StateQueryValidationTests(unittest.TestCase):
    def test_invalid_inputs_fail_before_sql(self):
        connection = Mock()
        cases = [
            lambda: states.list(connection, kind='territory'),
            lambda: states.by_census_code(connection, '01', year=2021),
            lambda: states.by_census_code(connection, '01', year='2011'),
        ]
        cases += [lambda value=v: states.by_code(connection, value)
                  for v in (None, True, -1, 32.0, '', ' 32 ', '३२', "32' OR TRUE")]
        cases += [lambda value=v: states.search(connection, value) for v in ('', '  ', None)]
        cases += [lambda options=o: states.search(connection, 'Kerala', **options) for o in (
            {'kind': 'x'}, {'mode': 'unknown'}, {'field': 'state_code'}, {'metric': 'sql()'},
            {'max_distance': -1}, {'max_distance': True}, {'max_distance': 1.5},
            {'limit': 0}, {'limit': -1}, {'limit': True},
        )]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                case()
        connection.sql.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class StatesCLIIntegrationTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.server = PublicFiles()
        with duckdb.connect() as db:
            db.sql('''CREATE TABLE states (
                state_code VARCHAR, state_version INTEGER, state_name VARCHAR,
                state_name_local VARCHAR, state_census_2001_code VARCHAR,
                state_census_2011_code VARCHAR, state_or_ut VARCHAR)''')
            db.executemany('INSERT INTO states VALUES (?, ?, ?, ?, ?, ?, ?)', ROWS)
            db.fetchall()
            path = self.root/'source.parquet'
            db.sql('COPY states TO ? (FORMAT PARQUET)', params=[str(path)])
        self.server.index({'states': self.server.dataset('states', path.read_bytes())})
        self.enterContext(patch('lgd_query._http.urlopen', side_effect=self.server.open))

    def run_cli(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(['--metadata-url', INDEX, 'states', *args,
                                       '--cache-dir', str(self.root/'cache'), '--format', 'json']), 0)
        return json.loads(output.getvalue())

    def test_all_state_commands_use_only_the_selected_states_dataset(self):
        self.assertEqual(len(self.run_cli('list', '--kind', 'ut')['rows']), 2)
        self.assertEqual(self.run_cli('code', '32')['rows'][0][2], 'Kerala')
        self.assertEqual(self.run_cli('census-code', '01', '--year', '2011')['rows'][0][0], '1')
        result = self.run_cli('search', 'kerla', '--mode', 'fuzzy', '--max-distance', '1')
        self.assertEqual(result['columns'][-1], 'distance')
        self.assertEqual([(r[0], r[-1]) for r in result['rows']], [('32', 1)])
        self.assertEqual(self.server.requests.count(INDEX), 4)
        self.assertEqual(len(self.server.requests), 5)  # One Parquet download reused by all four commands.

    def test_freshness_guard_precedes_data_download(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            self.run_cli('list', '--observed-on', '2026-10-24')
        self.assertEqual(result.exception.code, 1)
        self.assertEqual(self.server.requests, [INDEX])


if __name__ == '__main__':
    unittest.main()
