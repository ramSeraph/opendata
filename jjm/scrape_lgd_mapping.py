import json
import csv
import io
import copy
import shutil

import urllib.parse
from multiprocessing import Pool
from pathlib import Path
import requests

from bs4 import BeautifulSoup

base_url = 'https://ejalshakti.gov.in'
list_url = f"{base_url}/JJM/JJMReports/lgd_mapping/rpt_LGDMappedStatus.aspx"


data_dir = Path('data/lgd_mapping')
data_dir.mkdir(parents=True, exist_ok=True)

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

def save_page(soup, file):
    rows = []
    table = soup.find('table')
    thead = table.find('thead')
    ths = thead.find_all('th')
    head_row = [ th.text.strip() for th in ths ]
    rows.append(head_row)
    trs = table.find_all('tr', recursive=False)
    for tr in trs:
        tds = tr.find_all('td')
        row = [ td.text.strip() for td in tds ]
        rows.append(row)
    with open(file, 'w') as f:
        wr = csv.writer(f)
        for row in rows:
            wr.writerow(row)


def get_base_form_data(soup):
    hidden_inputs = soup.find_all('input', { 'type': 'hidden' })
    base_form_data = {}
    for inp in hidden_inputs:
        ident = inp.attrs['id']
        val = inp.attrs.get('value', '')
        base_form_data[ident] = val
    return base_form_data

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

def get_final_list(session, mapping_url, html, folder):

    soup = BeautifulSoup(html, 'html.parser')
    select =  soup.find('select', { 'id': 'CPHPage_ddPageNo' })
    options = select.find_all('option')
    num_pages = len(options) - 1
    print(f'handling pages - 1/{num_pages}')
    first_page = folder / '1.csv'
    if not first_page.exists():
        save_page(soup, first_page)
    base_form_data = get_base_form_data(soup)

    for i in range(0, num_pages):
        if i == 0:
            continue
        pno = i + 1
        print(f'handling pages - {pno}/{num_pages}')
        page_file = folder / f'{pno}.csv'
        if page_file.exists():
            continue
        page_var = 'ctl00$CPHPage$ddPageNo'
        form_data = {}
        form_data.update(base_form_data)
        form_data.update({
            "ctl00$ScriptManager1": 'ctl00$upPnl|' + page_var,
            "__EVENTTARGET": page_var,
            "__EVENTARGUMENT": '',
            "__LASTFOCUS": '',
            "ctl00$CPHPage$ddPageNo": str(pno),
            "__ASYNCPOST": "true"
        })
        headers = {}
        headers.update(base_headers)
        headers['Referer'] = mapping_url
        resp = session.post(mapping_url, data=form_data, headers=headers)
        if not resp.ok:
            print(resp.status_code)
            print(resp.text)
            raise Exception(f'getting data list for {key}, {pno} failed')

        # hack to overcome resp.text read truncation
        temp_file = folder / f'{pno}.temp.txt'
        temp_file.write_text(resp.text)
        resp_text = temp_file.read_text()
        temp_file.unlink()

        html, _ = get_data_from_post(resp_text)
        soup = BeautifulSoup(html, 'html.parser')
        save_page(soup, page_file)


def get_mapping_data(count, var, folder):
    print('getting main page')
    session = requests.session()
    resp = session.get(list_url)
    if not resp.ok:
        raise Exception(f'failed to get data from {list_url}')
    
    soup = BeautifulSoup(resp.text, 'html.parser')

    form_data = get_base_form_data(soup)

    print('post to prime for changing page')
    form_data.update({
        "ctl00$ScriptManager1": 'ctl00$upPnl|' + var,
        "__EVENTTARGET": var,
        "__EVENTARGUMENT": '',
        "__LASTFOCUS": '',
        "__ASYNCPOST": "true"
    })
    headers = {}
    headers.update(base_headers)
    headers['Referer'] = list_url
    resp = session.post(list_url, data=form_data, headers=headers)
    if not resp.ok:
        print(resp.status_code)
        print(resp.text)
        raise Exception('post to prime for changing page failed')
    parts = resp.text.split('|')
    redir_url = parts[7]
    redir_url = urllib.parse.unquote(redir_url)
    # need to do it twice to convert missed ='s 
    #redir_url = urllib.parse.unquote(redir_url)
    #print(redir_url)
    headers = {}
    headers.update(base_headers)
    headers['Referer'] = list_url
    del headers['Content-Type']
    mapping_url = base_url + redir_url
    resp = session.get(mapping_url)
    if not resp.ok:
        print(resp.status_code)
        print(resp.text)
        raise Exception(f'getting main data list for {key} failed')
    get_final_list(session, mapping_url, resp.text, folder)


def parse_main_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', { 'id': 'tableReportTable' })
    rows = table.find_all('tr', recursive=False)
    summary = []
    for row in rows:
        cells = list(row.find_all('td'))
        if len(cells) == 0:
            continue
        data = {}
        data['Sno'] = cells[0].text.strip()
        data['EntityName'] = cells[1].text.strip()
        var = cells[1].find('a').attrs['href'].split("'")[1]
        data['EntityName_var'] = var


        data['blocks_count'] = int(cells[2].text)

        count = int(cells[3].text)
        data['mapped_blocks_count'] = count
        if count > 0:
            var = cells[3].find('a').attrs['href'].split("'")[1]
            data['mapped_blocks_var'] = var

        count = int(cells[4].text)
        data['unmapped_blocks_count'] = count
        if count > 0:
            var = cells[4].find('a').attrs['href'].split("'")[1]
            data['unmapped_blocks_var'] = var


        data['gps_count'] = int(cells[5].text)

        count = int(cells[6].text)
        data['mapped_gps_count'] = count
        if count > 0:
            var = cells[6].find('a').attrs['href'].split("'")[1]
            data['mapped_gps_var'] = var

        count = int(cells[7].text)
        data['unmapped_gps_count'] = count
        if count > 0:
            var = cells[7].find('a').attrs['href'].split("'")[1]
            data['unmapped_gps_var'] = var


        data['vills_count'] = int(cells[8].text)

        count = int(cells[9].text)
        data['mapped_vills_count'] = count
        if count > 0:
            var = cells[9].find('a').attrs['href'].split("'")[1]
            data['mapped_vills_var'] = var

        count = int(cells[10].text)
        data['unmapped_vills_count'] = count
        if count > 0:
            var = cells[10].find('a').attrs['href'].split("'")[1]
            data['unmapped_vills_var'] = var


        count = int(cells[11].text)
        data['urbanised_to_be_deleted_vills_count'] = count
        if count > 0:
            var = cells[10].find('a').attrs['href'].split("'")[1]
            data['urbanised_to_be_deleted_vills_var'] = var

        count = int(cells[12].text)
        data['wrong_entry_to_be_deleted_vills_count'] = count
        if count > 0:
            var = cells[10].find('a').attrs['href'].split("'")[1]
            data['wrong_entry_to_be_deleted_vills_var'] = var

        count = int(cells[13].text)
        data['urbanized_not_to_be_deleted_vills_count'] = count
        if count > 0:
            var = cells[10].find('a').attrs['href'].split("'")[1]
            data['urbanized_not_to_be_deleted_vills_var'] = var

        summary.append(data)
    return summary


def get_data():
    print('getting main page')
    session = requests.session()
    resp = session.get(list_url)
    if not resp.ok:
        raise Exception(f'failed to get data from {list_url}')
    return parse_main_table(resp.text)

def get_block_info(state_name, state_name_var, dist_name, dist_name_var, dist_folder):
    pass

def get_dist_info(state_name, state_name_var, key_folder):
    print('getting dist_info')
    dist_info_file = key_folder.parent / 'dist_info.json'
    if dist_info_file.exists():
        dist_info = json.loads(dist_info_file.read_text())
        return dist_info

    print('getting main page')
    session = requests.session()
    resp = session.get(list_url)
    if not resp.ok:
        raise Exception(f'failed to get data from {list_url}')
     
    soup = BeautifulSoup(resp.text, 'html.parser')

    form_data = get_base_form_data(soup)

    print('post to prime for changing to dist page')
    form_data.update({
        "ctl00$ScriptManager1": 'ctl00$upPnl|' + state_name_var,
        "__EVENTTARGET": state_name_var,
        "__EVENTARGUMENT": '',
        "__LASTFOCUS": '',
        "__ASYNCPOST": "true"
    })
    headers = {}
    headers.update(base_headers)
    headers['Referer'] = list_url
    resp = session.post(list_url, data=form_data, headers=headers)
    if not resp.ok:
        print(resp.status_code)
        print(resp.text)
        raise Exception('post to prime for changing to dist page failed')
    parts = resp.text.split('|')
    redir_url = parts[7]
    redir_url = urllib.parse.unquote(redir_url)

    headers = {}
    headers.update(base_headers)
    headers['Referer'] = list_url
    del headers['Content-Type']
    dist_url = base_url + redir_url
    resp = session.get(dist_url)
    if not resp.ok:
        print(resp.status_code)
        print(resp.text)
        raise Exception(f'getting data list for {state_name} failed')

    dist_info = parse_main_table(resp.text)
    dist_info_file.write_text(json.dumps(dist_info, indent=2))
    return dist_info

def get_dist_mappping_data(state_name_var, dist_var, dist_dir):

    print('getting main page')
    session = requests.session()
    resp = session.get(list_url)
    if not resp.ok:
        raise Exception(f'failed to get data from {list_url}')
     
    soup = BeautifulSoup(resp.text, 'html.parser')

    form_data = get_base_form_data(soup)

    print('post to prime for changing to dist page')
    form_data.update({
        "ctl00$ScriptManager1": 'ctl00$upPnl|' + state_name_var,
        "__EVENTTARGET": state_name_var,
        "__EVENTARGUMENT": '',
        "__LASTFOCUS": '',
        "__ASYNCPOST": "true"
    })
    headers = {}
    headers.update(base_headers)
    headers['Referer'] = list_url
    resp = session.post(list_url, data=form_data, headers=headers)
    if not resp.ok:
        print(resp.status_code)
        print(resp.text)
        raise Exception('post to prime for changing to dist page failed')
    parts = resp.text.split('|')
    redir_url = parts[7]
    redir_url = urllib.parse.unquote(redir_url)
    headers = {}
    headers.update(base_headers)
    headers['Referer'] = list_url
    del headers['Content-Type']
    dist_url = base_url + redir_url
    resp = session.get(dist_url)
    if not resp.ok:
        print(resp.status_code)
        print(resp.text)
        raise Exception(f'getting district list for {state_name} failed')

    soup = BeautifulSoup(resp.text, 'html.parser')
    form_data = get_base_form_data(soup)
    form_data.update({
        "ctl00$ScriptManager1": 'ctl00$upPnl|' + dist_var,
        "__EVENTTARGET": dist_var,
        "__EVENTARGUMENT": '',
        "__LASTFOCUS": '',
        "__ASYNCPOST": "true"
    })
    headers = {}
    headers.update(base_headers)
    headers['Referer'] = dist_url
    resp = session.post(dist_url, data=form_data, headers=headers)
    if not resp.ok:
        print(resp.status_code)
        print(resp.text)
        raise Exception('post to prime for changing to final list failed')
    parts = resp.text.split('|')
    redir_url = parts[7]
    redir_url = urllib.parse.unquote(redir_url)
    headers = {}
    headers.update(base_headers)
    headers['Referer'] = dist_url
    del headers['Content-Type']
    key_dist_url = base_url + redir_url
    resp = session.get(key_dist_url)
    if not resp.ok:
        print(resp.status_code)
        print(resp.text)
        raise Exception(f'getting final list failed')
    get_final_list(session, key_dist_url, resp.text, dist_dir)


def get_mapping_data_by_district(state_name, state_name_var, key_folder, key):
    dist_info = get_dist_info(state_name, state_name_var, key_folder)
    for entry in dist_info:
        dist_name = entry["EntityName"]
        dist_count = int(entry[f'{key}_count'])
        if dist_count == 0:
            continue
        #TODO: this fails.. and is not retrievable.. its just 60 villages.. just skip for now
        if state_name == 'Manipur' and dist_name == 'Thoubal' and key == 'mapped_vills':
            continue
        dist_var = entry[f'{key}_var']
        print(f'handling {state_name=}, {dist_name=}')
        dist_dir = key_folder / f'{dist_name}'
        dist_dir_wip = key_folder / f'{dist_name}.wip'
        if dist_dir.exists():
            continue
        dist_dir_wip.mkdir(exist_ok=True, parents=True)
        get_dist_mappping_data(state_name_var, dist_var, dist_dir_wip)
        shutil.move(dist_dir_wip, dist_dir)

if __name__ == '__main__':

    print('getting data skeleton')
    state_map_file = data_dir / 'state_map.json'
    if state_map_file.exists():
        with open(state_map_file) as f:
            state_map = json.load(f)
    else:
        state_map = get_data()
        with open(state_map_file, 'w') as f:
            json.dump(state_map, f, indent=4)

    for entry in state_map:
        state_name = entry["EntityName"]
        state_name_var = entry["EntityName_var"]
        print(f'handling {state_name=}')
        state_dir = data_dir / f'{state_name}'
        state_dir_wip = data_dir / f'{state_name}.wip'
        if state_dir.exists():
            continue
        state_dir_wip.mkdir(exist_ok=True, parents=True)
        
        for key in [ 'mapped_blocks', 'unmapped_blocks',
                     'mapped_gps',    'unmapped_gps',
                     'mapped_vills',  'unmapped_vills',
                     'urbanised_to_be_deleted_vills',
                     'wrong_entry_to_be_deleted_vills',
                     'urbanized_not_to_be_deleted_vills']:
            print(f'handling {key=}')
            count = entry[f'{key}_count']
            if count <= 0:
                continue
            key_folder = state_dir_wip / f'{key}' 
            key_folder_wip = state_dir_wip / f'{key}.wip'
            if key_folder.exists():
                continue
            key_folder_wip.mkdir(exist_ok=True, parents=True)
            var = entry[f'{key}_var']
            error_file = key_folder_wip.joinpath('error.txt')
            if error_file.exists():
                print(f'{error_file} exists.. trying to go by district')
                get_mapping_data_by_district(state_name, state_name_var, key_folder_wip, key)
                error_file.unlink()
                shutil.move(key_folder_wip, key_folder)
                continue
            try:
                get_mapping_data(count, var, key_folder_wip)
            except Exception:
                error_file.write_text("")
            if not error_file.exists():
                shutil.move(key_folder_wip, key_folder)

        error_files = list(state_dir_wip.glob('*/error.txt'))
        if len(error_files) == 0:
            shutil.move(state_dir_wip, state_dir)
