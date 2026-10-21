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
        self.assertEqual(self.ctx.session.post.call_count, 2)


if __name__ == '__main__':
    unittest.main()
