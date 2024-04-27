import re
import csv
import copy
import json
from pathlib import Path
from datetime import datetime

import requests
from requests.models import PreparedRequest
import unidecode
import pywikibot
from indictrans import Transliterator
from bs4 import BeautifulSoup

from lev import masala_levenshtein

st_himachal = { "name": "Himachal pradesh", "suffix": "Subtehsil", "type": "Subtehsil", "wd_id": "Q123264643" }
st_haryana = { "name": "Haryana", "suffix": "Subtehsil", "type": "Subtehsil", "wd_id": "Q123264644" }
state_info = {
    "35": { "name": "Andaman And Nicobar Islands", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987709" },
    "28": { "name": "Andhra Pradesh", "suffix": "Mandal", "type": "Tehsil", "wd_id": "Q122987710"  },
    "12": { "name": "Arunachal Pradesh", "suffix": "Circle", "type": "Tehsil", "long": "Circle", "wd_id": "Q122987711"  },
    "18": { "name": "Assam", "suffix": "Circle", "type": "Tehsil", "long": "Circle", "wd_id": "Q122987712", "wd_block_id": "Q123009185" },
    "10": { "name": "Bihar", "suffix": "Block", "type": "Block", "wd_id": "Q122987713"  }, # tehsils exist and are called aanchals
    "4": { "name": "Chandigarh", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987714"  }, # TODO: check 
    "22": { "name": "Chhattisgarh", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987715", "wd_block_id": "Q123009223"  }, # TODO: check 
    "7": { "name": "Delhi", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987716"  }, # TODO: check 
    "30": { "name": "Goa", "suffix": "Taluk", "type": "Tehsil", "wd_id": "Q122987717"  },
    "24": { "name": "Gujarat", "suffix": "Taluka", "type": "Tehsil", "wd_id": "Q122987718"  }, # TODO: check 
    "6": { "name": "Haryana", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987719", "alts": [ st_haryana ]  }, # TODO: check 
    "2": { "name": "Himachal Pradesh", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987720", "alts": [ st_himachal ]  },
    "1": { "name": "Jammu And Kashmir", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987721"  }, # TODO: check 
    "20": { "name": "Jharkhand", "suffix": "Block", "type": "Block", "wd_id": "Q122987723"  }, # TODO: check 
    "29": { "name": "Karnataka", "suffix": "Taluk", "type": "Tehsil", "wd_id": "Q122987724"  }, # TODO: check 
    "32": { "name": "Kerala", "suffix": "Taluk", "type": "Tehsil", "wd_id": "Q7680362" }, # TODO: check 
    "37": { "name": "Ladakh", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987726"  }, # TODO: check 
    "31": { "name": "Lakshadweep", "suffix": "Subdivision", "type": "Subdivision", "wd_id": "Q122987727"  },
    "23": { "name": "Madhya Pradesh", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987728"  }, # TODO: check 
    "27": { "name": "Maharashtra", "suffix": "Taluka", "type": "Tehsil", "wd_id": "Q13119795" }, # TODO: check 
    "14": { "name": "Manipur", "suffix": "Subdivision", "type": "Subdivision", "wd_id": "Q122987729"  },
    "17": { "name": "Meghalaya", "suffix": "Block", "type": "Block", "wd_id": "Q122987730"  }, # C. & R. D. Block R is for Rural?
    "15": { "name": "Mizoram", "suffix": "Block", "type": "Block", "long": "Rural Development Block", "wd_id": "Q122987731"  }, # Rural Development Block
    "13": { "name": "Nagaland", "suffix": "Circle", "type": "Tehsil", "wd_id": "Q122987732"  },
    "21": { "name": "Odisha", "suffix": "Police Station", "label_suffix": "P.S.", "type": "Police Station", "wd_id": "Q122986857", "wd_block_id": "Q61863384" }, # Tehsils exist, Police station maps are available in the Census Atlas
    "34": { "name": "Puducherry", "suffix": "Taluk", "type": "Tehsil", "wd_id": "Q122987733"  },
    "3": { "name": "Punjab", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987734", "wd_block_id": "Q123200469" }, # TODO: check 
    "8": { "name": "Rajasthan", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987735", "wd_block_id": "Q123009239"  }, # TODO: check 
    "11": { "name": "Sikkim", "suffix": "Subdivision", "type": "Subdivision", "wd_id": "Q122956696" }, # revenue circles exist
    "33": { "name": "Tamil Nadu", "suffix": "Taluk", "type": "Tehsil", "wd_id": "Q122987736", "wd_block_id": "Q123009250"  }, # TODO: check
    "36": { "name": "Telangana", "suffix": "Mandal", "type": "Tehsil", "wd_id": "Q122987738" }, # TODO: check 
    "38": { "name": "The Dadra And Nagar Haveli And Daman And Diu", "suffix": "Taluk", "type": "Tehsil", "wd_id": "Q122987739"  }, # TODO: check 
    "16": { "name": "Tripura", "suffix": "Block", "type": "Block", "long": "Development Block", "wd_id": "Q122987740"  }, # Development Block
    "5": { "name": "Uttarakhand", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987741", "wd_block_id": "Q123009294"  },
    "9": { "name": "Uttar Pradesh", "suffix": "Tehsil", "type": "Tehsil", "wd_id": "Q122987742", "wd_block_id": "Q123009286" },
    "19": { "name": "West Bengal", "suffix": "Block", "type": "Block", "wd_id": "Q122987743"  },
}

SUBDIST_ID = 105626471
TEHSIL_ID = 817477
TEHSIL_INDIA_ID = 7694920
CD_BLOCK_INDIA_ID = 2775236

SUBDIV_ID = 7631016
SUBDIV_WESTBENGAL = 13058507
SUBDIV_REVENUE = 24943410
SUBDIV_ODISHA = 60843390
ALL_SUBDIV_IDS = [ SUBDIV_ID, SUBDIV_WESTBENGAL, SUBDIV_REVENUE, SUBDIV_ODISHA ]

SUBDIST_IDS = [ int(v['wd_id'][1:]) for v in state_info.values() ]

SUBTEHSIL_IDS = [ 123264644, 123264643 ]

ALL_SUBDIST_IDS = [ SUBDIST_ID, TEHSIL_ID, TEHSIL_INDIA_ID ] + SUBDIST_IDS + SUBTEHSIL_IDS

ALL_TEHSIL_IDS = [  SUBDIST_ID, TEHSIL_ID, TEHSIL_INDIA_ID ] + [ int(v['wd_id'][1:]) for v in state_info.values() if v['type'] == 'Tehsil' ] 

ALL_BLOCK_IDS = [ CD_BLOCK_INDIA_ID ] + [ int(v['wd_id'][1:]) for v in state_info.values() if v['type'] == 'Block' ] +  [ int(v['wd_block_id'][1:]) for v in state_info.values() if 'wd_block_id' in v ] 

P_INSTANCE_OF = 'P31'
P_REPLACED_BY = 'P1366'
P_DISSOLVED = 'P576'
P_COUNTRY = 'P17'
P_LOCATED_IN = 'P131'

P_LGD_CODE = 'P6425'
P_CENSUS_CODE = 'P5578'
P_END_TIME = 'P582'

STATE_ID = 12443800
UT_ID = 467745 
INDIA_ID = 668
PAK_ID = 843
DIST_ID = 1149652
DIV_ID = 1230708
PROPOSED_ENTITY = 64728694

LGD_URL="https://lgdirectory.gov.in/downloadDirectory.do?"

te_to_en_translit = Transliterator(source='tel', target='eng', build_lookup=True)
hi_to_en_translit = Transliterator(source='hin', target='eng', build_lookup=True)
mr_to_en_translit = Transliterator(source='mar', target='eng', build_lookup=True)


def get_label_translit(v):
    labels = v.get('labels', {})
    if 'en' in labels:
        label = labels['en']['value']
    else:
        if 'te' in labels:
            te_label = labels['te']['value']
            label = te_to_en_translit.transform(te_label)
        elif 'hi' in labels:
            hi_label = labels['hi']['value']
            label = hi_to_en_translit.transform(hi_label)
        elif 'mr' in labels:
            mr_label = labels['mr']['value']
            label = mr_to_en_translit.transform(mr_label)
        elif 'new' in labels:
            new_label = labels['new']['value']
            label = hi_to_en_translit.transform(new_label)
        elif 'de' in labels:
            de_label = labels['de']['value']
            label = de_label
        else:
            print('labels:', labels)
            label = 'NA'
    return label


def get_label(v):
    labels = v.get('labels', {})
    if 'en' in labels:
        label = labels['en']['value']
    else:
        print('labels:', labels)
        label = 'NA'
    return label


def get_census_code(v):
    census_code = 'NA'
    claims = v['claims'].get(P_CENSUS_CODE, None)
    if claims is None:
        return census_code
    for c in claims:
        census_code = c['mainsnak']['datavalue']['value']
    return census_code


def get_lgd_codes(v):
    lgd_codes = []
    claims = v['claims'].get(P_LGD_CODE, None)
    if claims is None:
        return lgd_codes
    for c in claims:
        lgd_code = c['mainsnak']['datavalue']['value']
        lgd_codes.append(lgd_code)
    return lgd_codes
 

def is_claim_current(c):
    return 'qualifiers' not in c or \
            P_END_TIME not in c['qualifiers'] or \
            len(c['qualifiers'][P_END_TIME]) == 0 or \
            'datavalue' not in c['qualifiers'][P_END_TIME][0]


def is_inactive(v):
    return P_REPLACED_BY in v['claims'] or P_DISSOLVED in v['claims']


def is_current_instance_of(v, inst_types):
    if is_inactive(v):
        return False
    inst_claims = v['claims'][P_INSTANCE_OF]
    still_valid = False
    for c in inst_claims:
        inst_of = c['mainsnak']['datavalue']['value']['numeric-id'] 
        if inst_of == PROPOSED_ENTITY:
            return False
        if inst_of not in inst_types:
            continue
        if still_valid:
            continue
        if is_claim_current(c):
            still_valid = True
    return still_valid


def get_aliases(v):
    en_aliases = [ e['value'] for e in v.get('aliases', {}).get('en', []) if e['language'] == 'en' ]
    return en_aliases


def clean_string(s, prefix_drops, suffix_drops):
    s = unidecode.unidecode(s)
    s = s.upper()
    for p in prefix_drops:
        if s.startswith(p):
            s = s[len(p):]

    for p in suffix_drops:
        if s.endswith(p):
            s = s[:-len(p)]

    s = s.strip()
    rex = re.compile(r'\s+')
    s = rex.sub(' ', s)
    s = s.replace('-', ' ')
    return s


def get_distance(s1, s2, prefix_drops, suffix_drops):
    cs1 = clean_string(s1, prefix_drops, suffix_drops)
    cs2 = clean_string(s2, prefix_drops, suffix_drops)
    dist = masala_levenshtein(cs1, cs2)
    return dist


def get_best_match(name, v, prefix_drops=[], suffix_drops=[], translit=False):
    if translit:
        label = get_label_translit(v)
    else:
        label = get_label(v)
    aliases = get_aliases(v)
    label_dist = get_distance(name, label, prefix_drops, suffix_drops)
    out_dist = label_dist
    out = label
    #print(f'{label=} {label_dist:}')
    for alias in aliases:
        alias_dist = get_distance(name, alias, prefix_drops, suffix_drops)
        if alias_dist < out_dist:
            out = alias
            out_dist = alias_dist
        #print(f'\t{alias=} {alias_dist:}')
    return out, out_dist


def is_in_india(v):
    country_claims = v['claims'].get(P_COUNTRY, [])
    for c in country_claims:
        country_id = c['mainsnak']['datavalue']['value']['numeric-id'] 
        if country_id == INDIA_ID:
            return True
    return False


def get_instance_of_ids(v):
    if is_inactive(v):
        return False
    inst_claims = v['claims'][P_INSTANCE_OF]
    ids = []
    for c in inst_claims:
        if not is_claim_current(c):
            continue
        inst_of = c['mainsnak']['datavalue']['value']['numeric-id'] 
        ids.append(inst_of)
    return ids


def get_located_in_ids(v):
    if is_inactive(v):
        return False
    loc_claims = v['claims'].get(P_LOCATED_IN, [])
    ids = []
    for c in loc_claims:
        if not is_claim_current(c):
            continue
        loc_in = c['mainsnak']['datavalue']['value']['numeric-id'] 
        ids.append(loc_in)
    return ids


def get_lgd_data(fname, key):
    lgd_data = {}
    with open(fname, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = r[key]
            lgd_data[code] = r
    return lgd_data

def get_wd_data(fname, filter_fn):
    filtered = {}
    with open(fname, 'r') as f:
        for line in f:
            if line.strip() == '':
                continue
            item = json.loads(line)
            k = item['id']
            v = item['data']
            if not filter_fn(v):
                print("filtering:", k, get_label(v))
                continue
            filtered[k] = v
    return filtered


page_cache = None
repo = None

def get_entry_from_wd_id(wd_num_id):
    global repo
    global page_cache

    pcache_fname = 'data/cache.jsonl'
    if page_cache is None:
        page_cache = {}
        if Path(pcache_fname).exists():
            with open(pcache_fname, 'r') as f:
                for line in f:
                    e = json.loads(line)
                    page_cache[e['id']] = e['data']

    if wd_num_id in page_cache:
        return page_cache[wd_num_id]

    if repo is None:
        site = pywikibot.Site("wikidata", "wikidata")
        repo = site.data_repository()
    item = pywikibot.ItemPage(repo, f'Q{wd_num_id}')
    label = item.get()['labels'].get('en', 'NA')
    data = { 'id': f'Q{wd_num_id}', 'label': label }
    page_cache[wd_num_id] = data
    with open(pcache_fname, 'a') as f:
        f.write(json.dumps({ 'id': wd_num_id, 'data': data }))
        f.write('\n')
    return page_cache[wd_num_id]



def base_entity_checks(entity_type=None,
                       has_lgd=True, lgd_fname=None, lgd_id_key=None, lgd_name_key=None,
                       lgd_url_fn=None, lgd_correction_fn=None,
                       wd_fname=None, wd_filter_fn=lambda x:True,
                       name_prefix_drops=[], name_suffix_drops=[], name_match_threshold=0.0):

    report = {
        'not_in_india': [],
        'multiple_located_in': [],
        'multiple_instance_of': [],
    }
    if has_lgd:
        report.update({
            'missing': [],
            'no_lgd_id': [],
            'unknown_lgd_id': [],
            'name_mismatch': [],
            'duplicate_lgd_id': [],
            'multiple_lgd_ids': [],
        })

    if has_lgd:
        lgd_data = get_lgd_data(lgd_fname, lgd_id_key)

    filtered = get_wd_data(wd_fname, wd_filter_fn)
    def create_ext_lgd_entry(lgd_entry):
        e = copy.copy(lgd_entry)
        e['lgd_code'] = e[lgd_id_key]
        e['lgd_name'] = e[lgd_name_key]
        del e[lgd_id_key]
        del e[lgd_name_key]
        return e

    seen = {}
    for k,v in filtered.items():
        #census_code = get_census_code(v)
        if has_lgd:
            lgd_codes = get_lgd_codes(v)
        label = get_label(v) 
        if not is_in_india(v):
            report['not_in_india'].append({'wikidata_id': k, 'wikidata_label': label})
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            print(f'multiple located_in {label}({k}): {located_in_ids}')
            report['multiple_located_in'].append({'wikidata_id': k, 'wikidata_label': label, 'located_in_entries': [ get_entry_from_wd_id(i) for i in located_in_ids ]})
        inst_of_ids = get_instance_of_ids(v)
        if len(inst_of_ids) != 1:
            print(f'multiple instance of {label}({k}): {inst_of_ids}')
            report['multiple_instance_of'].append({'wikidata_id': k, 'wikidata_label': label, 'inst_of_entries': [ get_entry_from_wd_id(i) for i in inst_of_ids ]})

        if not has_lgd:
            continue

        if len(lgd_codes) == 0:
            # TODO: locate best match?
            report['no_lgd_id'].append({
                'wikidata_id': k, 
                'wikidata_label': label
            })
            continue
        if len(lgd_codes) > 1:
            lgd_entries = [ create_ext_lgd_entry(lgd_data[l]) if l in lgd_data else { 'lgd_code': l, 'lgd_name': 'NA' } for l in lgd_codes ]
            for e in lgd_entries:
                if len(e) == 2:
                    report['unknown_lgd_id'].append({'wikidata_id': k, 'wikidata_label': label, 'lgd_code': e['lgd_code']})

                
            report['multiple_lgd_ids'].append({
                'wikidata_id': k,
                'wikidata_label': label,
                'lgd_entries': lgd_entries,
            })
            continue

        lgd_code = lgd_codes[0]
        if lgd_code not in lgd_data:
            report['unknown_lgd_id'].append({'wikidata_id': k, 'wikidata_label': label, 'lgd_code': lgd_code})
            print(f'{k} {label}, unknown {lgd_code=}')
            continue

        lgd_entry = lgd_data[lgd_code]
        lgd_name = lgd_entry[lgd_name_key]
        if lgd_code in seen:
            lgd_entry_out = create_ext_lgd_entry(lgd_entry)
            report['duplicate_lgd_id'].append({
                'lgd_entry': lgd_entry_out,
                'curr': k,
                'curr_label': label,
                'prev': seen[lgd_code][0],
                'prev_label': seen[lgd_code][1]
            })
        else:
            seen[lgd_code] = (k, label)
            #print(lgd_name)
            match, match_dist = get_best_match(lgd_name, v,
                                               prefix_drops=name_prefix_drops,
                                               suffix_drops=name_suffix_drops,
                                               translit=True)
            if match_dist > name_match_threshold:
                print(f'{match=} {match_dist=}')
                print('')
                lgd_entry_out = create_ext_lgd_entry(lgd_entry)
                report['name_mismatch'].append({
                    'wikidata_id': k,
                    'wikidata_label': label,
                    'lgd_entry': lgd_entry_out
                })

    if not has_lgd:
        return report

    all_lgd_ids = set(lgd_data.keys())
    missing_in_wikidata = all_lgd_ids - set(seen.keys())
    if len(missing_in_wikidata) > 0:
        for lgd_id in missing_in_wikidata:
            lgd_entry = lgd_data[lgd_id]
            lgd_entry_out = create_ext_lgd_entry(lgd_entry)
            url_info = lgd_url_fn(lgd_id)
            req = PreparedRequest()
            req.prepare_url(url_info['base'], url_info['params'])
            lgd_entry_out['lgd_url'] = req.url
            print(req.url)
            lgd_entry_out['Effective Date'] = get_effective_date(url_info['base'], url_info['params'])
            correction_info = lgd_correction_fn(lgd_entry_out)
            #TODO: locate and add best matches?
            report['missing'].append({'lgd_entry': lgd_entry_out, 'correction_info': correction_info})
    return report


def get_wd_entity_lgd_mapping(wd_fname, wd_filter_fn):
    filtered = get_wd_data(wd_fname, wd_filter_fn)
    mapping = {}
    for k,v in filtered.items():
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            # TODO: rethink
            mapping[k] = 'NA'
            continue
        mapping[k] = lgd_codes[0]

    return mapping



def write_report(report, fname):
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True, parents=True)
    report_file = reports_dir / fname
    report_file.write_text(json.dumps(report, indent=2))


def get_effective_date(url, params):
    print(url, params)
    resp = requests.get(url, params)
    if not resp.ok:
        raise Exception('unable to retrieve url')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    trs = soup.find_all('tr')
    for tr in trs:
        if 'Effective Date' in tr.text:
            tds = tr.find_all('td')
            date_str = tds[1].text
            return datetime.strftime(datetime.strptime(date_str, '%d/%m/%Y'), '%d%b%Y')
