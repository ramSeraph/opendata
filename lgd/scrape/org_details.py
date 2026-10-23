"""Reported organization-unit details, including office contacts and addresses.

This report can omit units present in the directory. Keep it as a separate
observation rather than replacing the more complete organization-unit census.
"""

import re
from urllib.parse import urlencode

from lxml import etree

from .base import BaseDownloader, INCORRECT_CAPTCHA_MESSAGE
from .org_coverage import OrganizationReportDownloader


# Normalize field names shared with the existing organization/coverage exports.
FIELDS = {
    'S.No': 'S.No.',
    'Parent Org Unit Code': 'Parent Org Unit Code',
    'Parent Org Unit Name': 'Parent Org Unit Name',
    'Organization Unit Code': 'Org Unit Code',
    'Organization Unit Name': 'Org Unit Name (In English)',
    'Organization Specific Code': 'Org Specific Code',
    'Organization Email ID': 'Organization Email ID',
    'Organization Contact Number': 'Organization Contact Number',
    'Organization Address': 'Organization Address',
    'Administrative Unit Level Code': 'Entity Type',
    'Administrative Unit Level (In English)': 'Entity Type Name',
    'Administrative Entity Code': 'Entity Code',
    'Administrative Unit Entity Name (In English)': 'Entity Name',
}


def parse_organization_details(content):
    document = etree.HTML(content)
    tables = [] if document is None else document.xpath('//table[@id="table"]')
    if len(tables) != 1:
        raise ValueError('Organization details report has no unique result table')
    rows = tables[0].xpath('.//tr')
    if not rows:
        raise ValueError('Organization details report has no header')
    header = [' '.join(''.join(c.itertext()).split()) for c in rows[0].xpath('./th|./td')]
    if header != list(FIELDS):
        raise ValueError(f'Unexpected organization details header: {header}')
    records = []
    for serial, row in enumerate(rows[1:], 1):
        # Preserve meaningful inner spacing and text codes (including "0").
        values = [' '.join(t.strip() for t in c.itertext() if t.strip())
                  for c in row.xpath('./td')]
        if len(values) != len(FIELDS):
            raise ValueError(f'Unexpected organization details row layout at {serial}')
        record = dict(zip(FIELDS.values(), values))
        if (record['S.No.'] != str(serial)
                or not record['Org Unit Code'].isdigit()
                or not record['Parent Org Unit Code'].isdigit()
                # LGD uses negative level codes for local bodies and overseas units.
                or not re.fullmatch(r'-?\d+', record['Entity Type'])
                or not record['Entity Code'].isdigit()):
            raise ValueError(f'Invalid organization details serial/codes at {serial}')
        records.append(record)
    return records


class OrganizationDetailsDownloader(BaseDownloader):
    def __init__(self, *, organization, **kwargs):
        super().__init__(organization=organization, **kwargs)
        self.organization = organization

    def get_records(self):
        org = self.organization
        token = self.ctx.csrf_token_reports
        query = '?' + urlencode({'OWASP_CSRFTOKEN': token})
        referer = self.base_url + '/departOrganizationUnit.do' + query
        response = self.ctx.session.get(referer, **self.ctx.params.request_args())
        response.raise_for_status()
        is_state = 'State Code' in org
        fields = {
            'OWASP_CSRFTOKEN': token, 'radioUser': '1' if is_state else '0',
            # LGD repeats the state selector's name attribute. Browsers use
            # the first ("code"); html.parser misleadingly returns "statelabel".
            'code': org.get('State Code', '0'),
            'orgCode': org['Organization Code'] if is_state else '',
            'orgUnitCode': '0' if is_state else org['Organization Code'],
            # orgztn is an optional report-heading label, not a selector. Some
            # real names cause LGD to return 404, including through its own UI
            # (state/org 32/1533 and 4/849). Codes select the same report without
            # that label; preserve the original organization name in rows below.
            'unitLvlDept': 'All', 'orgLevel': 'All',
        }
        for _ in range(self.ctx.params.captcha_retries + 1):
            fields['captchaAnswer'] = self.captcha_helper.get_code(referer)
            response = self.ctx.session.post(
                self.base_url + '/viewOrganizationUnitReport.do' + query,
                data=fields, headers={'Referer': referer}, **self.ctx.params.request_args())
            response.raise_for_status()
            if INCORRECT_CAPTCHA_MESSAGE in response.text:
                self.captcha_helper.mark_failure()
                continue
            records = parse_organization_details(response.content)
            self.captcha_helper.mark_success()
            for row in records:
                row.update({'Base Organization Code': org['Organization Code'],
                            'Base Organization Name': org['Organization Name'],
                            'State Code': org.get('State Code', '0'),
                            'State Name': org.get('State Name', 'India')})
            return records
        raise ValueError('Organization details captcha retries exhausted')


class AllOrganizationDetailsDownloader(OrganizationReportDownloader):
    child_class = OrganizationDetailsDownloader
