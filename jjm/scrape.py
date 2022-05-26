import json
import io
import copy
import shutil

from multiprocessing import Pool
from pathlib import Path
import requests

from bs4 import BeautifulSoup


dist_url = 'https://ejalshakti.gov.in/imisreports/Reports/Physical/rpt_RWS_FHTCCoverage_D.aspx?Rep=0'
list_url = 'https://ejalshakti.gov.in/imisreports/Reports/Physical/rpt_RWS_FHTCCoverage_List.aspx?Rep=0'

data_dir = Path('data/habitations')
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

def copy_full(resp_text):
    op = io.StringIO()
    op.write(resp_text)
    return op.getvalue()

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

def extract_habitation_list(soup):
    table = soup.find('table', {'id': 'tableReportTable'})
    trs = table.find_all('tr', recursive=False)
    hab_list = []
    for tr in trs:
        tds = tr.find_all('td', recursive=False)
        #print(tds)
        block_name = tds[3].text.strip()
        gp_name = tds[4].text.strip()
        village = tds[5].text.strip()
        hb_id = tds[7].text.strip()
        link = tds[6].find('a')
        hb_name = link.text.strip()
        url = link.attrs['href']
        url_id = '='.join(url.split('&')[-1].split('=')[1:])
        hab_list.append({'name': hb_name, 'village': village, 'gp': gp_name, 'id': hb_id, 'url_id': url_id, 'block': block_name})
    return hab_list



def get_data(inp=None):
    print('getting main page')
    session = requests.session()
    resp = session.get(dist_url)
    if not resp.ok:
        raise Exception(f'failed to get data from {dist_url}')
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    base_form_data = get_base_form_data(soup)
    table = soup.find('table', {'class': 'SelectData'})
    try:
        state_select = table.find('select', {'id': 'ContentPlaceHolder_ddState'})
    except Exception as ex:
        print(soup)
        raise ex
    state_options = state_select.find_all('option')
    state_map = {}
    for s_option in state_options:
        val = s_option.attrs['value']
        if val == '-1':
            continue
        name = s_option.text
        name = name.replace('\xa0', ' ')
        if inp is not None and inp[0] != name:
            continue
        state_dir = data_dir / f'{name}'
        if state_dir.exists():
            return
        state_dir_wip = data_dir / f'{name}.wip'
        state_dir_wip.mkdir(parents=True, exist_ok=True)
        print(f'handling state: {name}')
        state_map[name] = {}

        print('making dist list post')
        form_data = {}
        form_data.update(base_form_data)
        form_data.update({
            'ctl00$ScriptManager1': 'ctl00$upPnl|ctl00$ContentPlaceHolder$ddState',
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder$ddState',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            'ctl00$ddLanguage': '',
            'ctl00$ContentPlaceHolder$ddFinyear': '2022-2023',
            'ctl00$ContentPlaceHolder$ddState': val,
            'ctl00$ContentPlaceHolder$dddistrict': '-1',
            'ctl00$ContentPlaceHolder$ddType': '1',
            '__ASYNCPOST': 'true'
        })
        headers = {}
        headers.update(base_headers)
        headers['Referer'] = dist_url
        resp = session.post(dist_url, data=form_data, headers=headers)
        if not resp.ok:
            raise Exception('post to get district list failed')
        html, base_form_data = get_data_from_post(resp.text)
 
        print('getting dist full list for state')
        form_data = {}
        form_data.update(base_form_data)
        form_data.update({
            'ctl00$ScriptManager1': 'ctl00$upPnl|ctl00$ContentPlaceHolder$btnGO',
            'ctl00$ddLanguage': '',
            'ctl00$ContentPlaceHolder$ddFinyear': '2022-2023',
            'ctl00$ContentPlaceHolder$ddState': val,
            'ctl00$ContentPlaceHolder$dddistrict': '-1',
            'ctl00$ContentPlaceHolder$ddType': '1',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__ASYNCPOST': 'true',
            'ctl00$ContentPlaceHolder$btnGO': 'Show'
        })
        headers = {}
        headers.update(base_headers)
        headers['Referer'] = dist_url
        resp = session.post(dist_url, data=form_data, headers=headers)
        if not resp.ok:
            raise Exception('post to get district info failed')
        html, base_form_data = get_data_from_post(resp.text)
        s_soup = BeautifulSoup(html, 'html.parser')
        s_table = s_soup.find('table', {'id': 'tableReportTable'})
        trs = s_table.find_all('tr', recursive=False)
        for tr in trs:
            tds = tr.find_all('td', recursive=False)
            if len(tds) == 0:
                continue
            dist_td = tds[1]
            dist_name = dist_td.text.strip()
            if inp is not None and inp[1] != dist_name:
                continue
            hab_td = tds[2]
            dist_dir = state_dir_wip / f'{dist_name}'
            if dist_dir.exists():
                return

            state_map[name][dist_name] = True
            if inp is None:
                continue
            
            print(dist_name)
            dist_dir_wip = state_dir_wip / f'{dist_name}.wip'
            dist_dir_wip.mkdir(parents=True, exist_ok=True)
            a = hab_td.find('a')
            href = a.attrs['href']
            hab_ctl = href.split("'")[1]
            #hab_count = int(a.text.strip().replace(',', ''))

            print('post to prime hab list')
            hab_form_data = {}
            hab_form_data.update(base_form_data)
            hab_form_data.update({
                'ctl00$ScriptManager1': 'ctl00$upPnl|' + hab_ctl,
                'ctl00$ddLanguage': '',
                'ctl00$ContentPlaceHolder$ddFinyear': '2022-2023',
                'ctl00$ContentPlaceHolder$ddState': val,
                'ctl00$ContentPlaceHolder$dddistrict': '-1',
                'ctl00$ContentPlaceHolder$ddType': '1',
                '__EVENTTARGET': hab_ctl,
                '__EVENTARGUMENT': '',
                '__LASTFOCUS': '',
                '__ASYNCPOST': 'true',
            })
            h_headers = {}
            h_headers.update(base_headers)
            h_headers['Referer'] = dist_url
            resp = session.post(dist_url, data=hab_form_data, headers=h_headers)
            if not resp.ok:
                raise Exception('post to get district info failed')
            #print(resp.text)
            resp = session.get(list_url)
            if not resp.ok:
                raise Exception('getting habitation list failed')
            #print(resp.text)
            h_soup = BeautifulSoup(resp.text, 'html.parser')
            base_form_data = get_base_form_data(h_soup)
            page_links = h_soup.find_all('a', {'class': 'lnkPages'})
            page_map = {}
            for link in page_links:
                pno = link.text.strip()
                href = link.attrs['href']
                ctl = href.split("'")[1]
                page_map[pno] = ctl

            num_pages = len(page_map.keys())
            page_file = dist_dir_wip / '1.json'
            if not page_file.exists():
                print(f'{name}/{dist_name} handling page 1/{num_pages}')
                hab_list = extract_habitation_list(h_soup)
                with open(page_file, 'w') as f:
                    json.dump(hab_list, f)
            for pno in page_map.keys():
                if pno == '1':
                    continue
                page_file = dist_dir_wip / f'{pno}.json'
                if page_file.exists():
                    continue
                print(f'{name}/{dist_name} handling page {pno}/{num_pages}')
                ctl = page_map[pno]
                form_data = {}
                form_data.update(base_form_data)
                form_data.update({
                    'ctl00$ScriptManager1': 'ctl00$upPnl|' + ctl,
                    'ctl00$ddLanguage': '',
                    '__EVENTTARGET': ctl,
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__ASYNCPOST': 'true'
                })
                h_headers = {}
                h_headers.update(base_headers)
                h_headers['Referer'] = list_url
                resp = session.post(list_url, data=form_data, headers=h_headers)
                if not resp.ok:
                    raise Exception('post to get habitation list failed')

                # hack to overcome resp.text read truncation
                temp_file = data_dir / f'{name}.wip/{dist_name}.wip/{pno}.txt'
                temp_file.write_text(resp.text)
                resp_text = temp_file.read_text()
                temp_file.unlink()

                html, base_form_data = get_data_from_post(resp_text)
                #print(html)
                h_soup = BeautifulSoup(html, 'html.parser')
                try:
                    hab_list = extract_habitation_list(h_soup)
                except Exception as ex:
                    print(f'got exception {ex} while handling {name}/{dist_name}/{pno}')
                    raise ex
                with open(page_file, 'w') as f:
                    json.dump(hab_list, f)
            shutil.move(str(dist_dir_wip), str(dist_dir))
            if is_state_done(inp[2], name):
                shutil.move(str(state_dir_wip), str(state_dir))
        print(f'{name} - {state_map[name]}')

    if inp is None:
        return state_map

 
def is_state_done(state_map, s_name):
    state_dir_wip = data_dir / f'{s_name}.wip'
    dists = state_map[s_name]
    dists_done = set()
    for d_name in dists.keys():
        dist_dir = state_dir_wip / f'{d_name}'
        if dist_dir.exists():
            dists_done.add(d_name)
    all_dists = set(dists.keys())
    leftover = all_dists - dists_done
    return len(leftover) == 0



if __name__ == '__main__':
    state_map_file = data_dir / 'state_map.json'
    if state_map_file.exists():
        with open(state_map_file) as f:
            state_map = json.load(f)
    else:
        state_map = get_data()
        with open(state_map_file, 'w') as f:
            json.dump(state_map, f, indent=4)

    dist_list = []
    for s_name, dists in state_map.items():
        for d_name in dists.keys():
            dist_list.append((s_name, d_name, state_map))
    nb_processes = 8
    chunksize = max(1, min(128, len(dist_list) // nb_processes))
    done = 0
    with Pool(processes=nb_processes) as pool:
        for _ in pool.imap_unordered(get_data, dist_list, chunksize=chunksize):
            done += 1
            print(f'done - {done}/{len(dist_list)}')

    for s_name, dists in state_map.items():
        state_dir = data_dir / f'{s_name}'
        if state_dir.exists():
            continue
        state_dir_wip = data_dir / f'{s_name}.wip'
        dists_done = set()
        for d_name in dists.keys():
            dist_dir = state_dir_wip / f'{d_name}'
            if dist_dir.exists():
                dists_done.add(d_name)
        all_dists = set(dists.keys())
        leftover = all_dists - dists_done
        if len(leftover) == 0:
            shutil.move(str(state_dir_wip), str(state_dir))
        else:
            print(f'for {s_name}: {leftover=}')

        


