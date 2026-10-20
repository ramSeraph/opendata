import copy
import csv
import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests
import unidecode
from bs4 import BeautifulSoup
from constants import (
    INDIA_ID,
    P_CENSUS_CODE,
    P_COEXTENSIVE_WITH,
    P_CONTAINS,
    P_COORDINATE_LOCATION,
    P_COUNTRY,
    P_DISSOLVED,
    P_END_TIME,
    P_INSTANCE_OF,
    P_LGD_BLOCK_CODE,
    P_LGD_DIST_CODE,
    P_LGD_LOCAL_BODY_CODE,
    P_LGD_STATE_CODE,
    P_LGD_SUBDIST_CODE,
    P_LGD_VILLAGE_CODE,
    P_LOCATED_IN,
    P_REPLACED_BY,
    P_TERRITORY_OVERLAPS,
    PROPOSED_ENTITY,
)
from lev import masala_levenshtein
from raw_wikidata import client
from requests.models import PreparedRequest

transliterator = None
def get_label_translit(v):
    global transliterator
    label = get_label(v)
    if label != 'NA':
        return label
    from transliterate import CachedTransliterator
    labels = v.get('labels', {})
    en_label = None
    unsup_langs = []
    all_langs = list(labels.keys())
    all_langs = sorted(all_langs)
    for k in all_langs:
        label = labels[k]['value']
        if k in ['vi', 'nl', 'ca', 'ceb', 'it', 'es', 'hif', 'ms', 'de', 'fr', 'pl', 'sv', 'da', 'cs']:
            en_label = unidecode.unidecode(label)
            continue
        if transliterator is None:
            transliterator = CachedTransliterator()
        if not transliterator.is_lang_supported(k):
            unsup_langs.append(k)
        else:
            en_label = transliterator.transliterate(k, label)
            break
    if en_label is None:
        print(f'unsupported langs found: {unsup_langs}')
        return 'NA'
    return en_label


def get_label(v, lang='en'):
    labels = v.get('labels', {})
    if lang in labels:
        label = labels[lang]['value']
    elif 'mul' in labels:
        label = labels['mul']['value']
    else:
        label = 'NA'
    return label


def get_claim_values(v, prop, *, current_only=False):
    """Read concrete values, ignoring Wikidata's unknown/no-value snaks."""
    values = []
    for claim in v.get('claims', {}).get(prop, []):
        if current_only and not is_claim_current(claim):
            continue
        datavalue = claim.get('mainsnak', {}).get('datavalue')
        if datavalue is not None:
            values.append(datavalue['value'])
    return values


def get_census_code(v):
    codes = get_census_codes(v)
    return codes[-1] if codes else 'NA'


def get_census_codes(v):
    return get_claim_values(v, P_CENSUS_CODE)


LGD_CODE_PROPERTIES = {
    'localbody': P_LGD_LOCAL_BODY_CODE,
    'state': P_LGD_STATE_CODE,
    'district': P_LGD_DIST_CODE,
    'subdistrict': P_LGD_SUBDIST_CODE,
    'block': P_LGD_BLOCK_CODE,
    'village': P_LGD_VILLAGE_CODE,
}


def get_lgd_codes(v, code_type='localbody'):
    try:
        prop = LGD_CODE_PROPERTIES[code_type]
    except KeyError:
        raise ValueError(f'unknown LGD type {code_type!r}') from None
    return get_claim_values(v, prop)
 

def is_claim_current(c):
    return 'qualifiers' not in c or \
            P_END_TIME not in c['qualifiers'] or \
            len(c['qualifiers'][P_END_TIME]) == 0 or \
            'datavalue' not in c['qualifiers'][P_END_TIME][0]


def is_inactive(v):
    claims = v.get('claims', {})
    return P_REPLACED_BY in claims or P_DISSOLVED in claims


def is_current_instance_of(v, inst_types):
    if is_inactive(v):
        return False
    if any(value['numeric-id'] == PROPOSED_ENTITY for value in get_claim_values(v, P_INSTANCE_OF)):
        return False
    return any(number in inst_types for number in get_instance_of_ids(v))


def get_aliases(v):
    en_aliases = [ e['value'] for e in v.get('aliases', {}).get('en', []) if e['language'] == 'en' ]
    return en_aliases

def get_coordinates(v):
    if is_inactive(v):
        return []
    return [[value['longitude'], value['latitude']]
            for value in get_claim_values(v, P_COORDINATE_LOCATION)]

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


def get_best_match(name, v, prefix_drops=(), suffix_drops=(), translit=False):
    if translit:
        label = get_label_translit(v)
    else:
        label = get_label(v)
    aliases = get_aliases(v)
    label_dist = get_distance(name, label, prefix_drops, suffix_drops)
    out_dist = label_dist
    out = label
    for alias in aliases:
        alias_dist = get_distance(name, alias, prefix_drops, suffix_drops)
        if alias_dist < out_dist:
            out = alias
            out_dist = alias_dist
    return out, out_dist


def is_in_india(v):
    return any(value['numeric-id'] == INDIA_ID for value in get_claim_values(v, P_COUNTRY))


def get_current_item_ids(v, prop):
    if is_inactive(v):
        return []
    return [value['numeric-id'] for value in get_claim_values(v, prop, current_only=True)]


def get_contains_ids(v):
    return get_current_item_ids(v, P_CONTAINS)


def get_instance_of_ids(v):
    return get_current_item_ids(v, P_INSTANCE_OF)

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
    return get_current_item_ids(v, P_LOCATED_IN)

def get_coextensive_ids(v):
    return get_current_item_ids(v, P_COEXTENSIVE_WITH)


def get_overlap_ids(v):
    return get_current_item_ids(v, P_TERRITORY_OVERLAPS)

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

def get_entry_from_wd_id(wd_num_id):
    global page_cache

    wd_num_id = int(wd_num_id)
    pcache_fname = 'data/cache.jsonl'
    if page_cache is None:
        page_cache = {}
        if Path(pcache_fname).exists():
            with open(pcache_fname, 'r') as f:
                for line in f:
                    e = json.loads(line)
                    # Older cache entries did not consider multilingual labels.
                    if e['data']['label'] != 'NA':
                        page_cache[int(e['id'])] = e['data']

        # These entities already came from wbgetentities. Reading their labels
        # locally avoids one API request per referenced district/subdistrict.
        for path in Path('data').glob('*.jsonl'):
            if path.name == 'cache.jsonl':
                continue
            with path.open() as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    qid = row['id']
                    label = get_label(row['data'])
                    page_cache[int(qid[1:])] = {'id': qid, 'label': label}

    if wd_num_id in page_cache:
        return page_cache[wd_num_id]

    qid = f'Q{wd_num_id}'
    item = client.entities([qid], props='labels', languages='en|mul')[qid]
    label = get_label(item)
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
                       name_prefix_drops=(), name_suffix_drops=(), name_match_threshold=0.0,
                       multiple_instance_of_exceptions=None):

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
        allowed_inst_of_ids = (multiple_instance_of_exceptions or {}).get(k)
        if len(inst_of_ids) != 1 and set(inst_of_ids) != allowed_inst_of_ids:
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
        for lgd_id in sorted(missing_in_wikidata):
            lgd_entry = lgd_data[lgd_id]
            lgd_entry_out = create_ext_lgd_entry(lgd_entry)
            url_info = lgd_url_fn(lgd_id)
            req = PreparedRequest()
            req.prepare_url(url_info['base'], url_info['params'])
            lgd_entry_out['lgd_url'] = req.url
            if lgd_get_effective_date:
                try:
                    lgd_entry_out['Effective Date'] = get_effective_date(url_info['base'], url_info['params'])
                except (requests.RequestException, ValueError) as error:
                    # The date enriches a missing-entity report; losing this
                    # lookup must not discard the entity or the other checks.
                    lgd_entry_out.pop('Effective Date', None)
                    lgd_entry_out['Effective Date Error'] = str(error)
                    print(f'Warning: effective date unavailable for {req.url}: {error}', flush=True)
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


def invert_lgd_mapping(mapping):
    """Only resolve an LGD code when exactly one Wikidata item owns it."""
    counts = Counter(mapping.values())
    return {code: qid for qid, code in mapping.items() if code != 'NA' and counts[code] == 1}


def correction_inception(lgd_entry):
    date = lgd_entry.get('Effective Date')
    if not date:
        return None
    return datetime.strptime(date, '%d%b%Y').strftime('+%Y-%m-%dT00:00:00Z/11')



def write_report(report, fname):
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True, parents=True)
    report_file = reports_dir / fname
    report_file.write_text(json.dumps(report, indent=2))


def get_effective_date(url, params):
    print(url, params, flush=True)
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=(10, 60))
            resp.raise_for_status()
            break
        except requests.RequestException as error:
            response = error.response
            retryable = isinstance(error, (requests.ConnectionError, requests.Timeout)) or (
                response is not None and response.status_code in (408, 500, 502, 503, 504)
            )
            if not retryable or attempt == 2:
                raise
            delay = 2 ** (attempt + 1)
            print(f'LGD effective date lookup failed: {error}; retrying in {delay}s', flush=True)
            time.sleep(delay)

    soup = BeautifulSoup(resp.text, 'html.parser')
    trs = soup.find_all('tr')
    for tr in trs:
        tds = tr.find_all('td', recursive=False)
        if tds and tds[0].get_text(' ', strip=True).rstrip(':').strip() == 'Effective Date':
            if len(tds) < 2:
                break
            date_str = tds[1].get_text(strip=True)
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').strftime('%d%b%Y')
            except ValueError as error:
                raise ValueError('LGD Effective Date is empty or invalid') from error
    raise ValueError('LGD page has no Effective Date')
