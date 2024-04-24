import json
import csv
from pathlib import Path
from pprint import pprint

from common import (
    base_entity_checks, write_report,
    get_label, get_lgd_codes,
    get_located_in_ids, get_wd_entity_lgd_mapping,
    get_wd_data, get_lgd_data, get_entry_from_wd_id
)

from filters import filter_subdistrict, filter_district, filter_subdivision


lgd_fname = 'data/lgd/subdistricts.csv'
lgd_id_key = 'Sub-district Code'
lgd_name_key = 'Sub-district Name'
wd_fname = 'data/subdistricts.jsonl'

def hierarchy_check():
    report = { 'wrong_hierarchy': [] }
    
    wd_dist_map = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district)
    wd_dist_map_rev = {v:k for k,v in wd_dist_map.items() }

    filtered_subdivisions = get_wd_data('data/subdivisions.jsonl', filter_subdivision)
    for k,v in filtered_subdivisions.items():
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        v['super_id'] = located_in_ids[0]

    lgd_subdist_data = get_lgd_data(lgd_fname, lgd_id_key)

    filtered = get_wd_data(wd_fname, filter_subdistrict)
    for k,v in filtered.items():
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            continue
        lgd_code = lgd_codes[0]
        if lgd_code not in lgd_subdist_data:
            continue
        lgd_entry = lgd_subdist_data[lgd_code]
        expected_lgd_dist_code = lgd_entry['District Code']
        expected_dist_wd_id = wd_dist_map_rev[expected_lgd_dist_code]
        expected_dist_id = int(expected_dist_wd_id[1:])

        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0]
        parent_wd_id = f'Q{parent_id}'
        dist_id = None
        hierarchy = [ parent_id ]
        if parent_wd_id in filtered_subdivisions:
            dist_id = filtered_subdivisions[parent_wd_id]['super_id']
            hierarchy = [ dist_id ] + hierarchy
        else:
            dist_id = parent_id
        if f'Q{dist_id}' not in wd_dist_map or dist_id != expected_dist_id:
            
            label = get_label(v)
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(e) for e in hierarchy ],
                                              'expected': [ get_entry_from_wd_id(expected_dist_id) ]})
    return report


if __name__ == '__main__':
    report = base_entity_checks(entity_type='subdistrict',
                                lgd_fname=lgd_fname,
                                lgd_id_key=lgd_id_key, lgd_name_key=lgd_name_key,
                                wd_fname=wd_fname, wd_filter_fn=filter_subdistrict,
                                name_prefix_drops=['THE '], 
                                name_suffix_drops=[' SUBDISTRICT',
                                                   ' TEHSIL', ' TAHSIL',
                                                   ' TALUKA', ' TALUK', 
                                                   ' MANDAL', ' MANDALAM', ' MANDALA', 
                                                   ' COMMUNITY DEVELOPMENT BLOCK', ' BLOCK',
                                                   ' REVENUE CIRCLE', ' CIRCLE', ' CICLE', ' EAC', ' SDO', ' ADC', ' HQ',
                                                   ' SUBTEHSIL', ' ST',
                                                   ' SUBDIVISION',
                                                   ' P.S.', ' P.S', 'P.S.'],
                                name_match_threshold=0.99)
    report.update(hierarchy_check())
    pprint(report)
    write_report(report, 'subdistricts.json')

    


