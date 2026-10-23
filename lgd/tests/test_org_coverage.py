import unittest
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import requests

from scrape import get_all_downloaders
from scrape.base import BaseDownloader, Context, Params
from scrape.org_coverage import (HEADERS, OrganizationCoverageDownloader,
                                 parse_coverage_report, root_levels)
from scrape.site_map import get_known_site_map


def report(claims=',18%Assam%State%P,287%Goalpara%District%F', *, link=True):
    # Match LGD's invalid table nesting: the input is outside the <tr>.
    return ('<input id="1432644" type="hidden" value="' + claims + '">'
            '<table id="tableRecords"><tr>' + ''.join(f'<th>{h}</th>' for h in HEADERS)
            + '</tr><tr><td>1</td><td>1432644</td><td>Field Office</td>'
            '<td>48041</td><td>AGIA II</td><td>001</td><td>'
            + ('<a>View Coverage Details</a>' if link else '')
            + '</td></tr><tr><td colspan="10">Report Generated on today</td></tr></table>')


def repeated_unit_report():
    # The live Jharkhand Revenue report repeats units across rows, with a
    # separate hidden input after each row, including interleaved unit IDs.
    fragments = []
    for serial, code, claims in [(1, '11459', ',331%Gumla%District%P'),
                                 (2, '11677', ',338%Palamu%District%P'),
                                 (3, '11459', ',2713%Chainpur%Subdistrict%P'),
                                 (4, '11459', ',376062%Katabil%Village%F,376063%Rajadera%Village%F')]:
        fragments.append(f'<tr><td>{serial}</td><td>{code}</td><td>Revenue Office</td>'
                         '<td>2029</td><td>HALKA I</td><td></td>'
                         '<td><a>View Coverage Details</a></td></tr>'
                         f'<input id="{code}" type="hidden" value="{claims}">')
    return ('<table id="tableRecords"><tr>' + ''.join(f'<th>{h}</th>' for h in HEADERS)
            + '</tr>' + ''.join(fragments) + '</table>')


def empty_report():
    # Live DIT/Andaman Finance empty-result layout, distinct from the form
    # initially shown before submitting a report and from generic error pages.
    return ('<form id="capchForm" action="adminEntityCoverageDetails.do" method="POST">'
            '<h3 class="card-title">Organization Unit Coverage Details <label id="ssLabel"></label></h3>'
            '<div class="card-body"><div class="form-group row">'
            '<div class="col-sm-12 control-label">\n Data Not Found\n </div>'
            '</div></div></form>')


class CoverageParsingTests(unittest.TestCase):
    def test_all_links_and_location_are_distinct(self):
        rows = parse_coverage_report(report())
        self.assertEqual([r['Covered Entity Code'] for r in rows], ['18', '287'])
        self.assertEqual([r['Coverage Type'] for r in rows], ['P', 'F'])
        self.assertTrue(all(r['Entity Code'] == '48041' for r in rows))
        self.assertTrue(all(r['Org Specific Code'] == '001' for r in rows))

    def test_no_details_preserved_explicitly_and_claim_multiplicity_retained(self):
        row, = parse_coverage_report(report(',%%%', link=False))
        self.assertEqual(row['Coverage Details Reported'], 'false')
        self.assertEqual(row['Coverage Type'], '')
        claims = ',18%Assam%State%P,18%Assam%State%P'
        self.assertEqual(len(parse_coverage_report(report(claims))), 2)

    def test_missing_entity_name_does_not_drop_a_reported_link(self):
        row, = parse_coverage_report(report(',2873%%Subdistrict%P'))
        self.assertEqual(row['Covered Entity Code'], '2873')
        self.assertEqual(row['Covered Entity Name'], '')
        self.assertEqual(row['Coverage Details Reported'], 'true')

    def test_comma_names_do_not_split_coverage_claims(self):
        claims = (',37688%Joshi Colony, Ram Tirath Road (Og)%Village%F'
                  ',37690%Raggar Colony, Gali No. 1,2 & 3, Ram Tirath Road.(Og)%Village%F'
                  ',277142%%%F,287%Goalpara%District%P')
        rows = parse_coverage_report(report(claims))
        self.assertEqual([r['Covered Entity Code'] for r in rows],
                         ['37688', '37690', '277142', '287'])
        self.assertEqual(rows[0]['Covered Entity Name'], 'Joshi Colony, Ram Tirath Road (Og)')
        self.assertEqual(rows[1]['Covered Entity Name'],
                         'Raggar Colony, Gali No. 1,2 & 3, Ram Tirath Road.(Og)')
        self.assertEqual(rows[2]['Covered Entity Type'], '')
        self.assertEqual(rows[3]['Coverage Type'], 'P')

    def test_comma_names_do_not_hide_truncated_or_invalid_claims(self):
        good = '37688%Joshi Colony, Ram Tirath Road (Og)%Village%F'
        for claims in [good + ',broken', 'broken,' + good,
                       good + ',277142%%%invalid', '37688%Joshi Colony, Ram Tirath Road (Og)',
                       good + 'unexpected']:
            with self.subTest(claims=claims), self.assertRaisesRegex(ValueError, 'Malformed coverage claim'):
                parse_coverage_report(report(',' + claims))

    def test_explicit_empty_report_is_successful(self):
        self.assertEqual(parse_coverage_report(empty_report()), [])

    def test_missing_table_is_not_automatically_an_empty_report(self):
        empty = empty_report()
        for html in ['<html>Data Not Found</html>',
                     empty.replace('Data Not Found', ''),
                     empty.replace('Organization Unit Coverage Details', 'Other Report'),
                     empty.replace('adminEntityCoverageDetails.do', 'login.do'),
                     empty.replace('Data Not Found', 'Session expired'),
                     empty + '<input id="123" value=",18%Assam%State%P">',
                     empty + report().replace('S.No.', 'Unexpected Header')]:
            with self.subTest(html=html), self.assertRaises(ValueError):
                parse_coverage_report(html)

    def test_missing_entity_type_preserves_incomplete_claim(self):
        # ORG_UNIT_COVERAGE_20_835 reported this claim for unit 1346744.
        for claim, name in [('277142%%%F', ''), ('277142%Reported name%%P', 'Reported name')]:
            with self.subTest(claim=claim):
                html = report(',' + claim).replace('1432644', '1346744')
                row, = parse_coverage_report(html)
                self.assertEqual(row['Org Unit Code'], '1346744')
                self.assertEqual(row['Covered Entity Code'], '277142')
                self.assertEqual(row['Covered Entity Name'], name)
                self.assertEqual(row['Covered Entity Type'], '')
                self.assertEqual(row['Coverage Type'], claim[-1])
                self.assertEqual(row['Coverage Details Reported'], 'true')

    def test_missing_type_does_not_allow_invalid_codes_flags_or_layouts(self):
        for claim in ['%%%F', 'unknown%%%F', '277142%%%', '277142%%%unknown',
                      '277142%%F', '277142%%%%F']:
            with self.subTest(claim=claim), self.assertRaisesRegex(ValueError, 'Malformed coverage claim'):
                parse_coverage_report(report(',' + claim))

    def test_repeated_units_keep_each_rows_own_coverage(self):
        rows = parse_coverage_report(repeated_unit_report())
        self.assertEqual([(r['Org Unit Code'], r['Covered Entity Code']) for r in rows],
                         [('11459', '331'), ('11677', '338'), ('11459', '2713'),
                          ('11459', '376062'), ('11459', '376063')])
        self.assertEqual([r['Covered Entity Type'] for r in rows],
                         ['District', 'District', 'Subdistrict', 'Village', 'Village'])

    def test_repeated_units_still_require_one_input_per_row_and_serial_sequence(self):
        html = repeated_unit_report()
        first_input = '<input id="11459" type="hidden" value=",331%Gumla%District%P">'
        for broken in [html.replace(first_input, ''), first_input + html,
                       html.replace('<td>4</td>', '<td>3</td>')]:
            with self.subTest(html=broken), self.assertRaises(ValueError):
                parse_coverage_report(broken)

    def test_bad_reports_fail_instead_of_silently_dropping_data(self):
        for html in [report().replace('S.No.', 'Serial'),
                     report().replace('<td>1</td>', '<td>81</td>'),
                     report().replace('id="1432644"', 'id="999"'),
                     report(',18%Assam%State%unknown'),
                     report(',18%Assam%State%P,broken'),
                     report('', link=True), '<html>SQLGrammarException</html>']:
            with self.subTest(html=html), self.assertRaises(ValueError):
                parse_coverage_report(html)

    def test_root_level_selection_and_cycles(self):
        a = {'orgLocatedLevelCode': 10, 'parentOrgLocatedLevelCode': 0}
        b = {'orgLocatedLevelCode': 20, 'parentOrgLocatedLevelCode': 10}
        c = {'orgLocatedLevelCode': 30, 'parentOrgLocatedLevelCode': 999}
        self.assertEqual(root_levels([b, a, c]), [a, c])
        with self.assertRaises(ValueError):
            root_levels([dict(a, parentOrgLocatedLevelCode=20), b])
        self.assertEqual(root_levels([]), [])

    def test_root_level_with_null_parent(self):
        # Live NCST response (organization 717): ExceptTop still includes its
        # top level, with no parent, alongside the regional-centre level.
        root = {'orgLocatedLevelCode': 1243, 'parentOrgLocatedLevelCode': None,
                'orgLevelSpecificName': 'National Commission for Scheduled Tribes'}
        child = {'orgLocatedLevelCode': 1244, 'parentOrgLocatedLevelCode': 1243,
                 'orgLevelSpecificName': 'NCST Regional Centre'}
        self.assertEqual(root_levels([child, root]), [root])

    def test_invalid_and_duplicate_levels_still_rejected(self):
        valid = {'orgLocatedLevelCode': 10, 'parentOrgLocatedLevelCode': None}
        for code in (None, '', 'invalid'):
            with self.subTest(code=code), self.assertRaises(ValueError):
                root_levels([dict(valid, orgLocatedLevelCode=code)])
        for parent in ('', 'None', 'invalid'):
            with self.subTest(parent=parent), self.assertRaises(ValueError):
                root_levels([dict(valid, parentOrgLocatedLevelCode=parent)])
        with self.assertRaises(ValueError):
            root_levels([valid, valid.copy()])


class CoverageDownloaderTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(BaseDownloader.clear_cache)
        BaseDownloader.set_known_site_map(get_known_site_map())
        self.temp = self.enterContext(TemporaryDirectory())
        params = Params()
        params.base_raw_dir = self.temp
        self.ctx = Context(params)

    def test_registration_partitioning_and_serialization(self):
        parent = next(d for d in get_all_downloaders(self.ctx)
                      if d.name == 'ORG_UNIT_COVERAGE')
        central = {'Organization Code': '1', 'Organization Name': 'Central'}
        state = {'Organization Code': '1', 'Organization Name': 'State',
                 'State Code': '11', 'State Name': 'Sikkim'}
        with patch.object(BaseDownloader, 'records_from_downloader',
                          side_effect=[[central, central], [state]]):
            children = parent.get_child_downloaders()
        self.assertEqual(len(children), 2)
        self.assertNotEqual(children[0].get_filename(), children[1].get_filename())
        restored = BaseDownloader.from_dict('OrganizationCoverageDownloader',
                                            children[1].get_kwargs().copy(),
                                            self.ctx.params.__dict__.copy())
        self.assertEqual(restored.organization, state)

    def test_failure_never_publishes_partial_csv(self):
        child = OrganizationCoverageDownloader(name='probe', base_name='ORG_UNIT_COVERAGE',
                                               ctx=self.ctx, organization={
                                                   'Organization Code': '1',
                                                   'Organization Name': 'Example'})
        levels = [{'orgLocatedLevelCode': 10, 'parentOrgLocatedLevelCode': 0,
                   'orgLevelSpecificName': 'First'},
                  {'orgLocatedLevelCode': 20, 'parentOrgLocatedLevelCode': 0,
                   'orgLevelSpecificName': 'Second'}]
        with patch('scrape.org_coverage.DwrCaller.call', return_value=levels), \
                patch.object(child, 'get_level_records',
                             side_effect=[parse_coverage_report(report()), ValueError('bad report')]):
            with self.assertRaisesRegex(ValueError, 'bad report'):
                child.download()
        self.assertFalse(child.is_done())

    def test_empty_organization_is_checkpointed_and_parent_still_completes(self):
        parent = next(d for d in get_all_downloaders(self.ctx)
                      if d.name == 'ORG_UNIT_COVERAGE')
        organizations = [{'Organization Code': '716', 'Organization Name': 'DIT'},
                         {'Organization Code': '999', 'Organization Name': 'Populated'}]
        with patch.object(BaseDownloader, 'records_from_downloader',
                          side_effect=[organizations, []]):
            empty, populated = parent.get_child_downloaders()
        self.ctx._csrf_token_reports = 'report-token'
        self.ctx._session = Mock()
        def response(html):
            value = requests.Response()
            value.status_code = 200
            value._content = html.encode()
            return value
        self.ctx.session.get.return_value = response('<form/>')
        self.ctx.session.post.side_effect = [response(empty_report()), response(report())]
        level = {'orgLocatedLevelCode': 1238, 'parentOrgLocatedLevelCode': 1237,
                 'orgLevelSpecificName': 'Example'}
        with patch('scrape.org_coverage.DwrCaller.call', return_value=[level]), \
                patch('scrape.captcha_helper.CaptchaHelper.get_code', return_value='123456'):
            with self.assertLogs('scrape.org_coverage', level='INFO') as log:
                empty.download()
            self.assertIn('No coverage data reported for organization 716', log.output[0])
            self.assertTrue(empty.is_done())
            self.assertEqual(list(empty.retrieve_records()), [])
            populated.download()
            parent.download()
        self.assertTrue(parent.is_done())
        rows = list(parent.retrieve_records())
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row['Base Organization Code'] == '999' for row in rows))

    def test_http_404_is_not_accepted_as_an_empty_report(self):
        self.ctx._csrf_token_reports = 'report-token'
        self.ctx._session = Mock()
        response = requests.Response()
        response.status_code = 404
        response._content = empty_report().encode()
        self.ctx.session.post.return_value = response
        child = OrganizationCoverageDownloader(
            name='bad-http', base_name='ORG_UNIT_COVERAGE', ctx=self.ctx,
            organization={'Organization Code': '947', 'Organization Name': 'Example'})
        level = {'orgLocatedLevelCode': 1940, 'parentOrgLocatedLevelCode': 1939,
                 'orgLevelSpecificName': 'Example'}
        with patch('scrape.org_coverage.DwrCaller.call', return_value=[level]), \
                patch.object(child.captcha_helper, 'get_code', return_value='123456'):
            with self.assertRaises(requests.HTTPError):
                child.download()
        self.assertFalse(child.is_done())

    def test_state_request_retries_captcha_and_preserves_report_scope(self):
        self.ctx._csrf_token_reports = 'report-token'
        self.ctx._session = Mock()
        def response(text):
            value = requests.Response()
            value.status_code = 200
            value._content = text.encode()
            return value
        self.ctx.session.get.return_value = response('<form/>')
        self.ctx.session.post.side_effect = [
            response('The CAPTCHA image code was entered incorrectly.'), response(report())]
        child = OrganizationCoverageDownloader(
            name='state-probe', base_name='ORG_UNIT_COVERAGE', ctx=self.ctx,
            organization={'Organization Code': '441', 'Organization Name': 'Agriculture',
                          'State Code': '11', 'State Name': 'Sikkim'})
        level = {'orgLocatedLevelCode': 452, 'parentOrgLocatedLevelCode': 0,
                 'orgLevelSpecificName': 'Agriculture Department'}
        with patch('scrape.org_coverage.DwrCaller.call', return_value=[level]), \
                patch.object(child.captcha_helper, 'get_code', side_effect=['bad', 'good']):
            child.download()
        rows = list(child.retrieve_records())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['State Code'], '11')
        self.assertEqual(rows[0]['Report Org Located Level Code'], '452')
        self.assertEqual(set(rows[0]), set(child.expected_fields))
        sent = self.ctx.session.post.call_args.kwargs['data']
        self.assertEqual(sent['depatmentCode'], '441')
        self.assertEqual(sent['orgUnitCode'], '452')
        self.assertEqual(sent['stateCode'], '11')
        self.assertEqual(sent['state'], '1')
        self.assertNotIn('orgName', sent)
        self.assertNotIn('hierarchyIdList', sent)
        self.assertEqual(rows[0]['Base Organization Name'], 'Agriculture')
        self.assertEqual(rows[0]['Report Org Level Specific Name'], 'Agriculture Department')
        self.assertEqual(self.ctx.session.post.call_count, 2)

    def test_heading_rejection_is_avoided_without_changing_selection_or_metadata(self):
        self.ctx._csrf_token_reports = 'report-token'
        self.ctx._session = Mock()
        self.ctx.session.get.return_value = Mock()
        cases = [('29', '1288', '2829', 'Karnataka Public Works Department', 'PWD Division Office'),
                 ('8', '978', '2004', 'Public Works Department', 'PWD'),
                 ('5', '1555', '3513', 'Police', 'DIG Office')]
        for state, code, level_code, name, heading in cases:
            with self.subTest(organization=code):
                child = OrganizationCoverageDownloader(
                    name=f'heading-{code}', base_name='ORG_UNIT_COVERAGE', ctx=self.ctx,
                    csv_filename=f'heading-{code}.csv',
                    organization={'Organization Code': code, 'Organization Name': name,
                                  'State Code': state, 'State Name': 'Example'})
                level = {'orgLocatedLevelCode': int(level_code), 'parentOrgLocatedLevelCode': None,
                         'orgLevelSpecificName': heading}

                def post(url, *, data, **kwargs):
                    self.assertEqual((data['stateCode'], data['depatmentCode'], data['orgLocatedLevelCode'],
                                      data['orgUnitCode'], data['level']),
                                     (state, code, level_code, level_code, '0'))
                    result = requests.Response()
                    result.status_code = 404 if data.get('hierarchyIdList') else 200
                    result._content = report().encode()
                    return result

                self.ctx.session.post.side_effect = post
                with patch('scrape.org_coverage.DwrCaller.call', return_value=[level]), \
                        patch.object(child.captcha_helper, 'get_code', return_value='123456'):
                    child.download()
                rows = list(child.retrieve_records())
                self.assertEqual(len(rows), 2)
                self.assertTrue(all(r['Base Organization Name'] == name
                                    and r['Report Org Level Specific Name'] == heading
                                    and r['Report Org Located Level Code'] == level_code for r in rows))


if __name__ == '__main__':
    unittest.main()
