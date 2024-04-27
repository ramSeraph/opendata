import csv
import json
from pprint import pprint
from pathlib import Path

from common import base_entity_checks, get_wd_data, get_located_in_ids, write_report, get_entry_from_wd_id, get_label

from common import INDIA_ID, STATE_ID, UT_ID

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

# very unlikely to be hit
def get_correction_info(lgd_entry):

    name = lgd_entry['lgd_name']
    label = f'{name}'

    sname = lgd_entry['State Name']
    desc = f'state in India'

    state_or_ut = lgd_entry['State or UT']
    inst_of = f'Q{STATE_ID}' if state_or_ut == 'S' else f'Q{UT_ID}'

    loc_in = f'Q{INDIA_ID}'

    i_date = datetime.strptime(lgd_entry['Effective Date'], '%d%b%Y')
    inception = i_date.strftime('+%Y-%m-%dT00:00:00Z/11')
    correction_info = {
        'label': label,
        'desc': desc,
        'inst_of': inst_of,
        'loc_in': loc_in,
        'inception': inception,
        'lgd_code': lgd_entry['lgd_code'],
    }
    return correction_info


if __name__ == '__main__':
    wd_fname = 'data/states.jsonl'
    report = base_entity_checks(entity_type='state',
                                lgd_fname='data/lgd/states.csv', lgd_id_key='State Code', lgd_name_key='State Name(In English)',
                                lgd_url_fn=lambda x: { 'base': 'https://lgdirectory.gov.in/globalviewStateDetail.do', 'params': {'globalstateId': str(x) }},
                                lgd_correction_fn=get_correction_info,
                                wd_fname=wd_fname, wd_filter_fn=filter_state,
                                name_prefix_drops=['THE ', 'STATE OF ', 'UNION TERRITORY OF '], name_suffix_drops=['STATE'])

    report.update(hierarchy_check(wd_fname=wd_fname, wd_filter_fn=filter_state))
    pprint(report)
    write_report(report, 'states.json')
