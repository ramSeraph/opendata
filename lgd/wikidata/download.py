import json
import sys
import pywikibot
from pprint import pprint
from pathlib import Path
from pywikibot import pagegenerators
from pywikibot.data.sparql import SparqlQuery

def get_data(repo, qid, fname):
    p = Path(fname)
    already_seen = set()
    if p.exists():
        with open(p, 'r') as f:
            for line in f:
                if line.strip() == '':
                    continue
                item = json.loads(line)
                k = item['id']
                already_seen.add(k)

    QUERY = f"SELECT ?item WHERE {{ ?item wdt:P31/wdt:P279* wd:{qid}. }}"

    sparql = SparqlQuery(repo=repo)
    qids = sparql.get_items(QUERY, item_name='item')
    qids = list(qids - already_seen)
    
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.PagesFromTitlesGenerator(qids,site=repo))

    #generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(QUERY,site=repo))
    
    count = 0
    with open(p, 'a') as f:
        for item in generator:
            d = item.toJSON()
            f.write(json.dumps({'id': item.id, 'data': d}))
            f.write('\n')
            count += 1
            print(f'handled {count} entries')


if __name__ == '__main__':
    entity = sys.argv[1]
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()
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
