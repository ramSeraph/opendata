"""Queries for constituencies_mapping_urban; retain supplied rows and report columns.

See docs/datasets/constituencies_mapping_urban.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, NameLookup, Spec
from . import _eci


_queries = DatasetQueries(Spec(
    dataset='constituencies_mapping_urban',
    columns=(
        'ward_code',
        'ward_name',
        'local_body_code',
        'local_body_name',
        'local_body_type_name',
        'parliament_constituency_code',
        'parliament_constituency_name',
        'parliament_constituency_eci_code',
        'assembly_constituency_code',
        'assembly_constituency_name',
        'assembly_constituency_eci_code',
        'district_code',
        'district_name',
        'subdistrict_code',
        'subdistrict_name',
        'state_code',
    ),
    primary_code='ward_code', primary_name='ward_name',
    order=('state_code', 'district_code', 'subdistrict_code', 'ward_code', 'local_body_code', 'parliament_constituency_code', 'parliament_constituency_eci_code', 'assembly_constituency_code', 'assembly_constituency_eci_code'),
    local_name=None,
    signed=(), integers=(),
    lookups=(
        ('state_name', NameLookup('states', 'state_name', (('state_code', 'state_code'),))),
    ),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years


eci_levels = _eci.LEVELS


def eci_codes(connection, *, level, constituency_code=None, state_code=None, eci_code=None):
    """Look up the selected urban report's ECI claims, retaining ambiguity."""
    return _eci.lookup(connection, 'constituencies_mapping_urban', level=level,
        constituency_code=constituency_code, state_code=state_code, eci_code=eci_code)
