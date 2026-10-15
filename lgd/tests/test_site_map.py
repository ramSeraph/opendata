import unittest

from scrape import get_all_downloaders
from scrape.base import BaseDownloader, Context, Params
from scrape.site_map import get_changes_in_site_map, get_known_site_map


class SiteMapTests(unittest.TestCase):
    def test_unlisted_reports_do_not_repeat_removal_alerts(self):
        known = [{'dropdown': ['Reports', 'Active']},
                 {'dropdown': ['Reports', 'Retired'], 'listed': False}]
        self.assertEqual(get_changes_in_site_map(known, [['Reports', 'Active']]),
                         {'added': [], 'removed': []})

    def test_new_and_returning_reports_are_additions(self):
        known = [{'dropdown': ['Reports', 'Active']},
                 {'dropdown': ['Reports', 'Retired'], 'listed': False}]
        scraped = [['Reports', 'Active'], ['Reports', 'New'], ['Reports', 'Retired']]
        self.assertEqual(get_changes_in_site_map(known, scraped),
                         {'added': [['Reports', 'New'], ['Reports', 'Retired']], 'removed': []})

    def test_missing_active_report_is_still_a_removal(self):
        self.assertEqual(get_changes_in_site_map([{'dropdown': ['Reports', 'Active']}], []),
                         {'added': [], 'removed': [['Reports', 'Active']]})

    def test_unlisted_downloads_and_historical_metadata_are_retained(self):
        self.addCleanup(BaseDownloader.clear_cache)
        known = get_known_site_map()
        invalidated = next(item for item in known if item['comp'] == 'INVALIDATED_VILLAGES')
        self.assertFalse(invalidated['listed'])
        self.assertEqual(invalidated['file'], 'invalidated_census_villages.csv')
        BaseDownloader.set_known_site_map(known)
        active = {item.name for item in get_all_downloaders(Context(Params()))}
        self.assertIn('INVALIDATED_VILLAGES', active)
        self.assertIn('CHANGES', BaseDownloader.comp_map)


if __name__ == '__main__':
    unittest.main()
