"""Follow organization location/coverage references to typed LGD registers.

The numeric location types are administrative level codes, not constituency
coverage's textual entity types. Organization state is report scope, not a
restriction on the geographic location of its offices or coverage targets.
"""

import re

from ._common import code as validate_code


RESOLUTION_STATUSES = ('matched', 'ambiguous', 'missing_type', 'missing_code',
                       'invalid_code', 'unsupported_type', 'unmatched', 'not_reported')
TYPE_COLUMNS = ('reference_type', 'reported_type_name', 'known_type_name',
                'target_datasets', 'resolvable', 'source_rows', 'organization_units')


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

    def _scope(self, state_code):
        if state_code is not None:
            if 'state_code' not in self.queries.spec.columns:
                raise ValueError(f'{self.dataset} has no state_code filter')
            return validate_code(state_code)
        return None

    def _targets(self, value, state_code=None):
        """Return (dataset, code, name, condition, type_matches) SQL definitions.

        Only package-owned SQL appears here. Caller values are always bound.
        """
        if self.coverage:
            number = _COVERAGE_TYPES.get(value)
            body_type = _BODY_TYPES.get(value)
        else:
            number = int(value) if value and re.fullmatch(r'-?[0-9]+', value) else None
            body_type = -number if number is not None and -8 <= number <= -1 else None
        if body_type is not None:
            # Local bodies share a code namespace. Retain a changed body type
            # or register membership, explicitly exposing the disagreement.
            matches = f"try_cast(nullif(trim(n.local_body_type_code), '') AS INTEGER) = {body_type}"
            return tuple((name, 'local_body_code', 'local_body_name', 'TRUE', matches)
                         for name in _BODIES)
        if number in _GEOGRAPHY:
            return ((*_GEOGRAPHY[number], 'TRUE', 'TRUE'),)
        if not self.coverage and number is not None and number > 5:
            targets = []
            for scope in ('state', 'central'):
                if self.dataset == 'state_org_units' and scope == 'central':
                    continue
                if self.dataset == 'central_org_units' and scope == 'state':
                    continue
                if state_code is not None and (scope == 'central') != (state_code == '0'):
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

    def _entity_targets(self, value, state_code=None):
        targets = self._targets(value, state_code)
        if not targets:
            choices = ', '.join((*_COVERAGE_TYPES, *_BODY_TYPES)) if self.coverage else (
                '1–5 (geography), -1 through -8 (local bodies), or a custom level code >5')
            raise ValueError(f'Unsupported {self.entity_type_filter} for entities: {value!r}. '
                             f'Use {choices}. Use reference_types()/CLI types to inspect source types, '
                             'or references() to retain unresolved references.')
        return targets

    def required_entity_datasets(self, entity_type, *, state_code=None):
        """Inputs needed for this location type or covered-entity type label."""
        value = self._type(entity_type)
        return (self.dataset, *(target[0] for target in self._entity_targets(value, self._scope(state_code))))

    def entity_sources(self, release, entity_type, *, state_code=None, observed_on=None):
        """Resolve all inputs from one generation, checking each optional date guard."""
        return tuple(release.dataset(name, observed_on=observed_on)
                     for name in self.required_entity_datasets(entity_type, state_code=state_code))

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
        targets = self._entity_targets(value, self._scope(filters.get('state_code')))
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
        for dataset, key, name, extra, type_matches in targets:
            branches.append(f'''SELECT '{dataset}' AS entity_dataset,
                ?::VARCHAR AS entity_type, n.{key} AS entity_code,
                n.{name} AS entity_name, {type_matches} AS reference_type_matches,
                n.* FROM {dataset} n
                WHERE EXISTS (SELECT 1 FROM selected_entities s
                    WHERE s.entity_code = n.{key} AND {extra})''')
            params.append(value)
        return connection.sql(selected + ' SELECT * FROM (' +
                              ' UNION ALL BY NAME '.join(branches) +
                              ') resolved ORDER BY entity_type, entity_code, entity_dataset, entity_name',
                              params=params)

    def reference_type_map(self):
        """Known mappings without I/O; >5 denotes custom location levels.

        Labels for 0/-100 are deliberately absent: the source did not establish
        an official name. Numeric location codes and coverage labels differ.
        """
        values = (tuple((*_COVERAGE_TYPES, *_BODY_TYPES)) if self.coverage else
                  tuple(str(n) for n in (*_GEOGRAPHY, *range(-1, -9, -1), 0, -100)))
        result = []
        for value in values:
            result.append(dict(reference_type=value, known_type_name=self._label(value),
                               target_datasets=tuple(t[0] for t in self._targets(value)),
                               resolvable=bool(self._targets(value))))
        if not self.coverage:
            result.append(dict(reference_type='>5', known_type_name=None,
                               target_datasets=tuple(t[0] for t in self._targets('6')), resolvable=True))
        return tuple(result)

    def _label(self, value):
        if self.coverage:
            return value if value in (*_COVERAGE_TYPES, *_BODY_TYPES) else None
        names = {str(number): name for name, number in _COVERAGE_TYPES.items()}
        names.update({str(-number): name for name, number in _BODY_TYPES.items()})
        return names.get(value)

    def _reference_targets(self, value=None, state_code=None):
        """Group trusted type predicates by target register to scan each once."""
        state_code = self._scope(state_code)
        if value is not None:
            value = self._type(value)
        values = ((value,) if value is not None else
                  tuple((*_COVERAGE_TYPES, *_BODY_TYPES)) if self.coverage else
                  tuple(str(n) for n in (*_GEOGRAPHY, *range(-1, -9, -1), 6)))
        result = {}
        for kind in values:
            # Only supported package-owned kinds get SQL predicates. Unknown
            # caller values have no branches and are never interpolated.
            targets = self._targets(kind, state_code)
            if not targets:
                continue
            if not self.coverage and int(kind) > 5:
                type_condition = 'try_cast(s.entity_type AS BIGINT) > 5'
            elif self.coverage:
                type_condition = "s.entity_type = '" + kind + "'"
            else:
                type_condition = f'try_cast(s.entity_type AS BIGINT) = {int(kind)}'
            for dataset, key, name, extra, matches in targets:
                condition = f'({type_condition} AND {extra})'
                item = result.setdefault(dataset, dict(key=key, name=name, conditions=[], matches=[]))
                item['conditions'].append(condition)
                item['matches'].append(f'WHEN {type_condition} THEN {matches}')
        return result

    def required_reference_datasets(self, reference_type=None, *, state_code=None):
        """Inputs for references; omitted type includes all supported registers."""
        return (self.dataset, *self._reference_targets(reference_type, state_code))

    def reference_sources(self, release, reference_type=None, *, state_code=None, observed_on=None):
        return tuple(release.dataset(name, observed_on=observed_on)
                     for name in self.required_reference_datasets(reference_type, state_code=state_code))

    def _target_columns(self, targets):
        from ._catalog import get
        result = {}
        for dataset in targets:
            module = get(dataset)
            result[dataset] = module._queries.spec.columns if hasattr(module, '_queries') else module.columns
        return result

    def reference_columns(self, reference_type=None, *, state_code=None):
        targets = self._reference_targets(reference_type, state_code)
        return (*(f'source_{c}' for c in self.queries.spec.columns),
                'resolution_status', 'target_match_count', 'target_name_count',
                'target_dataset', 'target_code', 'target_name', 'reference_type_matches',
                *dict.fromkeys(f'target_{c}' for columns in self._target_columns(targets).values() for c in columns))

    def references(self, connection, *, resolution_status=None, **filters):
        """Keep source references, including unresolved and unreported claims.

        Each source row is retained once per distinct matching register variant,
        or once with NULL targets when unresolved. Exact target duplicates
        collapse; source duplicates remain. Status filters run after resolution.
        Missing required registers fail rather than appearing as unmatched data.
        """
        if resolution_status is not None and resolution_status not in RESOLUTION_STATUSES:
            raise ValueError('resolution_status must be one of: ' + ', '.join(RESOLUTION_STATUSES))
        condition, params = self.queries._conditions(filters)
        targets = self._reference_targets(filters.get(self.entity_type_filter), filters.get('state_code'))
        code = 'covered_entity_code' if self.coverage else 'entity_code'
        scope = "'0'" if self.dataset == 'central_org_units' else 't.state_code'
        reported = "t.coverage_details_reported = 'true'" if self.coverage else 'TRUE'
        source_columns = ', '.join(f't.{c} AS source_{c}' for c in self.queries.spec.columns)
        valid = (f"regexp_full_match(t.{code}, '[0-9]+') AND regexp_matches(t.{code}, '[1-9]')")
        # Reuse the same row ids across target branches, including identical
        # source rows; do not allow separate scans to assign different ids.
        sql = f'''WITH selected_references AS MATERIALIZED (
            SELECT row_number() OVER () AS _row_id, {source_columns},
                   t.{self.entity_type_filter} AS entity_type, t.{code} AS entity_code,
                   {scope} AS report_state_code, {reported} AS _reported,
                   {valid} AS _valid_code
            FROM {self.dataset} t WHERE {condition}
        )'''
        target_columns = self._target_columns(targets)
        union_columns = tuple(dict.fromkeys(c for columns in target_columns.values() for c in columns))
        branches = []
        for dataset, target in targets.items():
            selections = ', '.join(f'n.{c} AS target_{c}' for c in target_columns[dataset])
            branches.append(f'''SELECT DISTINCT s._row_id, '{dataset}' AS target_dataset,
                n.{target['key']} AS target_code, n.{target['name']} AS target_name,
                CASE {' '.join(target['matches'])} END AS reference_type_matches,
                {selections}
                FROM selected_references s JOIN {dataset} n
                ON s.entity_code = n.{target['key']} AND s._reported AND s._valid_code
                   AND ({' OR '.join(target['conditions'])})''')
        if not branches:
            branches.append('''SELECT _row_id, NULL::VARCHAR AS target_dataset,
                NULL::VARCHAR AS target_code, NULL::VARCHAR AS target_name,
                NULL::BOOLEAN AS reference_type_matches FROM selected_references WHERE FALSE''')
        # Custom-level conditions mention n: support depends on a known type,
        # not the existence/state of a particular target record.
        if self.coverage:
            supported_type = "s.entity_type IN (" + ', '.join("'"+v+"'" for v in (*_COVERAGE_TYPES, *_BODY_TYPES)) + ')'
        else:
            supported_type = '(try_cast(s.entity_type AS BIGINT) BETWEEN -8 AND -1 OR try_cast(s.entity_type AS BIGINT) > 0)'
        source_output = ', '.join(f's.source_{c}' for c in self.queries.spec.columns)
        extra_output = ''.join(f', m.target_{c}' for c in union_columns)
        sql += f''', matches AS ({' UNION ALL BY NAME '.join(branches)}),
        counts AS (SELECT _row_id, count(*) AS match_count,
            count(DISTINCT CASE WHEN nullif(trim(target_name), '') IS NOT NULL THEN target_name END) AS name_count
            FROM matches GROUP BY _row_id),
        resolved AS (
            SELECT {source_output},
                CASE WHEN NOT s._reported THEN 'not_reported'
                     WHEN nullif(trim(s.entity_type), '') IS NULL THEN 'missing_type'
                     WHEN nullif(trim(s.entity_code), '') IS NULL THEN 'missing_code'
                     WHEN NOT s._valid_code THEN 'invalid_code'
                     WHEN NOT coalesce({supported_type}, FALSE) THEN 'unsupported_type'
                     WHEN coalesce(c.match_count, 0) = 0 THEN 'unmatched'
                     WHEN c.match_count > 1 THEN 'ambiguous' ELSE 'matched' END AS resolution_status,
                coalesce(c.match_count, 0) AS target_match_count,
                coalesce(c.name_count, 0) AS target_name_count,
                m.target_dataset, m.target_code, m.target_name, m.reference_type_matches{extra_output}
            FROM selected_references s LEFT JOIN matches m USING (_row_id)
            LEFT JOIN counts c USING (_row_id)
        ) SELECT * FROM resolved'''
        if resolution_status is not None:
            sql += ' WHERE resolution_status = ?'
            params.append(resolution_status)
        sql += ' ORDER BY source_organization_unit_code, target_dataset, target_code, target_name'
        return connection.sql(sql, params=params)

    def reference_types(self, connection, **filters):
        """Summarize observed source types and labels without loading registers."""
        condition, params = self.queries._conditions(filters)
        value = f't.{self.entity_type_filter}'
        label = ('t.covered_entity_type' if self.coverage else
                 't.entity_type_name' if 'entity_type_name' in self.queries.spec.columns else 'NULL::VARCHAR')
        labels, targets = [], []
        for item in self.reference_type_map():
            kind = item['reference_type']
            predicate = (f'try_cast({value} AS BIGINT) > 5' if kind == '>5' else
                         f"{value} = '{kind}'" if self.coverage else f'try_cast({value} AS BIGINT) = {int(kind)}')
            if item['known_type_name'] is not None:
                labels.append(f"WHEN {predicate} THEN '{item['known_type_name']}'")
            names = self._targets('6' if kind == '>5' else kind, self._scope(filters.get('state_code')))
            array = '[' + ', '.join("'"+target[0]+"'" for target in names) + ']::VARCHAR[]'
            targets.append(f'WHEN {predicate} THEN {array}')
        sql = f'''SELECT {value} AS reference_type, {label} AS reported_type_name,
            CASE {' '.join(labels)} END AS known_type_name,
            CASE {' '.join(targets)} ELSE []::VARCHAR[] END AS target_datasets,
            len(target_datasets) > 0 AS resolvable, count(*) AS source_rows,
            count(DISTINCT t.organization_unit_code) AS organization_units
            FROM {self.dataset} t WHERE {condition}
            GROUP BY ALL ORDER BY reference_type, reported_type_name'''
        return connection.sql(sql, params=params)
