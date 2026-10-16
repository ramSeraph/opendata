import sys
from raw_wikidata import download_query

def get_data(repo, qid, fname):
    QUERY = f"SELECT ?item WHERE {{ ?item wdt:P31/wdt:P279* wd:{qid}. }}"
    return download_query(QUERY, fname)


if __name__ == '__main__':
    entity = sys.argv[1]
    repo = None
    if entity == 'state':
        print('getting states')
        get_data(repo, 'Q131541', 'data/states.jsonl')
    elif entity == 'division':
        print('getting divisions')
        get_data(repo, 'Q1230708', 'data/divisions.jsonl')
    elif entity == 'district':
        print('getting districts')
        get_data(repo, 'Q1149652', 'data/districts.jsonl')
    elif entity == 'subdivision':
        print('getting sub divisions')
        get_data(repo, 'Q7631016', 'data/subdivisions.jsonl')
    elif entity == 'subdistrict':
        print('getting sub districts')
        #get_data(repo, 'Q7694920', 'data/subdistricts.json')
        get_data(repo, 'Q105626471', 'data/subdistricts.jsonl')
    elif entity == 'block':
        print('getting blocks')
        get_data(repo, 'Q2775236', 'data/blocks.jsonl')
    elif entity == 'district_panchayat':
        print('getting district panchayats')
        get_data(repo, 'Q2758248', 'data/district_panchayats.jsonl')
    elif entity == 'block_panchayat':
        print('getting block panchayats')
        get_data(repo, 'Q4927168', 'data/block_panchayats.jsonl')
    elif entity == 'village':
        print('getting villages')

