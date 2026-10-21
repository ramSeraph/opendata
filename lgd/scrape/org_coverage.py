"""Organization-unit coverage, including the links omitted by LGD's Excel view.

This is a coverage report, not a complete census of organization units. Missing
units and blank coverage must not be interpreted as deleted units/relationships.
"""

from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .base import (BaseDownloader, DownloaderItem, MultiDownloader,
                   INCORRECT_CAPTCHA_MESSAGE)
from .dwr import DwrCaller


HEADERS = ['S.No.', 'Organization Unit Code', 'Organization Unit Name',
           'Entity Code', 'Entity Name', 'Org Specific Code', 'Coverage']
UNIT_FIELDS = ['Org Unit Code', 'Org Unit Name (In English)', 'Entity Code',
               'Entity Name', 'Org Specific Code']
LINK_FIELDS = ['Covered Entity Code', 'Covered Entity Name',
               'Covered Entity Type', 'Coverage Type']


def parse_coverage_report(content):
    soup = BeautifulSoup(content, 'html.parser')
    table = soup.find('table', id='tableRecords')
    if table is None:
        raise ValueError('Organization coverage report has no result table')
    rows = table.find_all('tr')
    if not rows or [c.get_text(' ', strip=True) for c in rows[0].find_all('th')] != HEADERS:
        raise ValueError('Unexpected organization coverage header')

    # LGD places hidden inputs between <tr>s, including outside the table.
    inputs = {}
    for item in soup.find_all('input', id=True):
        code = item['id']
        if code.isdigit():
            if code in inputs:
                raise ValueError(f'Duplicate coverage input for unit {code}')
            inputs[code] = item.get('value', '')

    records, seen = [], set()
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
        if serial != str(len(seen) + 1) or not code.isdigit() or code in seen:
            raise ValueError(f'Invalid organization coverage serial/unit: {values[:2]}')
        seen.add(code)
        if code not in inputs:
            raise ValueError(f'Missing coverage input for unit {code}')
        unit = dict(zip(UNIT_FIELDS, values[1:6]))
        # LGD represents an unmapped unit as ",%%%" (four empty fields).
        claims = [part for part in inputs[code].split(',') if part not in ('', '%%%')]
        if bool(claims) != bool(cells[-1].find('a')):
            raise ValueError(f'Coverage link/input mismatch for unit {code}')
        if not claims:
            records.append({**unit, **dict.fromkeys(LINK_FIELDS, ''),
                            'Coverage Details Reported': 'false'})
        for claim in claims:
            parts = claim.split('%')
            if (len(parts) != 4 or not parts[0].isdigit()
                    or not parts[2] or parts[3] not in ('F', 'P')):
                raise ValueError(f'Malformed coverage claim for unit {code}: {claim!r}')
            # Keep source multiplicity; no event/relationship IDs justify deduplication.
            # Some supplied codes have no name (e.g. Rubber Board subdistrict 2873).
            records.append({**unit, **dict(zip(LINK_FIELDS, parts)),
                            'Coverage Details Reported': 'true'})
    if not seen or set(inputs) != seen:
        raise ValueError('Empty or unmatched organization coverage result')
    return records


def root_levels(levels):
    """Select each outermost dropdown level; its report includes descendants."""
    by_code = {}
    for level in levels:
        code = str(level['orgLocatedLevelCode'])
        parent = str(level['parentOrgLocatedLevelCode'])
        if not code.isdigit() or not parent.isdigit() or code in by_code:
            raise ValueError('Invalid or repeated organization coverage level')
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
