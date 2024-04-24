import csv
import json
from pprint import pprint
from pathlib import Path

from common import base_entity_checks, get_wd_data, get_located_in_ids, write_report, get_entry_from_wd_id, get_label

from common import INDIA_ID

from filters import filter_state


def hierarchy_check(wd_fname=None, wd_filter_fn=None):

    report = { 'wrong_hierarchy': [] }

    filtered = get_wd_data(wd_fname, wd_filter_fn)
    for k,v in filtered.items():
        label = get_label(v) 
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        if located_in_ids[0] != INDIA_ID:
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(located_in_ids[0]) ],
                                              'expected': [ get_entry_from_wd_id(INDIA_ID) ] })
    return report

if __name__ == '__main__':
    wd_fname = 'data/states.jsonl'
    report = base_entity_checks(entity_type='state',
                                lgd_fname='data/lgd/states.csv', lgd_id_key='State Code', lgd_name_key='State Name(In English)',
                                wd_fname=wd_fname, wd_filter_fn=filter_state,
                                name_prefix_drops=['THE ', 'STATE OF ', 'UNION TERRITORY OF '], name_suffix_drops=['STATE'])

    report.update(hierarchy_check(wd_fname=wd_fname, wd_filter_fn=filter_state))
    pprint(report)
    write_report(report, 'states.json')
