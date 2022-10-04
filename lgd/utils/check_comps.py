import json
from scrape import get_all_downloaders
from scrape.base import Context

ctx = Context()
downloaders = get_all_downloaders(ctx)
comp_names = set([d.name for d in downloaders])
print(comp_names)

with open('site_map.json', 'r') as f:
    site_map = json.load(f)
    #print(site_map)
    listed = []
    for l in site_map:
        cs = l[1]
        if type(cs) == list:
            listed.extend(cs)
        else:
            listed.append(cs)

listed = set([ l for l in listed if l != 'IGNORE' ])
missing_comps = listed - comp_names
print(missing_comps)
