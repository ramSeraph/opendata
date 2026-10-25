"""Queries for constituency_coverage; retain supplied rows and report columns.

See docs/datasets/constituency_coverage.md for identifiers, filters and dependencies.
"""

from ._signatures import bind, bind_entities
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='constituency_coverage',
    columns=(
        'entity_code',
        'entity_name',
        'entity_type',
        'parliament_constituency_code',
        'parliament_constituency_name',
        'assembly_constituency_code',
        'assembly_constituency_name',
        'coverage_type',
        'state_code',
        'state_name',
        'constituency_level',
        'constituency_code',
    ),
    primary_code='entity_code', primary_name='entity_name',
    order=('state_code', 'entity_code', 'parliament_constituency_code', 'assembly_constituency_code'),
    local_name=None,
    signed=(), integers=(),
    typed_code=True,
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years


# These are LGD namespaces, not interchangeable numeric IDs. Local bodies and
# wards can be supplied by several registers; no source wins by lookup order.
_ENTITY_TABLES = {
    'District': (('districts', 'district_code', 'district_name'),),
    'SubDistrict': (('subdistricts', 'subdistrict_code', 'subdistrict_name'),),
    'Village': (('villages', 'village_code', 'village_name'),),
    'Localbody': (
        ('urban_local_bodies', 'local_body_code', 'local_body_name'),
        ('pri_local_bodies', 'local_body_code', 'local_body_name'),
        ('traditional_local_bodies', 'local_body_code', 'local_body_name'),
    ),
    'Ward': (
        ('urban_local_body_wards', 'ward_code', 'ward_name'),
        ('pri_local_body_wards', 'ward_code', 'ward_name'),
    ),
}
entity_types = tuple(_ENTITY_TABLES)


def _entity_tables(entity_type):
    if not isinstance(entity_type, str) or entity_type not in _ENTITY_TABLES:
        raise ValueError(f'entity_type must be one of: {", ".join(entity_types)}')
    return _ENTITY_TABLES[entity_type]


def required_entity_datasets(entity_type):
    """Views needed to follow coverage claims of this type to entity records."""
    return ('constituency_coverage', *(row[0] for row in _entity_tables(entity_type)))


def entity_sources(release, entity_type, *, observed_on=None):
    """Resolve the coverage report and target registers from one pinned release.

    Inspect each Dataset's date/status before connect(). An explicit date guard
    applies to every input; an unavailable register fails before downloading.
    """
    return tuple(release.dataset(name, observed_on=observed_on)
                 for name in required_entity_datasets(entity_type))


def entities(connection, *, entity_type, **filters):
    """Return register records referenced by matching coverage claims.

    Filters apply to constituency_coverage. Joins use the typed LGD entity code
    and state code, never the reported name. Returns entity_dataset, entity_type,
    entity_code and entity_name followed by every field from the register.
    Multiple registers use UNION ALL BY NAME, filling absent columns with NULL.

    Repeated/contradictory coverage claims do not multiply entity records. Every
    matching register variant is retained, including village categories and
    duplicate source rows. Unmatched claims return no entity record; list() and
    by_code() still expose those claims. This lookup does not adjudicate their
    coverage flags or establish a relationship at another observation date.
    """
    tables = _entity_tables(entity_type)
    condition, params = _queries._conditions(dict(filters, entity_type=entity_type))
    branches = []
    for dataset, code_column, name_column in tables:
        # Identifiers and the type literal come exclusively from our allowlist.
        branches.append(f'''SELECT '{dataset}' AS entity_dataset,
            '{entity_type}' AS entity_type, n.{code_column} AS entity_code,
            n.{name_column} AS entity_name, n.* FROM {dataset} n
            WHERE EXISTS (SELECT 1 FROM selected_entities s
                WHERE s.entity_code=n.{code_column} AND s.state_code=n.state_code
                  AND NULLIF(trim(s.entity_code), '') IS NOT NULL AND s.entity_code<>'0')''')
    sql = f'''WITH selected_entities AS (
        SELECT DISTINCT t.entity_code,t.state_code FROM constituency_coverage t WHERE {condition}
    ) SELECT * FROM ({' UNION ALL BY NAME '.join(branches)}) resolved
    ORDER BY entity_type,entity_code,state_code,entity_dataset,entity_name'''
    return connection.sql(sql, params=params)


entities = bind_entities(_queries, entities, type_annotation='str')
