"""Queries for traditional_local_bodies; retain supplied rows and report columns.

See docs/datasets/traditional_local_bodies.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, NameLookup, Spec


_queries = DatasetQueries(Spec(
    dataset='traditional_local_bodies',
    columns=(
        'local_body_code',
        'local_body_version',
        'local_body_name',
        'local_body_name_local',
        'local_body_type_code',
        'local_body_type_name',
        'district_panchayat_code',
        'intermediate_panchayat_code',
        'state_code',
        'state_name',
        'local_body_level',
    ),
    primary_code='local_body_code', primary_name='local_body_name',
    order=('state_code', 'local_body_code', 'local_body_type_code', 'district_panchayat_code', 'intermediate_panchayat_code'),
    local_name='local_body_name_local',
    signed=(), integers=('local_body_version',),
    lookups=tuple(
        # These source parent fields can reference either body register. Keep
        # every matching label; the report does not identify a preferred source.
        (field, tuple(NameLookup(
            dataset, 'local_body_name', ((parent, 'local_body_code'), ('state_code', 'state_code')),
            nonzero_keys=(parent,),
        ) for dataset in ('traditional_local_bodies', 'pri_local_bodies')))
        for field, parent in (
            ('district_panchayat_name', 'district_panchayat_code'),
            ('intermediate_panchayat_name', 'intermediate_panchayat_code'),
        )
    ),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
