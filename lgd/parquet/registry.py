"""Schemas available to the standalone converter."""

from .administrative import SCHEMAS as ADMINISTRATIVE_SCHEMAS
from .events import SCHEMAS as EVENT_SCHEMAS
from .villages import FIELDS as VILLAGE_FIELDS
from .org_coverage import FIELDS as ORGANIZATION_COVERAGE_FIELDS


SCHEMAS = {'villages': VILLAGE_FIELDS, **ADMINISTRATIVE_SCHEMAS, **EVENT_SCHEMAS,
           'org_unit_coverage': ORGANIZATION_COVERAGE_FIELDS}
