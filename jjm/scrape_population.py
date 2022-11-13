import json
import csv
import io
import re
import copy
import shutil

from multiprocessing import Pool
from pathlib import Path
import requests

from Levenshtein import distance
from bs4 import BeautifulSoup
    
s_url = 'https://ejalshakti.gov.in/IMISReports/Reports/BasicInformation/rpt_RWS_RuralPopulation_S.aspx?Rep=0&RP=Y'
h_url = 'https://ejalshakti.gov.in/IMISReports/Reports/BasicInformation/rpt_RWS_RuralPopulation_H.aspx?Rep=0'

special_cases = {
    '0000028246': {'pop_sc': '28', 'pop_st': '6', 'pop_gen': '61', 'num_hh': 'NA'},
    '0001495683': {'pop_sc': '0', 'pop_st': '327', 'pop_gen': '135', 'num_hh': 'NA'},
    '0001561402': {'pop_sc': '14', 'pop_st': '0', 'pop_gen': '110', 'num_hh': 'NA'},
    '0000431435': None,
    '0001521172': None,
    '0001522969': None,
    '0001522617': None,
    '0001522665': None,
    '0001523653': None,
    '0001521382': None,
    '0001518463': None,
    '0001517221': None,
    '0001516923': None,
    '0001518000': None,
    '0001518237': None,
    '0001518453': None,
    '0001516928': None,
    '0001516710': None,
    '0001516976': None,
    '0001515542': None,
    '0001515551': None,
    '0001515564': None,
    '0001516713': None,
    '0001516933': None,
    '0001516575': None,
    '0001516971': None,
    '0001516981': None,
    '0001516672': None,
    '0001517047': None,
    '0001516881': None,
    '0001518668': None,
    '0001518707': None,
    '0001516618': None,
    '0001515784': None,
    '0001515929': None,
    '0001515927': None,
    '0001516875': None,
    '0001517682': None,
    '0001516999': None,
    '0001517009': None,
    '0001517184': None,
    '0001517194': None,
    '0001518584': None,
    '0001516835': None,
    '0001517423': None,
    '0001517371': None,
    '0001517413': None,
    '0001517248': None,
    '0001515792': None,
    '0001515980': None,
    '0001516610': None,
    '0001516597': None,
    '0001556080': None,
    '0001561376': None,
    '0001559249': None,
    '0001557667': None,
    '0001556915': None,
    '0001560976': None,
    '0001558234': None,
    '0001556923': None,
    '0001560234': None,
    '0001556503': None,
    '0001553888': None,
    '0001556463': None,
    '0001557118': None,
    '0001554338': None,
}

corrections = {
    "district": {
        "DIMA HASAO": "NORTH CHACHAR HILLS"
    }
}


base_headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'https://ejalshakti.gov.in',
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36',
    'X-MicrosoftAjax': 'Delta=true',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="101", "Google Chrome";v="101"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
}

data_dir = Path('data')

def get_best_match(hay, needle, ret_idx=False):
    scores = [ distance(h, needle) for h in hay ]
    min_score = min(scores)
    min_idx = scores.index(min_score)
    ret = hay[min_idx]
    if ret_idx:
        ret = min_idx
    return ret, min_score

    

def gen_canon(name, kind=None):
    out = name.strip().upper().replace('\xa0', ' ')
    out = ' '.join(out.split())
    #out = out.replace(' ', '')
    if kind is not None:
        if kind in corrections:
            kind_corrections = corrections[kind]
            if out in kind_corrections:
                out = kind_corrections[out]
    return out

def get_data_from_post(resp_text):

    panel_label = '|updatePanel|upPnl|'
    idx = resp_text.find(panel_label)
    str_len = int(resp_text[:idx].split('|')[-1])
    count = 0
    idx = idx + len(panel_label)
    start_idx = idx
    while count < str_len:
        if resp_text[idx] == '\n':
            count += 2
        else:
            count += 1
        idx += 1
    end_idx = idx
    html = resp_text[start_idx:end_idx]

    pieces = resp_text[end_idx+1:].split('|')
    idx = 0
    base_form_data = {}
    while idx < len(pieces):
        if pieces[idx] != 'hiddenField':
            idx += 1
            continue
        idx += 1
        key = pieces[idx] 
        idx += 1
        val = pieces[idx]
        #print(key)
        base_form_data[key] = val
        idx += 1
    return html, base_form_data


def get_base_form_data(soup):
    hidden_inputs = soup.find_all('input', { 'type': 'hidden' })
    base_form_data = {}
    for inp in hidden_inputs:
        ident = inp.attrs['id']
        val = inp.attrs.get('value', '')
        base_form_data[ident] = val
    return base_form_data

def parse_and_call(session, base_form_data, soup, hab_info):
    form_data = {}
    form_data.update(base_form_data)

    #print(hab_info)
    table = soup.find('table', { 'class': 'SelectData' }) 
    tds = table.find_all('td')
    hab_keys_seen = []
    ctl_map = {}
    for td in tds:
        select = td.find('select')
        if select is None:
            continue
        select_type = str(select.attrs['id']).replace('ContentPlaceHolder_dd', '').lower()
        fkey = select.attrs['name']
        #print(fkey)

        ctl_map[select_type] = fkey
        options = select.find_all('option')
        selected = None
        opt_map = {}
        for option in options:
            key = gen_canon(option.text)
            val = option.attrs['value']
            selected_attr = option.attrs.get('selected', None)
            if selected_attr is not None:
                selected = key
            opt_map[key] = val

        if selected is None:
            selected = list(opt_map.items())[0][0]


        #print(opt_map)
        #print(selected)
        hab_val = gen_canon(hab_info[select_type], kind=select_type)

        if len(opt_map) == 1 and opt_map[selected] == '-1':
            form_data[fkey] = opt_map[selected]
        else:
            matched, score = get_best_match(list(opt_map.keys()), hab_val)
            if score > 2:
                print(f'WARNING: ambiguous match {select_type=} - {matched=}, {hab_val=}, {score=}')
            form_data[fkey] = opt_map[matched]
            hab_keys_seen.append(select_type)

    ctl = None
    for hab_key in hab_info.keys():
        key_ctl = ctl_map[hab_key]
        if hab_key not in hab_keys_seen:
            #print(hab_key)
            break
        ctl = key_ctl

    final = False
    if len(hab_keys_seen) == len(hab_info.keys()):
        final = True

    headers = {}
    headers.update(base_headers)
    headers['referer'] = s_url


    if not final:
        form_data.update({
            'ctl00$ScriptManager1': 'ctl00$upPnl|' + ctl,
            'ctl00$ddLanguage': '',
            '__EVENTTARGET': ctl,
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__ASYNCPOST': 'true'
        })
    else:
        form_data.update({
            'ctl00$ScriptManager1': 'ctl00$upPnl|ctl00$ContentPlaceHolder$btnGO',
            'ctl00$ddLanguage': '',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__ASYNCPOST': 'true',
            '__LASTFOCUS': '',
            'ctl00$ContentPlaceHolder$btnGO': 'Show'
        })

    #print(form_data)
    resp = session.post(s_url, data = form_data, headers=headers)
    if not resp.ok:
        raise Exception('priming call failed')

    # hack to overcome resp.text read truncation
    temp_file = data_dir / 'temp.txt'
    temp_file.write_text(resp.text)
    resp_text = temp_file.read_text()
    temp_file.unlink()
    if not final:
        html, h_form_data = get_data_from_post(resp_text)
        h_soup = BeautifulSoup(html, 'html.parser')
    else:
        resp = session.get(h_url)
        if not resp.ok:
            raise Exception('unable to get final hab page')
        h_soup = BeautifulSoup(resp.text, 'html.parser')
        h_form_data = None
    return h_form_data, h_soup, final



def parse_hab_table(soup):
    data = []
    table = soup.find('table', {'id': 'tableReportTable'})
    trs = table.find_all('tr', recursive=False)
    for tr in trs:
        tds = tr.find_all('td')
        vals = [ gen_canon(td.text) for td in tds ]
        if len(vals) == 0:
            continue
        for i in range(2, len(vals)):
            vals[i] = vals[i].replace(',', '')
        data.append({'name': vals[1], 'pop_sc': vals[2], 'pop_st': vals[3], 'pop_gen': vals[4], 'num_hh': 'NA'})
    return data


def get_pop_info(hab_info):
    session = requests.session()
    resp = session.get(s_url)
    if not resp.ok:
        raise Exception('unable to get main page')
    soup = BeautifulSoup(resp.text, 'html.parser')
    base_form_data = get_base_form_data(soup)
    while True:
        base_form_data, soup, final = parse_and_call(session, base_form_data, soup, hab_info)
        if final:
            hab_data = parse_hab_table(soup)
            return hab_data

out_fields = ['id', 'pop_sc', 'pop_st', 'pop_gen', 'num_hh'] 

if __name__ == '__main__':
    pop_done = set()
    pop_file = Path('data/hab_pop_hh.csv')
    print('processing hab_pop_hh file')
    if pop_file.exists():
        with open(pop_file, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                pop_done.add(r['id'])
    else:
        with open(pop_file, 'w') as f:
            wr = csv.DictWriter(f, fieldnames=out_fields)
            wr.writeheader()

    
    no_data_ids = set()
    print('processing hab_info file')
    with open(pop_file, 'a') as f:
        wr = csv.DictWriter(f, fieldnames=out_fields)
        with open('data/hab_info.jsonl', 'r') as f:
            for line in f:
                d = json.loads(line)
                hab_id = d['hab_id']
                if hab_id not in pop_done:
                    if 'error' in d:
                        no_data_ids.add(hab_id)
                        continue
                    abstract_data = d['Abstract Data']
                    num_hh = abstract_data["No. of Housesholds (As on 01/04/2022)"]
                    pop_data = abstract_data["Total Population (As on 01/04/2022)"]
                    row = {
                        'id': hab_id,
                        'pop_sc': pop_data['SC -'],
                        'pop_st': pop_data['ST -'],
                        'pop_gen': pop_data['GEN -'],
                        'num_hh': num_hh
                    }
                    wr.writerow(row)

    hab_ids_to_scrape = no_data_ids - pop_done
    total = len(hab_ids_to_scrape)
    print(f'{total=}')

    hab_infos = []
    with open('data/habitations.csv', 'r')  as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r['id'] in hab_ids_to_scrape:
                hab_info = {
                    'finyear': 'AsOn (01/04/22)',
                    'state': r['state'],
                    'district': r['district'],
                    'block': r['block'],
                    'panchayat': r['gp'],
                    'village': r['village'],
                    'name': r['name'],
                    'id': r['id']
                }
                hab_infos.append(hab_info)

    def hab_canon(name):
        out = name
        m = re.match(r'^(.*)(\([0-9]{16}\))$', out)
        if m is not None:
            out = m.group(1)
        out = gen_canon(out)
        return out


    with open(pop_file, 'a') as f:
        count = 0
        wr = csv.DictWriter(f, fieldnames=out_fields)
        for hab_info in hab_infos:
            hab_id = hab_info.pop('id')
            if hab_id in special_cases:
                data = special_cases[hab_id]
                if data is None:
                    continue

            hab_name = hab_info.pop('name')
            hab_name = hab_canon(hab_name)

            count += 1
            print(f'getting pop info for {hab_id=} {count}/{total} - {hab_name=}')
            vill_data = get_pop_info(hab_info)
            for h in vill_data:
                h['name'] = hab_canon(h['name'])

            print(f'{vill_data=}')
            hnames = [ h['name'] for h in vill_data ]
            match_idx, score = get_best_match(hnames, hab_name, ret_idx=True)
            h = vill_data[match_idx]
            if score > 2:
                print(f'WARNING: ambiguous match - {hab_name=}, {h["name"]=}, {score=}')
            print(f'matched {h=}')
            h.pop('name')
            h['id'] = hab_id
            wr.writerow(h)
    



