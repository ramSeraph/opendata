import csv
import json
from pprint import pprint
from pathlib import Path

from common import (
    base_entity_checks, write_report,
    get_label, get_lgd_codes,
    get_located_in_ids, get_wd_entity_lgd_mapping,
    get_wd_data, get_lgd_data, get_entry_from_wd_id
)

from filters import filter_district, filter_state, filter_division

lgd_fname = 'data/lgd/districts.csv'
lgd_id_key = 'District Code'
lgd_name_key = 'District Name (In English)'
wd_fname = 'data/districts.jsonl'

def hierarchy_check():
    report = { 'wrong_hierarchy': [] }

    wd_state_map = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state)
    wd_state_map_rev = {v:k for k,v in wd_state_map.items() }

    filtered_divisions = get_wd_data('data/divisions.jsonl', filter_division)
    for k,v in filtered_divisions.items():
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        v['super_id'] = located_in_ids[0]

    lgd_dist_data = get_lgd_data(lgd_fname, lgd_id_key)

    filtered = get_wd_data(wd_fname, filter_district)
    for k,v in filtered.items():
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            continue
        lgd_code = lgd_codes[0]
        if lgd_code not in lgd_dist_data:
            continue
        lgd_entry = lgd_dist_data[lgd_code]
        expected_lgd_state_code = lgd_entry['State Code']
        expected_state_wd_id = wd_state_map_rev[expected_lgd_state_code]
        expected_state_id = int(expected_state_wd_id[1:])

        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0]
        parent_wd_id = f'Q{parent_id}'
        state_id = None
        hierarchy = [ parent_id ]
        if parent_wd_id in filtered_divisions:
            state_id = filtered_divisions[parent_wd_id]['super_id']
            hierarchy = [ state_id ] + hierarchy
        else:
            state_id = parent_id
        if f'Q{state_id}' not in wd_state_map or state_id != expected_state_id:
            
            label = get_label(v)
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(e) for e in hierarchy ],
                                              'expected': [ get_entry_from_wd_id(expected_state_id) ]})

        return report


def suffix_check():
    report = { 'wrong_suffix': [] }
    filtered = get_wd_data(wd_fname, filter_district)

    for k,v in filtered.items():
        label = get_label(v)
        if label.upper().endswith(' DISTRICT'):
            continue
        report['wrong_suffix'].append({'wikidata_id': k,
                                       'wikidata_label': label,
                                       'expected_suffix': ' district'})
    return report


if __name__ == '__main__':
    report = base_entity_checks(entity_type='district',
                                lgd_fname=lgd_fname, lgd_id_key=lgd_id_key, lgd_name_key=lgd_name_key,
                                lgd_url_fn=lambda x: f'https://lgdirectory.gov.in/globalviewDistrictDetail.do?globaldistrictId={x}',
                                wd_fname=wd_fname, wd_filter_fn=filter_district,
                                name_prefix_drops=['THE '], name_suffix_drops=['DISTRICT'], name_match_threshold=0.0)
    report.update(hierarchy_check())
    report.update(suffix_check())
    pprint(report)
    write_report(report, 'districts.json')
