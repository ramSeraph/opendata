import json
import sys
import pywikibot
from pprint import pprint
from pathlib import Path
from pywikibot import pagegenerators

def get_entities(repo, qid):
    QUERY = f"SELECT ?item WHERE {{ ?item wdt:P31/wdt:P279* wd:{qid}. }}"
    
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(QUERY,site=repo))
    
    count = 0
    dicts = {}
    for item in generator:
        d = item.toJSON()
        dicts[item.id] = d
        count += 1
        print(f'handled {count} entries')
    return dicts

def get_data(repo, qid, fname):
    p = Path(fname)
    if p.exists():
        return
    data = get_entities(repo, qid)
    p.write_text(json.dumps(data, indent=2))

if __name__ == '__main__':
    entity = sys.argv[1]
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()
    if entity == 'state':
        print('getting states')
        get_data(repo, 'Q131541', 'data/states.json')
    elif entity == 'division':
        print('getting divisions')
        get_data(repo, 'Q1230708', 'data/divisions.json')
    elif entity == 'district':
        print('getting districts')
        get_data(repo, 'Q1149652', 'data/districts.json')
    elif entity == 'subdivision':
        print('getting sub divisions')
        get_data(repo, 'Q7631016', 'data/subdivisions.json')
    elif entity == 'subdistrict':
        print('getting sub districts')
        #get_data(repo, 'Q7694920', 'data/subdistricts.json')
        get_data(repo, 'Q105626471', 'data/subdistricts.json')
    elif entity == 'block':
        print('getting blocks')
        get_data(repo, 'Q2775236', 'data/blocks.json')
    elif entity == 'village':
        print('getting villages')
