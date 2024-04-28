from pprint import pprint

from common import (
    base_entity_checks, write_report,
    get_label, get_located_in_ids,
    get_wd_entity_lgd_mapping, get_wd_data,
    get_entry_from_wd_id
)

from filters import filter_state, filter_division


wd_fname = 'data/divisions.jsonl'
def hierarchy_check():
    report = { 'wrong_hierarchy': [] }
    state_mapping = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state)

    filtered = get_wd_data(wd_fname, filter_division)
    for k,v in filtered.items():
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0] 
        parent_wid = f'Q{parent_id}'
        if parent_wid not in state_mapping:
            label = get_label(v)
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(parent_id) ],
                                              'expected': [{ 'label': 'Any State of India' }]})

    return report

def suffix_check():
    report = { 'wrong_suffix': [] }
    filtered = get_wd_data(wd_fname, filter_division)

    for k,v in filtered.items():
        label = get_label(v)
        if label.upper().endswith(' DIVISION'):
            continue
        report['wrong_suffix'].append({'wikidata_id': k,
                                       'wikidata_label': label,
                                       'expected_suffix': ' division'})
    return report



if __name__ == '__main__':
    report = base_entity_checks(entity_type='division',
                                has_lgd=False,
                                wd_fname=wd_fname, wd_filter_fn=filter_division)
    report.update(hierarchy_check())
    report.update(suffix_check())
    pprint(report)
    write_report(report, 'divisions.json')
