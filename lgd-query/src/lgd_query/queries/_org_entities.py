"""Follow organization location/coverage references to typed LGD registers.

The numeric location types are administrative level codes, not constituency
coverage's textual entity types. Organization state is report scope, not a
restriction on the geographic location of its offices or coverage targets.
"""

import re


_GEOGRAPHY = {
    1: ('states', 'state_code', 'state_name'),
    2: ('districts', 'district_code', 'district_name'),
    3: ('subdistricts', 'subdistrict_code', 'subdistrict_name'),
    4: ('villages', 'village_code', 'village_name'),
    5: ('blocks', 'block_code', 'block_name'),
}
_BODY_TYPES = {
    'District Panchayat': 1,
    'Intermediate Panchayat': 2,
    'Village Panchayat': 3,
    'Municipal Corporations': 4,
    'Municipality': 5,
    'Notified Area Council': 6,
    'Town Panchayat': 7,
    'Cantonment Board': 8,
}
_COVERAGE_TYPES = dict(zip(('State', 'District', 'Subdistrict', 'Village', 'Block'), _GEOGRAPHY))
_BODIES = ('pri_local_bodies', 'urban_local_bodies', 'traditional_local_bodies')


class OrganizationEntityQueries:
    """Resolve references selected from one organization report.

    Results contain full register records, not office/claim rows. Missing and
    unknown references remain inspectable in the report's list/by_code APIs.
    """

    def __init__(self, queries, *, coverage=False):
        self.queries = queries
        self.dataset = queries.spec.dataset
        self.coverage = coverage
        self.entity_type_filter = 'covered_entity_type' if coverage else 'entity_type'

    def _type(self, value):
        if self.coverage:
            if not isinstance(value, str):
                raise ValueError('covered_entity_type must be source text')
            return value
        value = str(value) if type(value) is int else value
        if not isinstance(value, str) or not re.fullmatch(r'-?[0-9]+', value):
            raise ValueError('entity_type must be signed integer text')
        return value

    def _targets(self, value):
        """Return (dataset, code, name, condition, type_matches) SQL definitions.

        Only package-owned SQL appears here. Caller values are always bound.
        """
        if self.coverage:
            number = _COVERAGE_TYPES.get(value)
            body_type = _BODY_TYPES.get(value)
        else:
            number = int(value)
            body_type = -number if -8 <= number <= -1 else None
        if body_type is not None:
            # Local bodies share a code namespace. Retain a changed body type
            # or register membership, explicitly exposing the disagreement.
            matches = f"try_cast(nullif(trim(n.local_body_type_code), '') AS INTEGER) = {body_type}"
            return tuple((name, 'local_body_code', 'local_body_name', 'TRUE', matches)
                         for name in _BODIES)
        if number in _GEOGRAPHY:
            return ((*_GEOGRAPHY[number], 'TRUE', 'TRUE'),)
        if not self.coverage and number > 5:
            targets = []
            for scope in ('state', 'central'):
                if self.dataset == 'state_org_units' and scope == 'central':
                    continue
                if self.dataset == 'central_org_units' and scope == 'state':
                    continue
                condition = 'n.administrative_unit_level_code = s.entity_type'
                condition += (' AND n.state_code = s.report_state_code AND s.report_state_code <> \'0\''
                              if scope == 'state' else " AND s.report_state_code = '0'")
                targets.append((scope + '_admin_dept_units', 'administrative_unit_code',
                                'administrative_unit_name', condition, 'TRUE'))
            return tuple(targets)
        # Zero, -100 (international), unknown negative types and unrecognized
        # coverage labels have no verified target namespace in these datasets.
        return ()

    def required_entity_datasets(self, entity_type):
        """Inputs needed for this location type or covered-entity type label."""
        value = self._type(entity_type)
        return (self.dataset, *(target[0] for target in self._targets(value)))

    def entity_sources(self, release, entity_type, *, observed_on=None):
        """Resolve all inputs from one generation, checking each optional date guard."""
        return tuple(release.dataset(name, observed_on=observed_on)
                     for name in self.required_entity_datasets(entity_type))

    def entities(self, connection, **filters):
        """Return full register rows referenced by matching offices or claims.

        Require entity_type for directories/details, or covered_entity_type
        for coverage targets. Other filters select source report rows. Codes
        match exactly, never by name. Repeated source references do not multiply
        results; every matching register variant remains visible.

        reference_type_matches is false for a different local-body subtype,
        NULL when that subtype is unavailable, and true for a matching type.
        It compares the selected reports, not the legal validity of the link.
        """
        if self.entity_type_filter not in filters or filters[self.entity_type_filter] is None:
            raise ValueError(f'{self.entity_type_filter} is required')
        value = self._type(filters[self.entity_type_filter])
        filters = dict(filters, **{self.entity_type_filter: value})
        condition, params = self.queries._conditions(filters)
        code = 'covered_entity_code' if self.coverage else 'entity_code'
        scope = "'0'" if self.dataset == 'central_org_units' else 't.state_code'
        if self.coverage:
            condition += " AND t.coverage_details_reported = 'true'"
        selected = f'''WITH selected_entities AS (
            SELECT DISTINCT t.{self.entity_type_filter} AS entity_type,
                t.{code} AS entity_code, {scope} AS report_state_code
            FROM {self.dataset} t WHERE {condition}
              AND regexp_full_match(t.{code}, '[0-9]+')
              AND regexp_matches(t.{code}, '[1-9]')
        )'''
        branches = []
        for dataset, key, name, extra, type_matches in self._targets(value):
            branches.append(f'''SELECT '{dataset}' AS entity_dataset,
                ?::VARCHAR AS entity_type, n.{key} AS entity_code,
                n.{name} AS entity_name, {type_matches} AS reference_type_matches,
                n.* FROM {dataset} n
                WHERE EXISTS (SELECT 1 FROM selected_entities s
                    WHERE s.entity_code = n.{key} AND {extra})''')
            params.append(value)
        if not branches:
            # Keep a useful result schema and validate source filters even
            # when this type deliberately has no target register.
            branches.append('''SELECT NULL::VARCHAR AS entity_dataset,
                entity_type, entity_code, NULL::VARCHAR AS entity_name,
                NULL::BOOLEAN AS reference_type_matches
                FROM selected_entities WHERE FALSE''')
        return connection.sql(selected + ' SELECT * FROM (' +
                              ' UNION ALL BY NAME '.join(branches) +
                              ') resolved ORDER BY entity_type, entity_code, entity_dataset, entity_name',
                              params=params)
