import json
import csv
import io
import re
import copy
import shutil
import random
import asyncio
import aiohttp
import traceback

from pathlib import Path
from datetime import datetime

import aiofiles
import aiocsv

#from aiohttp.client_exceptions import ServerDisconnectedError, ClientOSError
#from aiohttp_retry import RetryClient, JitterRetry

from Levenshtein import distance
from bs4 import BeautifulSoup



random.seed(datetime.now().timestamp())    

num_parallel = 10
base_url = 'https://ejalshakti.gov.in'
list_url = 'https://ejalshakti.gov.in/JJM/JJMReports/BasicInformation/JJMRep_RWS_RuralPopulation.aspx'
fname = 'data/hab_pop_raw.csv'

post_headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Host': 'ejalshakti.gov.in',
    'Origin': base_url,
    'Pragma': 'no-cache',
    'Referer': list_url,
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'X-MicrosoftAjax': 'Delta=true',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
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

def get_entries(soup, typ, pop_done):
    key = select_ids[typ]
    select = soup.find('select', {'id': key })
    options = select.find_all('option')
    option_entries = [ (o.get('value'), o.text.strip()) for o in options ]
    return [ o for o in option_entries if o[0] != '-1' and (typ, o[0]) not in pop_done ]


def hab_canon(name):
    out = name
    m = re.match(r'^(.*)(\([0-9]{16}\))$', out)
    if m is not None:
        out = m.group(1)
    out = gen_canon(out)
    return out



out_fields = [
    'state_name', 'state_id',
    'dist_name', 'dist_id',
    'block_name', 'block_id',
    'gp_name', 'gp_id',
    'village_name', 'village_id',
    'hab_name',
    'pop_sc', 'pop_st', 'pop_gen'
]

select_ids = {
    'state': 'CPHPage_ddState',
    'dist': 'CPHPage_ddDistrict',
    'block': 'CPHPage_ddblock',
    'gp': 'CPHPage_ddPanchayat',
    'village': 'CPHPage_ddVillage',
}

vars_map = {
    'state': 'ctl00$CPHPage$ddState',
    'dist': 'ctl00$CPHPage$ddDistrict',
    'block': 'ctl00$CPHPage$ddblock',
    'gp': 'ctl00$CPHPage$ddPanchayat',
    'village': 'ctl00$CPHPage$ddVillage',
}

next_type = {
    'state': 'dist',
    'dist': 'block',
    'block': 'gp',
    'gp': 'village',
    'village': 'hab'
}

async def write_entry(r_q, pop_info, entry, stack):
    data = {}
    for key in out_fields:
        data[key] = None

    new_arr = stack + [ entry ]
    for s in new_arr:
        if s[0] == 'state':
            data['state_id'] = s[1]
            data['state_name'] = s[2]
        elif s[0] == 'dist':
            data['dist_id'] = s[1]
            data['dist_name'] = s[2]
        elif s[0] == 'block':
            data['block_id'] = s[1]
            data['block_name'] = s[2]
        elif s[0] == 'gp':
            data['gp_id'] = s[1]
            data['gp_name'] = s[2]
        elif s[0] == 'village':
            data['village_id'] = s[1]
            data['village_name'] = s[2]
        elif s[0] == 'hab':
            data['hab_name'] = s[1][1]

    data['pop_sc'] = pop_info[0]
    data['pop_st'] = pop_info[1]
    data['pop_gen'] = pop_info[2]
    row = []
    for key in out_fields:
        row.append(data[key])

    await r_q.put((row, entry))

async def writer(q, pop_done):
    async with aiofiles.open(fname, mode='a') as f:
        writer = aiocsv.AsyncWriter(f)
        while True:
            res = await q.get()
            q.task_done()
            if res is None:
                break
            row, entry = res

            if (entry[0], entry[1]) in pop_done:
                continue
            await writer.writerow(row)
            pop_done.add((entry[0], entry[1]))


async def writer_wrap(q, pop_done):
    try:
        await writer(q, pop_done)
    except:
        traceback.print_exc()
        print('WRITER FAILED')



async def extract_habs(i, session, r_q, form_data, stack, pop_done):
    var = 'ctl00$CPHPage$btnShow'
    form_data.update({
        'ctl00$ScriptManager1': 'ctl00$upPnl|' + var,
        '__EVENTTARGET': '',
        var: 'Show'
    })

    resp = await session.post(list_url, data=form_data, headers=post_headers)
    if not resp.ok:
        raise Exception(f'{i}: unable to drill further: {stack=}')

    resp_text = await resp.text()
    html, _ = get_data_from_post(resp_text)

    new_soup = BeautifulSoup(html, 'html.parser')
    table = new_soup.find('table', {'id': 'tableReportTable' })
    if table is None:
        return
    trs = table.find_all('tr', recursive=False)
    trs = trs[:-1]
    for tr in trs:
        tds = tr.find_all('td', recursive=False)
        td_vals = [ td.text.strip() for td in tds ]
        pop_info = ( td_vals[2], td_vals[3], td_vals[4] )
        hab_name = td_vals[1]
        village_id = stack[-1][1]
        await write_entry(r_q, pop_info, ('hab', (village_id, hab_name)), stack)



def update_form_from_stack(form_data, stack):
    form_data.update({
        'ctl00$CPHPage$ddFinyear': '2023-2024',
    })
    for k in vars_map.values():
        form_data[k] = '-1'

    for s in stack:
        var = vars_map[s[0]]
        form_data.update({
            'ctl00$ScriptManager1': 'ctl00$upPnl|' + var,
            '__EVENTTARGET': var,
            var: s[1] 
        })

async def drill_recursive(i, session, r_q, typ, soup, base_form_data, stack, pop_done):
    entries = get_entries(soup, typ, pop_done)
    random.seed(datetime.now().timestamp())    
    random.shuffle(entries)
    for entry in entries:
        if entry[0] == '-1':
            continue
        if (typ, entry[0]) in pop_done:
            continue
        stack.append((typ, *entry))
        form_data = {}
        form_data.update(base_form_data)
        update_form_from_stack(form_data, stack)
        #print(f'{i:<3}: exploring {stack=}')
        nxt = next_type[typ]
        if typ == 'village':
            try:
                await extract_habs(i, session, r_q, form_data, stack, pop_done)
            except:
                print(f'failed to extract habs from {stack}')
                stack_entry = stack.pop()
                await write_entry(r_q, (None, None, None), stack_entry, stack)
                continue
        else:
            resp = await session.post(list_url, data=form_data, headers=post_headers)
            if not resp.ok:
                raise Exception(f'{i}: unable to drill further: {stack=}')
            resp_text = await resp.text()
            html, new_base_form_data = get_data_from_post(resp_text)
            new_soup = BeautifulSoup(html, 'html.parser')
            await drill_recursive(i, session, r_q, next_type[typ], new_soup, new_base_form_data, stack, pop_done)
        if len(stack) <= 3:
            print(f'{i:<3}: done exploring {stack=}')
        stack_entry = stack.pop()
        await write_entry(r_q, (None, None, None), stack_entry, stack)

def get_client():
    return aiohttp.ClientSession()
    #retry_options = JitterRetry(exceptions=[ServerDisconnectedError, ClientOSError, asyncio.TimeoutError])
    #retry_client = RetryClient(raise_for_status=False, retry_options=retry_options)
    #return retry_client


async def run(i, r_q, session, pop_done):
    print('getting main page')
    stack = []
    resp = await session.get(list_url, headers=base_headers)
    if not resp.ok:
        raise Exception(f'{i}: unable to get main page: {list_url}')

    resp_text = await resp.text()
    soup = BeautifulSoup(resp_text, 'html.parser')
    base_form_data = get_base_form_data(soup)
    await drill_recursive(i, session, r_q, 'state', soup, base_form_data, stack, pop_done)

async def run_wrap(i, r_q, pop_done):
    try:
        async with aiohttp.ClientSession() as session:
            await run(i, r_q, session, pop_done)
    except:
        traceback.print_exc()
        print(f'RUUNER {i} FAILED')


async def scrape_data(pop_done):
    res_queue = asyncio.Queue()
    w_task = asyncio.create_task(writer_wrap(res_queue, pop_done))
    scrape_tasks = [ asyncio.create_task(run_wrap(i, res_queue, pop_done)) for i in range(num_parallel)]
    await asyncio.sleep(5)
    await asyncio.gather(*scrape_tasks)
    await res_queue.put(None)
    await res_queue.join()
    await asyncio.gather(w_task)

if __name__ == '__main__':
    pop_done = set()
    pop_file = Path(fname)
    print('processing hab_pop file')
    if pop_file.exists():
        with open(pop_file, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r['hab_name'] != '':
                    pop_done.add(('hab', (r['village_id'], r['hab_name'])))
                    continue
                if r['village_id'] != '':
                    pop_done.add(('village', r['village_id']))
                    continue
                if r['gp_id'] != '':
                    pop_done.add(('gp', r['gp_id']))
                    continue
                if r['block_id'] != '':
                    pop_done.add(('block', r['block_id']))
                    continue
                if r['dist_id'] != '':
                    pop_done.add(('dist', r['dist_id']))
                    continue
                if r['state_id'] != '':
                    pop_done.add(('state', r['state_id']))
                    continue
                print('All Done!!!')
                exit(0)
    else:
        with open(pop_file, 'w') as f:
            wr = csv.DictWriter(f, fieldnames=out_fields)
            wr.writeheader()

    asyncio.run(scrape_data(pop_done))

