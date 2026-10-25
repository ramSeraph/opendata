"""Optional location-name output for state and central organization units."""

from dataclasses import replace

from ._dataset import DatasetQueries
from ._missing import column_names


NAME_STATUSES = ('matched', 'missing', 'ambiguous')
NAME_COLUMNS = ('entity_name', 'entity_name_status')


def include_entity_name_option(value):
    if type(value) is not bool:
        raise ValueError('include_entity_name must be a boolean')
    return value


def wants_entity_name(*, include_entity_name=False, entity_name=None,
                      entity_name_status=None, is_null=None, is_blank=None):
    include_entity_name_option(include_entity_name)
    if entity_name_status is not None and entity_name_status not in NAME_STATUSES:
        raise ValueError('entity_name_status must be matched, missing or ambiguous')
    if entity_name is not None and not isinstance(entity_name, str):
        raise ValueError('entity_name must be a string')
    missing = (*column_names(is_null, 'is_null'), *column_names(is_blank, 'is_blank'))
    return (include_entity_name or entity_name is not None or entity_name_status is not None
            or bool(set(missing) & set(NAME_COLUMNS)))


class OrganizationUnitQueries(DatasetQueries):
    def required_datasets(self, *, field=None, include_entity_name=False, entity_name=None,
                          entity_name_status=None, is_null=None, is_blank=None):
        names = super().required_datasets(field=field)
        if wants_entity_name(include_entity_name=include_entity_name, entity_name=entity_name,
                             entity_name_status=entity_name_status, is_null=is_null, is_blank=is_blank):
            names = (*names, 'org_unit_details')
        return tuple(dict.fromkeys(names))

    def _enriched(self):
        names = self._lookup_names('entity_name', alias='s')
        table = f'''(SELECT t.*,
            CASE WHEN len(entity_names)=1 THEN entity_names[1] END AS entity_name,
            CASE WHEN len(entity_names)=0 THEN 'missing'
                 WHEN len(entity_names)=1 THEN 'matched' ELSE 'ambiguous' END AS entity_name_status
            FROM (SELECT s.*, {names} AS entity_names FROM {self.spec.dataset} s) t)'''
        # Reuse all normal filter/search validation. The extra columns are
        # available before WHERE/ranking/LIMIT, rather than enriched afterwards.
        return DatasetQueries(replace(self.spec, columns=(*self.spec.columns, *NAME_COLUMNS)), table=table)

    def list(self, connection, *, include_entity_name=False, entity_name=None,
             entity_name_status=None, **filters):
        """Optionally return reported location labels and their resolution status.

        Name filters imply enrichment. Missing labels have []/NULL; ambiguous
        labels retain every alternative with a NULL scalar. Labels are reported
        by org_unit_details, not verified names from geographic registers.
        """
        enriched = wants_entity_name(include_entity_name=include_entity_name, entity_name=entity_name,
            entity_name_status=entity_name_status, is_null=filters.get('is_null'), is_blank=filters.get('is_blank'))
        if enriched:
            return self._enriched().list(connection, entity_name=entity_name,
                                        entity_name_status=entity_name_status, **filters)
        return super().list(connection, **filters)

    def by_code(self, connection, code, *, include_entity_name=False, entity_name=None,
                entity_name_status=None, **filters):
        """Look up a unit code, optionally resolving/filtering its location label."""
        return super().by_code(connection, code, include_entity_name=include_entity_name,
                               entity_name=entity_name, entity_name_status=entity_name_status, **filters)

    def search(self, connection, name, *, include_entity_name=False, entity_name=None,
               entity_name_status=None, **options):
        """Search units; derived name filters apply before ranking and limits."""
        enriched = wants_entity_name(include_entity_name=include_entity_name, entity_name=entity_name,
            entity_name_status=entity_name_status, is_null=options.get('is_null'), is_blank=options.get('is_blank'))
        if enriched:
            return self._enriched().search(connection, name, entity_name=entity_name,
                                          entity_name_status=entity_name_status, **options)
        return super().search(connection, name, **options)
