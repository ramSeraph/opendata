"""Optional location-name output for state and central organization units."""

from ._dataset import DatasetQueries


def include_entity_name_option(value):
    if type(value) is not bool:
        raise ValueError('include_entity_name must be a boolean')
    return value


class OrganizationUnitQueries(DatasetQueries):
    def required_datasets(self, *, field=None, include_entity_name=False):
        names = super().required_datasets(field=field)
        if include_entity_name_option(include_entity_name):
            names = (*names, 'org_unit_details')
        return tuple(dict.fromkeys(names))

    def _with_entity_name(self, relation):
        names = self._lookup_names('entity_name', alias='t')
        order = ('t.distance, ' if 'distance' in relation.columns else '') + self._order
        # The correlated array preserves unmatched rows and original duplicates.
        # A scalar label is supplied only when the reference is unambiguous.
        return relation.query('_org_unit_rows', f'''SELECT t.*,
            CASE WHEN len(entity_names)=1 THEN entity_names[1] END AS entity_name
            FROM (SELECT t.*, {names} AS entity_names FROM _org_unit_rows t) t
            ORDER BY {order}''')

    def list(self, connection, *, include_entity_name=False, **filters):
        """List units, optionally adding entity_name and all entity_names labels.

        Missing/ambiguous matches have a NULL entity_name. entity_names holds
        distinct alternatives, or [] for an unmatched reference. Load
        org_unit_details only when opting into this lookup.
        """
        include_entity_name_option(include_entity_name)
        result = super().list(connection, **filters)
        return self._with_entity_name(result) if include_entity_name else result

    def by_code(self, connection, value, *, include_entity_name=False, **filters):
        """Look up a unit code, optionally resolving its location name."""
        return super().by_code(connection, value,
                               include_entity_name=include_entity_name, **filters)

    def search(self, connection, name, *, include_entity_name=False, **options):
        """Search units with optional location-name output; preserve ranking."""
        include_entity_name_option(include_entity_name)
        result = super().search(connection, name, **options)
        return self._with_entity_name(result) if include_entity_name else result
