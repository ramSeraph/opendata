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
from bs4 import BeautifulSoup

from lev import masala_levenshtein

st_himachal = { "name": "Himachal pradesh", "suffix": "Subtehsil", "type": "Subtehsil", "wd_id": "Q123264643" }
st_haryana = { "name": "Haryana", "suffix": "Subtehsil", "type": "Subtehsil", "wd_id": "Q123264644" }
state_info = {
    "35": {
        "name": "Andaman And Nicobar Islands",
        "suffix": "Tehsil",
        "type": "Tehsil", 
        "wd_id": "Q122987709", 
        "dp_suffix": "Zilla Parishad",
        "bp_suffix": "Panchayat Samiti",
    },
    "28": {
        "name": "Andhra Pradesh",
        "suffix": "Mandal",
        "type": "Tehsil",
        "wd_id": "Q122987710",
        "wd_block_id": "Q122987710",
        "wd_subdiv_id": "Q125626445",
        "subdiv_label_suffix": "revenue division",
        "dp_suffix": "Zilla Parishad",
        "bp_suffix": "Mandal Panchayat",
    },
    "12": {
        "name": "Arunachal Pradesh",
        "suffix": "Circle",
        "type": "Tehsil", 
        "long": "Circle",
        "wd_id": "Q122987711",
        "wd_div_id": "Q125907363",
        "divs_in_main_hierarchy": False,
        "dp_suffix": "Zilla Parishad",
    },
    "18": {
        "name": "Assam",
        "suffix": "Circle",
        "type": "Tehsil",
        "long": "Circle",
        "wd_id": "Q122987712",
        "wd_div_id": "Q125907354",
        "wd_block_id": "Q123009185",
        "dp_suffix": "Zilla Parishad",
        "bp_suffix": "Anchalik Panchayat",
    },
    "10": {
        "name": "Bihar",
        "suffix": "Block",
        "type": "Block",
        "wd_id": "Q122987713",
        "wd_div_id": "Q125907353",
        "wd_subdiv_id": "Q125631936",
        "dp_suffix": "Zilla Parishad",
        "bp_suffix": "Panchayat Samiti",
    }, # tehsils exist and are called aanchals
    "4": { 
        "name": "Chandigarh",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987714",
        "dp_suffix": "Zilla Parishad",
        "bp_suffix": "Panchayat Samiti",
    }, # TODO: check 
    "22": {
        "name": "Chhattisgarh",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987715", 
        "wd_div_id": "Q125907349",
        "wd_block_id": "Q123009223",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Janpad Panchayat",
     }, # TODO: check 
    "7": {
        "name": "Delhi",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987716",
        "wd_div_id": "Q125907356",
    }, # TODO: check 
    "30": {
        "name": "Goa",
        "suffix": "Taluk",
        "type": "Tehsil",
        "wd_id": "Q122987717",
        "dp_suffix": "Zilla Panchayat",
     },
    "24": {
        "name": "Gujarat",
        "suffix": "Taluka",
        "type": "Tehsil",
        "wd_id": "Q122987718",
        "wd_subdiv_id": "Q125923559",
        "dp_suffix": "District Panchayat",
        "bp_suffix": "Taluk Panchayat",
    }, # TODO: check 
    "6": {
        "name": "Haryana",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987719",
        "wd_div_id": "Q125907351",
        "wd_block_id": "Q126118370",
        "alts": [ st_haryana ],
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Panchayat Samiti",
    }, # TODO: check 
    "2": {
        "name": "Himachal Pradesh",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987720",
        "wd_div_id": "Q125907359",
        "divs_in_main_hierarchy": False,
        "alts": [ st_himachal ],
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Panchayat Samiti",
    },
    "1": {
        "name": "Jammu And Kashmir",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987721",
        "wd_div_id": "Q125907352",
        "dp_suffix": "District Planning and Development Board",
        "bp_suffix": "Block Development Council",
    }, # TODO: check 
    "20": {
        "name": "Jharkhand",
        "suffix": "Block",
        "type": "Block",
        "wd_id": "Q122987723",
        "wd_subdiv_id": "Q125919353",
        "wd_div_id": "Q125907347",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Panchayat Samiti",
    }, # TODO: check 
    "29": {
        "name": "Karnataka",
        "suffix": "Taluk",
        "type": "Tehsil",
        "wd_id": "Q122987724",
        "wd_div_id": "Q125907360",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Taluka Panchayat",
    }, # TODO: check 
    "32": {
        "name": "Kerala",
        "suffix": "Taluk",
        "type": "Tehsil",
        "wd_id": "Q7680362",
        "wd_subdiv_id": "Q125627541",
        "subdiv_label_suffix": "revenue division",
        "dp_suffix": "District Panchayat",
        "bp_suffix": "Block Panchayat",
    }, # TODO: check 
    "37": {
        "name": "Ladakh",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987726",
        "wd_div_id": "Q125907364",
        "divs_in_main_hierarchy": False,
        "dp_suffix": "District Planning and Development Board",
        "bp_suffix": "Block Development Council",
    }, # TODO: check 
    "31": { 
        "name": "Lakshadweep",
        "suffix": "Subdivision",
        "type": "Subdivision",
        "wd_id": "Q122987727",
        "dp_suffix": "Zilla Panchayat",
    },
    "23": {
        "name": "Madhya Pradesh",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987728",
        "wd_div_id": "Q124669069",
        "wd_block_id": "Q125750771",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Janpad Panchayat",
    }, # TODO: check 
    "27": {
        "name": "Maharashtra",
        "suffix": "Taluka",
        "type": "Tehsil",
        "wd_id": "Q13119795",
        "wd_div_id": "Q125907357",
        "wd_subdiv_id": "Q125918906",
        "dp_suffix": "Zilla Parishad",
        "bp_suffix": "Block Panchayat",
    }, # TODO: check 
    "14": {
        "name": "Manipur",
        "suffix": "Subdivision",
        "type": "Subdivision",
        "wd_id": "Q122987729",
        # no divisions?
        "dp_suffix": "Zilla Parishad",
    },
    "17": {
        "name": "Meghalaya",
        "suffix": "Block",
        "type": "Block",
        "wd_id": "Q122987730",
        "wd_div_id": "Q125907362",
        "divs_in_main_hierarchy": False,
    }, # C. & R. D. Block R is for Rural?
    "15": {
        "name": "Mizoram",
        "suffix": "Block",
        "type": "Block",
        "long": "Rural Development Block",
        "wd_id": "Q122987731",
    }, # Rural Development Block
    "13": {
        "name": "Nagaland",
        "suffix": "Circle",
        "type": "Tehsil",
        "wd_id": "Q122987732",
        "wd_div_id": "Q125907369",
        "divs_in_main_hierarchy": False,
    },
    "21": {
        "name": "Odisha",
        "suffix": "Police Station",
        "label_suffix": "P.S.",
        "type": "Police Station",
        "wd_id": "Q122986857",
        "wd_div_id": "Q125907355",
        "wd_block_id": "Q61863384",
        "wd_subdiv_id": "Q60843390",
        "dp_suffix": "Zilla Parishad",
        "bp_suffix": "Panchayat Samiti",
    }, # Tehsils exist, Police station maps are available in the Census Atlas
    "34": {
        "name": "Puducherry",
        "suffix": "Taluk",
        "type": "Tehsil",
        "wd_id": "Q122987733",
        "bp_suffix": "Commune Panchayat",
    },
    "3": {
        "name": "Punjab",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987734",
        "wd_div_id": "Q125907365",
        "wd_block_id": "Q123200469",
        "dp_suffix": "Zilla Parishad",
        "bp_suffix": "Panchayat Samiti",
    }, # TODO: check 
    "8": {
        "name": "Rajasthan",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987735",
        "wd_div_id": "Q125907350",
        "wd_block_id": "Q123009239",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Block Panchayat",
    }, # TODO: check 
    "11": {
        "name": "Sikkim",
        "suffix": "Subdivision",
        "type": "Subdivision",
        "wd_id": "Q122956696",
        "dp_suffix": "Zilla Panchayat",
    }, # revenue circles exist
    "33": {
        "name": "Tamil Nadu",
        "suffix": "Taluk",
        "type": "Tehsil",
        "wd_id": "Q122987736",
        "wd_block_id": "Q123009250",
        "wd_subdiv_id": "Q125626392",
        "subdiv_label_suffix": "division",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Panchayat Samiti",
    }, # TODO: check
    "36": {
        "name": "Telangana",
        "suffix": "Mandal",
        "type": "Tehsil",
        "wd_id": "Q122987738",
        "wd_block_id": "Q122987738",
        "wd_subdiv_id": "Q125626476",
        "subdiv_label_suffix": "revenue division",
        "dp_suffix": "Zilla Parishad",
        "bp_suffix": "Mandal Panchayat",
    }, # TODO: check 
    "38": {
        "name": "The Dadra And Nagar Haveli And Daman And Diu",
        "suffix": "Taluk",
        "type": "Tehsil",
        "wd_id": "Q122987739",
        "dp_suffix": "Zilla Parishad",
    }, # TODO: check 
    "16": {
        "name": "Tripura",
        "suffix": "Subdivision",
        "type": "Subdivision",
        #"long": "Development Block",
        "wd_id": "Q126201439",
        "wd_block_id": "Q122987740",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Block Panchayat",
    }, # Development Block
    "5": {
        "name": "Uttarakhand",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987741",
        "wd_subdiv_id": "Q125919325",
        "wd_div_id": "Q125907368",
        "wd_block_id": "Q123009294",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Kshetra Panchayat",
    },
    "9": {
        "name": "Uttar Pradesh",
        "suffix": "Tehsil",
        "type": "Tehsil",
        "wd_id": "Q122987742",
        "wd_div_id": "Q125907346",
        "wd_block_id": "Q123009286",
        "wd_sd_id": "Q125631953",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Kshetra Panchayat",
    },
    "19": {
        "name": "West Bengal",
        "suffix": "Block",
        "type": "Block",
        "wd_id": "Q122987743",
        "wd_div_id": "Q5284624",
        "wd_subdiv_id": "Q13058507",
        "dp_suffix": "Zilla Panchayat",
        "bp_suffix": "Panchayat Samiti",
    },
}

SUBDIST_ID = 105626471
TEHSIL_ID = 817477
TEHSIL_INDIA_ID = 7694920
CD_BLOCK_INDIA_ID = 2775236

SUBDIV_ID = 7631016
SUBDIV_REVENUE = 24943410
ALL_SUBDIV_IDS = [ SUBDIV_ID, SUBDIV_REVENUE ] +\
        [ int(v['wd_subdiv_id'][1:]) for v in state_info.values() if 'wd_subdiv_id' in v ] +\
        [ int(v['wd_id'][1:]) for v in state_info.values() if v['type'] == 'Subdivision' ]

SUBDIST_IDS = [ int(v['wd_id'][1:]) for v in state_info.values() ]

SUBTEHSIL_IDS = [ 123264644, 123264643 ]

ALL_SUBDIST_IDS = [ SUBDIST_ID, TEHSIL_ID, TEHSIL_INDIA_ID ] + SUBDIST_IDS + SUBTEHSIL_IDS

ALL_TEHSIL_IDS = [  SUBDIST_ID, TEHSIL_ID, TEHSIL_INDIA_ID ] + [ int(v['wd_id'][1:]) for v in state_info.values() if v['type'] == 'Tehsil' ] 

ALL_BLOCK_IDS = [ CD_BLOCK_INDIA_ID ] + [ int(v['wd_id'][1:]) for v in state_info.values() if v['type'] == 'Block' ] +  [ int(v['wd_block_id'][1:]) for v in state_info.values() if 'wd_block_id' in v ] 

DIST_COUNCIL_OF_INDIA_ID = 2758248
BLOCK_PANCHAYAT_ID = 4927168

VILLAGE_IN_INDIA_ID = 56436498
CENSUS_TOWN_IN_INDIA_ID = 16830604
ALL_VILLAGE_IDS = [ VILLAGE_IN_INDIA_ID, CENSUS_TOWN_IN_INDIA_ID ]

P_INSTANCE_OF = 'P31'
P_REPLACED_BY = 'P1366'
P_DISSOLVED = 'P576'
P_COUNTRY = 'P17'
P_LOCATED_IN = 'P131'
P_COORDINATE_LOCATION = 'P625'
P_COEXTENSIVE_WITH = 'P3403'
P_TERRITORY_OVERLAPS = 'P3179'
P_CONTAINS = 'P150'


P_LGD_CODE = 'P6425'
P_LGD_STATE_CODE = 'P12747'
P_LGD_DIST_CODE = 'P12746'
P_LGD_SUBDIST_CODE = 'P12748'
P_LGD_BLOCK_CODE = 'P12717'
P_LGD_VILLAGE_CODE = 'P12745'
P_CENSUS_CODE = 'P5578'
P_END_TIME = 'P582'

STATE_ID = 12443800
UT_ID = 467745 
INDIA_ID = 668
PAK_ID = 843
DIST_ID = 1149652
DIV_ID = 1230708
ALL_DIV_IDS = [ DIV_ID ] + [ int(v['wd_div_id'][1:]) for v in state_info.values() if 'wd_div_id' in v ]
PROPOSED_ENTITY = 64728694
FORMER_ENTITY = 15893266

LGD_URL="https://lgdirectory.gov.in/downloadDirectory.do?"
LGD_REF_ITEM = 'Q125923171'
P_STATED_IN = 'P248'

transilterator = None
def get_label_translit(v):
    global transilterator
    from transliterate import CachedTransliterator 
    labels = v.get('labels', {})
    if 'en' in labels:
        label = labels['en']['value']
        return label
    en_label = None
    unsup_langs = []
    all_langs = list(labels.keys())
    all_langs = sorted(all_langs)
    for k in all_langs:
        label = labels[k]['value']
        if k in ['vi', 'nl', 'ca', 'ceb', 'it', 'es', 'hif', 'ms', 'de', 'fr', 'pl', 'sv', 'da', 'cs']:
            en_label = unidecode.unidecode(label)
            continue
        if transilterator is None:
            transilterator = CachedTransliterator()
        if not transilterator.is_lang_supported(k):
            unsup_langs.append(k)
        else:
            en_label = transilterator.transliterate(k, label)
            #print(f'transilterated {label=} to {en_label=}')
            break
    if en_label is None:
        print(f'unsupported langs found: {unsup_langs}')
        return 'NA'
    return en_label


def get_label(v, lang='en'):
    labels = v.get('labels', {})
    if lang in labels:
        label = labels[lang]['value']
    else:
        #print('labels:', labels)
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

def get_census_codes(v):
    census_codes = []
    claims = v['claims'].get(P_CENSUS_CODE, None)
    if claims is None:
        return census_codes
    for c in claims:
        census_codes.append(c['mainsnak']['datavalue']['value'])
    return census_codes



def get_lgd_codes(v, code_type='localbody'):
    if code_type == 'localbody':
        LGD_CODE_PROP = P_LGD_CODE
    elif code_type == 'state':
        LGD_CODE_PROP = P_LGD_STATE_CODE
    elif code_type == 'district':
        LGD_CODE_PROP = P_LGD_DIST_CODE
    elif code_type == 'subdistrict':
        LGD_CODE_PROP = P_LGD_SUBDIST_CODE
    elif code_type == 'block':
        LGD_CODE_PROP = P_LGD_BLOCK_CODE
    elif code_type == 'village':
        LGD_CODE_PROP = P_LGD_VILLAGE_CODE
    else:
        raise Exception('unknown lgd type ' + code_type)
    lgd_codes = []
    claims = v['claims'].get(LGD_CODE_PROP, None)
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

def get_coordinates(v):
    if is_inactive(v):
        return []
    coordinates = []
    coord_claims = v['claims'].get(P_COORDINATE_LOCATION, [])

    for c in coord_claims:
        val = c['mainsnak']['datavalue']['value']
        coordinates.append([val['longitude'], val['longitude']])
    return coordinates

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

def get_contains_ids(v):
    if is_inactive(v):
        return []
    inst_claims = v['claims'].get(P_CONTAINS, [])
    ids = []
    for c in inst_claims:
        if not is_claim_current(c):
            continue
        inst_of = c['mainsnak']['datavalue']['value']['numeric-id'] 
        ids.append(inst_of)
    return ids


def get_instance_of_ids(v):
    if is_inactive(v):
        return []
    inst_claims = v['claims'].get(P_INSTANCE_OF, [])
    ids = []
    for c in inst_claims:
        if not is_claim_current(c):
            continue
        inst_of = c['mainsnak']['datavalue']['value']['numeric-id'] 
        ids.append(inst_of)
    return ids

def get_all_located_id_ranks(v):
    if is_inactive(v):
        return []
    loc_claims = v['claims'].get(P_LOCATED_IN, [])
    ranks = []
    for c in loc_claims:
        rank = c['rank']
        ranks.append(rank)
    return ranks


def get_located_in_ids(v):
    if is_inactive(v):
        return []
    loc_claims = v['claims'].get(P_LOCATED_IN, [])
    ids = []
    for c in loc_claims:
        if not is_claim_current(c):
            continue
        loc_in = c['mainsnak']['datavalue']['value']['numeric-id'] 
        ids.append(loc_in)
    return ids

def get_coextensive_ids(v):
    if is_inactive(v):
        return []
    coex_claims = v['claims'].get(P_COEXTENSIVE_WITH, [])
    ids = []
    for c in coex_claims:
        if not is_claim_current(c):
            continue
        coex_with = c['mainsnak']['datavalue']['value']['numeric-id'] 
        ids.append(coex_with)
    return ids


def get_overlap_ids(v):
    if is_inactive(v):
        return []
    overlap_claims = v['claims'].get(P_TERRITORY_OVERLAPS, [])
    ids = []
    for c in overlap_claims:
        if not is_claim_current(c):
            continue
        overlap = c['mainsnak']['datavalue']['value']['numeric-id'] 
        ids.append(overlap)
    return ids

def get_lgd_data(fname, key, filter_fn=None):
    lgd_data = {}
    with open(fname, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if filter_fn is not None and not filter_fn(r):
                continue
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
    label = item.get(get_redirect=True)['labels'].get('en', 'NA')
    data = { 'id': f'Q{wd_num_id}', 'label': label }
    page_cache[wd_num_id] = data
    with open(pcache_fname, 'a') as f:
        f.write(json.dumps({ 'id': wd_num_id, 'data': data }))
        f.write('\n')
    return page_cache[wd_num_id]



#TODO: all subclasses of division/subdivision/subdistrict/block should be picked up automatically and not from config?
#TODO: subdivisions should be moved out of the main hierarchy
#TODO: divisions should be moved out of the main hierarchy
#TODO: frontend: add corrections for other sections as well

def base_entity_checks(entity_type=None,
                       has_lgd=True, lgd_fname=None, lgd_id_key=None, lgd_name_key=None,
                       lgd_url_fn=None, lgd_correction_fn=None, lgd_filter_fn=None,
                       lgd_get_effective_date=True, lgd_code_type=None,
                       check_expected_located_in_fn=None,
                       wd_fname=None, wd_filter_fn=lambda x:True,
                       name_prefix_drops=[], name_suffix_drops=[], name_match_threshold=0.0):

    report = {
        'not_in_india': [],
        'multiple_located_in': [],
        'multiple_instance_of': [],
        'wrong_kind_of_located_in': [],
        'no_single_preferred_rank_for_located_in': [],
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
        lgd_data = get_lgd_data(lgd_fname, lgd_id_key, filter_fn=lgd_filter_fn)
    else:
        lgd_data = None

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
            lgd_codes = get_lgd_codes(v, code_type=lgd_code_type)
        else:
            lgd_codes = None
        label = get_label(v) 
        if not is_in_india(v):
            report['not_in_india'].append({'wikidata_id': k, 'wikidata_label': label})
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            print(f'multiple located_in {label}({k}): {located_in_ids}')
            report['multiple_located_in'].append({'wikidata_id': k,
                                                  'wikidata_label': label,
                                                  'located_in_entries': [ get_entry_from_wd_id(i) for i in located_in_ids ]})
        else:
            res = check_expected_located_in_fn(located_in_ids[0])
            if not res['ok']:
                report['wrong_kind_of_located_in'].append({'wikidata_id': k,
                                                           'wikidata_label': label,
                                                           'located_in': get_entry_from_wd_id(located_in_ids[0]),
                                                           'expected': res['expected']})
            all_located_in_id_ranks = get_all_located_id_ranks(v)
            num_located_in = len(all_located_in_id_ranks)
            num_preferred = len([ r for r in all_located_in_id_ranks if r == 'preferred' ])
            if num_located_in > 1:
                if num_preferred != 1:
                    report['no_single_preferred_rank_for_located_in'].append({'wikidata_id': k,
                                                                              'wikidata_label': label,
                                                                              'num_preferred': num_preferred,
                                                                              'expected_preferred': get_entry_from_wd_id(located_in_ids[0])})


        inst_of_ids = get_instance_of_ids(v)
        if len(inst_of_ids) != 1:
            print(f'multiple instance of {label}({k}): {inst_of_ids}')
            report['multiple_instance_of'].append({'wikidata_id': k,
                                                   'wikidata_label': label, 
                                                   'inst_of_entries': [ get_entry_from_wd_id(i) for i in inst_of_ids ]})

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
                    report['unknown_lgd_id'].append({'wikidata_id': k,
                                                     'wikidata_label': label,
                                                     'lgd_code': e['lgd_code']})

                
            report['multiple_lgd_ids'].append({
                'wikidata_id': k,
                'wikidata_label': label,
                'lgd_entries': lgd_entries,
            })
            continue

        lgd_code = lgd_codes[0]
        if lgd_code not in lgd_data:
            report['unknown_lgd_id'].append({'wikidata_id': k,
                                             'wikidata_label': label,
                                             'lgd_code': lgd_code})
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
                                               translit=False)
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
            if lgd_get_effective_date:
                lgd_entry_out['Effective Date'] = get_effective_date(url_info['base'], url_info['params'])
            correction_info = lgd_correction_fn(lgd_entry_out)
            #TODO: locate and add best matches?
            report['missing'].append({'lgd_entry': lgd_entry_out, 'correction_info': correction_info})
    return report


def get_wd_entity_lgd_mapping(wd_fname, wd_filter_fn, lgd_code_type):
    filtered = get_wd_data(wd_fname, wd_filter_fn)
    mapping = {}
    for k,v in filtered.items():
        lgd_codes = get_lgd_codes(v, code_type=lgd_code_type)
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
