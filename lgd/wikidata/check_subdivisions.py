from pprint import pprint

from common import (
    base_entity_checks, write_report,
    get_label, get_located_in_ids,
    get_wd_entity_lgd_mapping, get_wd_data,
    get_entry_from_wd_id
)

from filters import filter_district, filter_subdivision


wd_fname = 'data/subdivisions.jsonl'
def hierarchy_check():
    report = { 'wrong_hierarchy': [] }
    dist_mapping = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district)

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

wd_dist_data = None
def check_if_located_in_district(wid):
    global wd_dist_data
    if wd_dist_data is None:
        wd_dist_data = get_wd_data('data/districts.jsonl', filter_district)
    qid = f'Q{wid}'
    if qid in wd_dist_data:
        return {'ok': True}
    return {'ok': False, 'expected': 'located in a District'}



if __name__ == '__main__':
    report = base_entity_checks(entity_type='subdivision',
                                has_lgd=False,
                                check_expected_located_in_fn=check_if_located_in_district,
                                wd_fname=wd_fname, wd_filter_fn=filter_subdivision)
    report.update(hierarchy_check())
    #report.update(suffix_check())
    pprint(report)
    write_report(report, 'subdivisions.json')
