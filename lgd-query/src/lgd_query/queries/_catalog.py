"""Discover report query helpers and their name lookup dependencies."""

from importlib import import_module

DATASETS = (
    'states',
    'districts',
    'subdistricts',
    'villages',
    'blocks',
    'district_panchayats',
    'pri_local_bodies',
    'urban_local_bodies',
    'traditional_local_bodies',
    'urban_local_body_wards',
    'pri_local_body_wards',
    'villages_by_blocks',
    'gp_mapping',
    'tlb_villages',
    'statewise_ulbs_coverage',
    'parliament_constituencies',
    'assembly_constituencies',
    'constituency_coverage',
    'constituencies_mapping_pri',
    'constituencies_mapping_urban',
    'parliament_constituencies_lb_mapping',
    'pincode_villages',
    'pincode_urban',
    'invalidated_census_villages',
    'state_orgs',
    'central_orgs',
    'state_org_units',
    'central_org_units',
    'state_org_designations',
    'central_org_designations',
    'state_admin_depts',
    'central_admin_depts',
    'state_admin_dept_units',
    'central_admin_dept_units',
    'org_unit_details',
    'org_unit_coverage',
    'nofn_panchayats',
    'changes',
    'transactions',
)


def get(dataset):
    """Return the dataset's query module; unknown names fail before imports."""
    if dataset not in DATASETS:
        raise ValueError(f'No canned queries for dataset {dataset!r}')
    return import_module(f'{__package__}.{dataset}')


def required_datasets(dataset, *, field=None, include_entity_name=False, entity_name=None,
                      entity_name_status=None, is_null=None, is_blank=None):
    """Return all view names required for the selected query/search field."""
    module = get(dataset)
    if type(include_entity_name) is not bool:
        raise ValueError('include_entity_name must be a boolean')
    if dataset in ('state_org_units', 'central_org_units'):
        return module.required_datasets(field=field, include_entity_name=include_entity_name,
            entity_name=entity_name, entity_name_status=entity_name_status, is_null=is_null, is_blank=is_blank)
    if include_entity_name or entity_name_status is not None:
        raise ValueError('Name enrichment is supported for state_org_units and central_org_units')
    if hasattr(module, 'required_datasets'):
        return module.required_datasets(field=field)
    return (dataset,)


def sources(release, dataset, *, field=None, observed_on=None, include_entity_name=False,
            entity_name=None, entity_name_status=None, is_null=None, is_blank=None):
    """Resolve every query dependency from one already-pinned release.

    Returns Dataset objects so callers can inspect dates/status before opening
    views with lgd_query.connect(). An explicit date applies to every input.
    Pass field for search dependencies. Unit queries can also request location
    labels with include_entity_name=True, loading org_unit_details.
    """
    return tuple(release.dataset(name, observed_on=observed_on)
                 for name in required_datasets(dataset, field=field,
                     include_entity_name=include_entity_name, entity_name=entity_name,
                     entity_name_status=entity_name_status, is_null=is_null, is_blank=is_blank))
