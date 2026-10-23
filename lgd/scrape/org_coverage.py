"""Organization-unit coverage, including the links omitted by LGD's Excel view.

This is a coverage report, not a complete census of organization units. Missing
units and blank coverage must not be interpreted as deleted units/relationships.
"""

import logging
import re

from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from bs4 import BeautifulSoup

from .base import (BaseDownloader, DownloaderItem, MultiDownloader,
                   INCORRECT_CAPTCHA_MESSAGE)
from .dwr import DwrCaller


logger = logging.getLogger(__name__)

HEADERS = ['S.No.', 'Organization Unit Code', 'Organization Unit Name',
           'Entity Code', 'Entity Name', 'Org Specific Code', 'Coverage']
UNIT_FIELDS = ['Org Unit Code', 'Org Unit Name (In English)', 'Entity Code',
               'Entity Name', 'Org Specific Code']
LINK_FIELDS = ['Covered Entity Code', 'Covered Entity Name',
               'Covered Entity Type', 'Coverage Type']
CLAIM = re.compile(r'([0-9]+)%([^%]*)%([^%]*)%([FP])(?=,|$)')


def parse_coverage_claims(value, unit_code):
    """Read complete claims; commas inside entity names are ordinary text."""
    claims, offset = [], 0
    while offset < len(value):
        if value[offset] == ',':
            offset += 1
            continue
        # LGD uses four empty fields for an unmapped unit.
        if value.startswith('%%%', offset) and (
                offset + 3 == len(value) or value[offset + 3] == ','):
            offset += 3
            continue
        match = CLAIM.match(value, offset)
        if match is None:
            raise ValueError(f'Malformed coverage claim for unit {unit_code}: {value[offset:offset + 200]!r}')
        claims.append(match.groups())
        offset = match.end()
    return claims


def parse_coverage_report(content):
    soup = BeautifulSoup(content, 'html.parser')
    table = soup.find('table', id='tableRecords')
    if table is None:
        form = soup.find('form', id='capchForm')
        if form is not None and urlsplit(form.get('action', '')).path.rsplit('/', 1)[-1] == 'adminEntityCoverageDetails.do':
            title = form.select_one('h3.card-title')
            empty = any(node.get_text(' ', strip=True) == 'Data Not Found'
                        for node in form.select('div.control-label'))
            if (title is not None
                    and title.get_text(' ', strip=True) == 'Organization Unit Coverage Details'
                    and empty
                    and not any(node['id'].isdigit() for node in soup.find_all('input', id=True))):
                return []
        raise ValueError('Organization coverage report has no result table')
    rows = table.find_all('tr')
    if not rows or [c.get_text(' ', strip=True) for c in rows[0].find_all('th')] != HEADERS:
        raise ValueError('Unexpected organization coverage header')

    # LGD places hidden inputs between <tr>s, including outside the table.
    # A unit may appear in several rows, each with its own coverage input.
    # Pair occurrences in report order instead of overwriting or combining
    # all of a unit's claims into every occurrence of its row.
    inputs = defaultdict(deque)
    for item in soup.find_all('input', id=True):
        code = item['id']
        if code.isdigit():
            inputs[code].append(item.get('value', ''))

    records, row_count = [], 0
    for row in rows[1:]:
        cells = row.find_all('td', recursive=False)
        # The only non-data row is the generated-on/URL footer.
        if (len(cells) == 1 and cells[0].get('colspan') == '10'
                and 'Report Generated on' in cells[0].get_text()):
            continue
        if len(cells) != len(HEADERS):
            raise ValueError('Unexpected organization coverage row layout')
        values = [c.get_text(' ', strip=True) for c in cells]
        serial, code = values[:2]
        if serial != str(row_count + 1) or not code.isdigit():
            raise ValueError(f'Invalid organization coverage serial/unit: {values[:2]}')
        row_count += 1
        if not inputs.get(code):
            raise ValueError(f'Missing coverage input for unit {code}')
        unit = dict(zip(UNIT_FIELDS, values[1:6]))
        claims = parse_coverage_claims(inputs[code].popleft(), code)
        if bool(claims) != bool(cells[-1].find('a')):
            raise ValueError(f'Coverage link/input mismatch for unit {code}')
        if not claims:
            records.append({**unit, **dict.fromkeys(LINK_FIELDS, ''),
                            'Coverage Details Reported': 'false'})
        for parts in claims:
            # Keep source multiplicity; no event/relationship IDs justify deduplication.
            # LGD can omit the name and even the entity type (e.g. org 835,
            # unit 1346744: 277142%%%F). Preserve blanks, never infer a type
            # from the numeric code or treat an incomplete link as absent.
            records.append({**unit, **dict(zip(LINK_FIELDS, parts)),
                            'Coverage Details Reported': 'true'})
    if not row_count or any(inputs.values()):
        raise ValueError('Empty or unmatched organization coverage result')
    return records


def root_levels(levels):
    """Select each outermost dropdown level; its report includes descendants."""
    by_code = {}
    for level in levels:
        code = str(level['orgLocatedLevelCode'])
        parent = level['parentOrgLocatedLevelCode']
        if not code.isdigit():
            raise ValueError(f'Invalid organization coverage level code: {code!r}')
        # Some organizations include their top level even in ExceptTop. LGD
        # represents that level's absent parent as null (e.g. NCST, code 717).
        if parent is not None and not str(parent).isdigit():
            raise ValueError(f'Invalid parent {parent!r} for organization coverage level {code}')
        if code in by_code:
            raise ValueError(f'Repeated organization coverage level: {code}')
        by_code[code] = level
    for code in by_code:
        seen = set()
        while code in by_code:
            if code in seen:
                raise ValueError('Cycle in organization coverage levels')
            seen.add(code)
            code = str(by_code[code]['parentOrgLocatedLevelCode'])
    return [level for level in levels
            if str(level['parentOrgLocatedLevelCode']) not in by_code]


class OrganizationCoverageDownloader(BaseDownloader):
    def __init__(self, *, organization, **kwargs):
        super().__init__(organization=organization, **kwargs)
        self.organization = organization

    def get_records(self):
        org = self.organization
        levels = DwrCaller(ctx=self.ctx, base_url=self.base_url,
                           script_name='lgdAdminDepatmentDwr',
                           method_name='getOrgLocatedLevelListExceptTop',
                           call_args={'c0-param0': 'number:' + org['Organization Code']}).call()
        selected = root_levels(levels)
        records = []
        for level in selected:
            for row in self.get_level_records(level):
                row.update({'Report Org Located Level Code': str(level['orgLocatedLevelCode']),
                            'Report Org Level Specific Name': level['orgLevelSpecificName'],
                            'Base Organization Code': org['Organization Code'],
                            'Base Organization Name': org['Organization Name'],
                            'State Code': org.get('State Code', '0'),
                            'State Name': org.get('State Name', 'India')})
                records.append(row)
        return records

    def get_level_records(self, level):
        org = self.organization
        token = self.ctx.csrf_token_reports
        url = self.base_url + '/adminEntityCoverageDetails.do'
        referer = url + '?' + urlencode({'OWASP_CSRFTOKEN': token})
        response = self.ctx.session.get(referer, **self.ctx.params.request_args())
        response.raise_for_status()
        fields = {
            'OWASP_CSRFTOKEN': token,
            'state': '1' if 'State Code' in org else '0',
            'stateCode': org.get('State Code', ''),
            'depatmentCode': org['Organization Code'], 'orgName': org['Organization Name'],
            'orgLocatedLevelCode': str(level['orgLocatedLevelCode']),
            'orgUnitCode': str(level['orgLocatedLevelCode']), 'level': '0',
            'hierarchyList': '', 'hierarchyIdList': level['orgLevelSpecificName'],
        }
        for _ in range(self.ctx.params.captcha_retries + 1):
            fields['captchaAnswer'] = self.captcha_helper.get_code(referer)
            response = self.ctx.session.post(referer, data=fields,
                                             headers={'Referer': referer},
                                             **self.ctx.params.request_args())
            response.raise_for_status()
            if INCORRECT_CAPTCHA_MESSAGE in response.text:
                self.captcha_helper.mark_failure()
                continue
            result = parse_coverage_report(response.content)
            self.captcha_helper.mark_success()
            if not result:
                logger.info('No coverage data reported for organization %s, state %s, level %s',
                            org['Organization Code'], org.get('State Code', '0'),
                            level['orgLocatedLevelCode'])
            return result
        raise ValueError('Organization coverage captcha retries exhausted')


class OrganizationReportDownloader(MultiDownloader):
    """Partition an organization report using the existing organization lists."""
    child_class = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_dep('CENTRAL_ORG_DETAILS')
        self.add_dep('STATE_ORG_DETAILS')

    def populate_downloaders(self):
        if self.downloader_items is not None:
            return
        items, seen = [], {}
        for dependency in self.deps:
            for org in BaseDownloader.records_from_downloader(dependency):
                # Organization listings can repeat an organization under parents.
                org = {k: org[k] for k in ('Organization Code', 'Organization Name',
                                          'State Code', 'State Name') if k in org}
                key = (org.get('State Code', '0'), org['Organization Code'])
                if key in seen:
                    if seen[key] != org:
                        raise ValueError(f'Conflicting organization identity: {key}')
                    continue
                seen[key] = org
                suffix = '_'.join(key)
                path = Path(self.csv_filename)
                child = self.child_class(
                    name=f'{self.name}_{suffix}', base_name=self.name, ctx=self.ctx,
                    csv_filename=f'{path.stem}_{suffix}{path.suffix}', organization=org)
                items.append(DownloaderItem(downloader=child, record=org))
        self.downloader_items = items

    def combine_records(self):
        records = super().combine_records()
        if not records:
            raise ValueError(f'Entire {self.name} export is empty')
        return records


class AllOrganizationCoverageDownloader(OrganizationReportDownloader):
    child_class = OrganizationCoverageDownloader
