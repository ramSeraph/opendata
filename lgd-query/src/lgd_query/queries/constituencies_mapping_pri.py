"""Queries for constituencies_mapping_pri; retain supplied rows and report columns.

See docs/datasets/constituencies_mapping_pri.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, NameLookup, Spec
from . import _eci


_queries = DatasetQueries(Spec(
    dataset='constituencies_mapping_pri',
    columns=(
        'village_code',
        'village_name',
        'village_census_2011_code',
        'local_body_code',
        'local_body_name',
        'block_code',
        'block_name',
        'subdistrict_code',
        'subdistrict_name',
        'subdistrict_census_2011_code',
        'district_code',
        'district_name',
        'district_census_2011_code',
        'parliament_constituency_code',
        'parliament_constituency_name',
        'parliament_constituency_eci_code',
        'assembly_constituency_code',
        'assembly_constituency_name',
        'assembly_constituency_eci_code',
        'state_code',
        'constituency_level',
        'constituency_code',
    ),
    primary_code='village_code', primary_name='village_name',
    order=('state_code', 'district_code', 'subdistrict_code', 'village_code', 'village_census_2011_code', 'local_body_code', 'block_code', 'subdistrict_census_2011_code', 'district_census_2011_code', 'parliament_constituency_code', 'parliament_constituency_eci_code', 'assembly_constituency_code', 'assembly_constituency_eci_code'),
    local_name=None,
    signed=(), integers=(),
    lookups=(
        ('state_name', NameLookup('states', 'state_name', (('state_code', 'state_code'),))),
    ),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
by_census_code = _queries.by_census_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years


eci_levels = _eci.LEVELS


def eci_codes(connection, *, level, constituency_code=None, state_code=None, eci_code=None):
    """Look up reported ECI codes; inspect the source date and ambiguity flags.

    Values are source claims for the selected observation, not independently
    verified electoral identifiers. See the dataset guide for dated-view usage.
    """
    return _eci.lookup(connection, 'constituencies_mapping_pri', level=level,
        constituency_code=constituency_code, state_code=state_code, eci_code=eci_code)
