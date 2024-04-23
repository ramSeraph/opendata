import csv
import json
from pprint import pprint
from pathlib import Path

from common import (
    base_entity_checks, write_report,
    get_label, get_located_in_ids,
    get_wd_entity_lgd_mapping, get_wd_data,
    get_entry_from_wd_id
)

from filters import filter_district, filter_subdivision


wd_fname = 'data/subdivisions.json'
def hierarchy_check():
    report = { 'wrong_hierarchy': [] }
    dist_mapping = get_wd_entity_lgd_mapping('data/districts.json', filter_district)

    filtered = get_wd_data(wd_fname, filter_subdivision)
    for k,v in filtered.items():
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0] 
        parent_wid = f'Q{parent_id}'
        if parent_wid not in dist_mapping:
            label = get_label(v)
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(parent_id) ],
                                              'expected': [{ 'label': 'Any District of India' }]})

    return report


if __name__ == '__main__':
    report = base_entity_checks(entity_type='subdivision',
                                has_lgd=False,
                                wd_fname=wd_fname, wd_filter_fn=filter_subdivision)
    report.update(hierarchy_check())
    pprint(report)
    write_report(report, 'subdivisions.json')
