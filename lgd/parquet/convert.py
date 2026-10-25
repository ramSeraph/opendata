"""Convert a single source report; no history database or catalog is needed."""

from contextlib import contextmanager
from datetime import date, datetime
import gzip
import io
from pathlib import Path
import tempfile
import uuid
import re

import duckdb

from . import archive, events, villages, org_coverage
from .administrative import AdministrativeReport
from .common import file_hash, sql_identifier, sql_string
from .registry import SCHEMAS
from .schema import schema_id


@contextmanager
def source_report(path, member=None):
    path = Path(path).resolve()
    source = {'path': str(path), 'sha256': file_hash(path), 'member': None}
    if path.suffix == '.7z':
        entries = archive.members(path)
        if member is None and len(entries) != 1:
            raise ValueError('Archive contains several reports; select one with --member')
        selected = [entry for entry in entries if member is None or entry[0] == member]
        if len(selected) != 1:
            raise ValueError(f'Archive does not contain the requested member: {member}')
        source['member'] = selected[0][0]
        with archive.stream_member(path, selected[0]) as (stream, checked):
            yield stream, source
        source['csv_sha256'] = checked.digest.hexdigest()
    else:
        if member is not None:
            raise ValueError('--member is only valid for a 7z archive')
        if path.suffix not in ('.csv', '.gz'):
            raise ValueError('Expected a CSV, gzip-compressed CSV, or 7z archive')
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rb') as raw:
            checked = archive.DigestReader(raw)
            with io.BufferedReader(checked) as stream:
                yield stream, source
            if not checked.eof:
                raise ValueError('CSV report was not fully consumed')
            source['csv_sha256'] = checked.digest.hexdigest()


def load_report(connection, dataset, path, *, observed_on=None):
    """Return the canonical temporary table and source diagnostics."""
    if dataset == 'villages':
        headers, mapping, identity, count = villages.load_source(connection, path)
        raw_count = connection.execute('SELECT count(*) FROM village_source').fetchone()[0]
        connection.execute('DROP TABLE village_source')
        table, extra = 'village_incoming', {}
    elif dataset == 'org_unit_coverage':
        headers, mapping, identity, count, raw_count = org_coverage.load_source(connection, path)
        table, extra = 'organization_coverage_incoming', {}
    elif dataset in events.SCHEMAS:
        headers, count = events.load_csv(connection, dataset, path)
        mapping = {name: header for _, name, _, header in events.SCHEMAS[dataset]}
        identity, raw_count, table, extra = schema_id(mapping), count, 'event_rows', {}
    else:
        backend = AdministrativeReport(dataset)
        headers, mapping, identity, count = backend.load_source(connection, path, observed_on=observed_on)
        raw_count, table = backend.source_row_count, 'entity_incoming'
        extra = {'ignored_embedded_header_rows': backend.embedded_header_rows}
        if dataset in ('villages_by_blocks', 'tlb_villages'):
            extra['omitted_source_fields'] = sorted(set(mapping) - set(backend.columns))
        if dataset in ('gp_mapping', 'assembly_constituencies'):
            extra['ignored_source_rows'] = backend.ignored_source_rows
        if dataset == 'pri_local_body_wards':
            extra.update(backend.ward_resolution)
        if dataset in ('constituency_coverage', 'parliament_constituencies_lb_mapping'):
            extra['conflicting_coverage_rows'] = backend.conflicting_coverage_rows
        if dataset == 'constituencies_mapping_pri':
            extra['conflicting_name_rows'] = backend.conflicting_name_rows
        if hasattr(backend, 'constituency_layout'):
            extra['source_layout'] = backend.constituency_layout
    return table, dict(source_headers=headers, supplied_fields=sorted(mapping),
                       source_schema_id=identity, source_rows=raw_count, rows=count,
                       collapsed_rows=raw_count-count-extra.get('ignored_source_rows', 0)-extra.get('unresolved_source_rows', 0), **extra)


def write_parquet(connection, dataset, table, output):
    """Write canonical fields atomically, using stable Parquet field IDs."""
    fields = SCHEMAS[dataset]
    columns = ', '.join(sql_identifier(name) for _, name, _, _ in fields)
    date_field = events.DATE_FIELDS.get(dataset)
    order = ([date_field] if date_field else []) + [name for _, name, _, _ in fields if name != date_field]
    ordered = ', '.join(sql_identifier(name) for name in order)
    ids = ', '.join(f'{sql_identifier(name)}: {i}' for i, name, _, _ in fields)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f'.{output.name}.{uuid.uuid4().hex}.tmp')
    try:
        connection.execute(f'COPY (SELECT {columns} FROM {sql_identifier(table)} ORDER BY {ordered}) '
                           f'TO {sql_string(temporary)} '
                           f'(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 122880, FIELD_IDS {{{ids}}})')
        count = connection.execute('SELECT count(*) FROM read_parquet(?)', [str(temporary)]).fetchone()[0]
        result = dict(path=str(output), rows=count, bytes=temporary.stat().st_size,
                      sha256=file_hash(temporary))
        temporary.replace(output)
        return result
    finally:
        temporary.unlink(missing_ok=True)


def convert(dataset, source, output, *, member=None, memory_limit='512MB',
            max_temp_size='2GB', threads=2, observed_on=None,
            pri_reference=None, reference_observed_on=None):
    if dataset not in SCHEMAS:
        raise ValueError(f'Unknown dataset: {dataset}')
    source, output = Path(source).resolve(), Path(output).resolve()
    if observed_on is not None and not isinstance(observed_on, date):
        observed_on = date.fromisoformat(observed_on)
    if observed_on is None:
        match = re.search(r'\.([0-9]{2}[A-Z][a-z]{2}[0-9]{4})\.csv(?:\.|$)', member or source.name)
        if match:
            observed_on = datetime.strptime(match[1], '%d%b%Y').date()
    if source == output:
        raise ValueError('Input and output must be different files')
    reference = None
    if pri_reference is not None:
        if dataset not in ('pri_local_body_wards', 'constituencies_mapping_pri') or observed_on is None or reference_observed_on is None:
            raise ValueError('PRI references require both the report and reference observation dates')
        reference_day = (reference_observed_on if isinstance(reference_observed_on, date)
                         else date.fromisoformat(reference_observed_on))
        if reference_day > observed_on:
            raise ValueError('Cannot use a future PRI register to resolve historical names')
        pri_reference = Path(pri_reference).resolve()
        reference = dict(path=str(pri_reference), observed_on=str(reference_day), sha256=file_hash(pri_reference))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Only DuckDB spill needs temporary disk space; input CSV bytes are streamed.
    with tempfile.TemporaryDirectory(prefix='.lgd-parquet-', dir=output.parent) as temp:
        with duckdb.connect(config={'threads': threads, 'memory_limit': memory_limit,
                                    'temp_directory': str(Path(temp) / 'spill'),
                                    'max_temp_directory_size': max_temp_size}) as connection:
            if reference:
                connection.read_parquet(str(pri_reference)).create_view('pri_ward_reference')
            with source_report(source, member) as (stream, provenance):
                table, diagnostics = load_report(connection, dataset, stream, observed_on=observed_on)
            # Leaving source_report verifies EOF, size, CRC and extractor status.
            # No final output is replaced until every extraction check passes.
            if dataset in ('pri_local_body_wards', 'constituency_coverage', 'constituencies_mapping_pri',
                           'parliament_constituencies_lb_mapping'):
                evidence_table = ('pri_ward_discrepancies' if dataset == 'pri_local_body_wards'
                                  else 'pri_mapping_discrepancies' if dataset == 'constituencies_mapping_pri'
                                  else 'constituency_coverage_discrepancies')
                if dataset in ('pri_local_body_wards', 'constituencies_mapping_pri'):
                    diagnostics['name_reference'] = reference
                evidence_available = connection.execute(
                    'SELECT count(*) FROM duckdb_tables() WHERE table_name=?', [evidence_table]).fetchone()[0]
                if evidence_available and (dataset == 'pri_local_body_wards' or connection.execute(
                        f'SELECT count(*) FROM {evidence_table}').fetchone()[0]):
                    temporary = output.with_name('.'+output.stem+'.discrepancies.'+uuid.uuid4().hex+'.tmp')
                    try:
                        connection.execute(f'''COPY (SELECT * FROM {evidence_table} ORDER BY ALL)
                            TO {sql_string(temporary)} (FORMAT PARQUET,COMPRESSION ZSTD)''')
                        evidence = output.with_name(output.stem+'.discrepancies.'+file_hash(temporary)[:16]+'.parquet')
                        temporary.replace(evidence)
                    finally:
                        temporary.unlink(missing_ok=True)
                    diagnostics['discrepancy_evidence'] = dict(path=str(evidence),
                        rows=connection.execute(f'SELECT count(*) FROM {evidence_table}').fetchone()[0],
                        sha256=file_hash(evidence),bytes=evidence.stat().st_size)
            result = write_parquet(connection, dataset, table, output)
    return dict(dataset=dataset, source=provenance, output=result, **diagnostics)
