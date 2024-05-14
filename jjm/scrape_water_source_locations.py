import csv
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

from bs4 import BeautifulSoup

num_parallel = 20

base_url = 'https://ejalshakti.gov.in'
list_url = 'https://ejalshakti.gov.in/JJM/JJMReports/profiles/rpt_VillageProfile.aspx'

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

state_done_count = 0
dist_done_count = 0
block_done_count = 0
gp_done_count = 0
vill_done_count = 0
data_dir = Path('data')

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


out_fields = [
    'state_name', 'state_id',
    'dist_name', 'dist_id',
    'block_name', 'block_id',
    'gp_name', 'gp_id',
    'village_name', 'village_id',
    'village_lgd_id', 'hab_name',
    'src_name', 'src_type',
    'ws_coords',
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

def get_client():
    return aiohttp.ClientSession()

async def write_entry(r_q, ws_info, stack, leaf):
    data = {}
    for key in out_fields:
        data[key] = None

    for s in stack:
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

    data['village_lgd_id'] = ws_info[0]
    data['hab_name'] = ws_info[1]
    data['src_name'] = ws_info[2]
    data['src_type'] = ws_info[3]
    data['ws_coords'] = ws_info[4]
    row = []
    for key in out_fields:
        row.append(data[key])
    if leaf:
        entry = None
    else:
        entry = stack[-1]

    await r_q.put((row, entry))


def get_entries(soup, typ):
    key = select_ids[typ]
    select = soup.find('select', {'id': key })
    options = select.find_all('option')
    option_entries = [ (o.get('value'), o.text.strip()) for o in options ]
    return option_entries

def update_form_from_stack(form_data, stack):
    form_data.update({
        'ctl00$CPHPage$hdntagwatersource': '',
        'ctl00$CPHPage$txtAutoPageName': '',
        '__ASYNCPOST': 'true',
    })
    # for blocks
    # ctl00$CPHPage$ddList: -1

    for k in vars_map.values():
        form_data[k] = '-1'

    for s in stack:
        var = vars_map[s[0]]
        form_data.update({
            'ctl00$ScriptManager1': 'ctl00$upPnl|' + var,
            '__EVENTTARGET': var,
            var: s[1] 
        })

async def extract_locs(i, session, r_q, form_data, stack, pop_done):
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

    village_id = stack[-1][1]
    try:
        vill_lgd_id, items = get_data_from_page(html)
    except:
        with open(f'{village_id}.html', 'w') as f:
            f.write(html)
        raise
    await write_entry(r_q, (vill_lgd_id, None, None, None, None), stack, True)
    for item in items:
        hab_name, src_str, src_type, loc_str = item
        await write_entry(r_q, (vill_lgd_id, hab_name, src_str, src_type, loc_str), stack, True)





async def drill_recursive(i, session, r_q, typ, soup, base_form_data, stack, locs_done):
    global state_done_count, dist_done_count, block_done_count, gp_done_count, vill_done_count
    entries = get_entries(soup, typ)
    # special case when there is only one option and other fields get autofilled
    if len(entries) == 1 and typ != 'village':
        entry = entries[0]
        if (typ, entry[0]) in locs_done:
            return
        stack.append((typ, *entry))
        await drill_recursive(i, session, r_q, next_type[typ], soup, base_form_data, stack, locs_done)
        await write_entry(r_q, (None, None, None, None, None), stack, False)
        stack.pop()
        return

    random.seed(datetime.now().timestamp())
    random.shuffle(entries)
    for entry in entries:
        if entry[0] == '-1':
            continue
        if (typ, entry[0]) in locs_done:
            continue
        stack.append((typ, *entry))
        form_data = {}
        form_data.update(base_form_data)
        update_form_from_stack(form_data, stack)
        #print(f'{i:<3}: exploring {stack=}')
        #nxt = next_type[typ]
        if typ == 'village':
            await extract_locs(i, session, r_q, form_data, stack, locs_done)
        else:
            resp = await session.post(list_url, data=form_data, headers=post_headers)
            if not resp.ok:
                raise Exception(f'{i}: unable to drill further: {stack=}')
            resp_text = await resp.text()
            try:
                html, new_base_form_data = get_data_from_post(resp_text)
            except:
                print(f'ERROR: failed stack {stack}')
                raise
            new_soup = BeautifulSoup(html, 'html.parser')
            await drill_recursive(i, session, r_q, next_type[typ], new_soup, new_base_form_data, stack, locs_done)
        if len(stack) == 1:
            state_done_count += 1
        if len(stack) == 2:
            dist_done_count += 1
        if len(stack) == 3:
            block_done_count += 1
        if len(stack) == 4:
            gp_done_count += 1
        if len(stack) == 5:
            vill_done_count += 1
        if len(stack) <= 3:
            print(f'{i:<3}: done exploring {stack=} {state_done_count=} {dist_done_count=} {block_done_count=} {gp_done_count=} {vill_done_count=}')
        await write_entry(r_q, (None, None, None, None, None), stack, False)
        stack.pop()


async def run(i, r_q, session, locs_done):
    print('getting main page')
    stack = []
    resp = await session.get(list_url, headers=base_headers)
    if not resp.ok:
        raise Exception(f'{i}: unable to get main page: {list_url}')

    resp_text = await resp.text()
    soup = BeautifulSoup(resp_text, 'html.parser')
    base_form_data = get_base_form_data(soup)
    await drill_recursive(i, session, r_q, 'state', soup, base_form_data, stack, locs_done)


async def run_wrap(i, r_q, locs_done):
    try:
        async with aiohttp.ClientSession() as session:
            await run(i, r_q, session, locs_done)
    except:
        traceback.print_exc()
        print(f'RUUNER {i} FAILED')

async def writer(q, locs_done):
    locs_file = 'data/facilities/water_sources_raw.csv'
    async with aiofiles.open(locs_file, mode='a') as f:
        writer = aiocsv.AsyncWriter(f)
        while True:
            res = await q.get()
            q.task_done()
            if res is None:
                break
            row, entry = res

            if entry is None:
                await writer.writerow(row)
                continue

            if (entry[0], entry[1]) in locs_done:
                continue
            await writer.writerow(row)
            locs_done.add((entry[0], entry[1]))

async def writer_wrap(q, locs_done):
    try:
        await writer(q, locs_done)
    except:
        traceback.print_exc()
        print('WRITER FAILED')




async def scrape_data(locs_done):
    res_queue = asyncio.Queue()
    w_task = asyncio.create_task(writer_wrap(res_queue, locs_done))
    scrape_tasks = [ asyncio.create_task(run_wrap(i, res_queue, locs_done)) for i in range(num_parallel)]
    await asyncio.sleep(5)
    await asyncio.gather(*scrape_tasks)
    await res_queue.put(None)
    await res_queue.join()
    await asyncio.gather(w_task)


def get_data_from_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    span = soup.find('span', {'id': 'CPHPage_lblVillage'})
    if span is None:
        return 'NA', []
    vill_label = span.text
    vill_lgd_id = vill_label.split(':')[-1].replace(')','').strip()
    items = []
    trs = soup.find_all('tr')
    tr_srcs = [ tr for tr in trs if tr.has_attr('id') and tr.get('id').startswith('CPHPage_rptSource_tr_Approved_') ]
    for tr in tr_srcs:
        tds = list(tr.find_all('td', recursive=False))
        span = tds[1].find('span', recursive=False)
        if span is None:
            continue
        hab_name = tds[1].text.strip()
        src_link = tds[2].find('a', recursive=False)
        src_str = src_link.text.strip()
        src_type = tds[3].text.strip()
        link = tds[4].find('a', recursive=False)
        coords_str = link.text.strip()
        items.append((hab_name, src_str, src_type, coords_str))
    return vill_lgd_id, items



if __name__ == '__main__':
    locs_done = set()
    locs_file = Path('data/facilities/water_sources_raw.csv')
    print('processing locs file')
    if locs_file.exists():
        with open(locs_file, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r['village_lgd_id'] != '':
                    continue
                if r['village_id'] != '':
                    locs_done.add(('village', r['village_id']))
                    vill_done_count += 1
                    continue
                if r['gp_id'] != '':
                    locs_done.add(('gp', r['gp_id']))
                    gp_done_count += 1
                    continue
                if r['block_id'] != '':
                    locs_done.add(('block', r['block_id']))
                    block_done_count += 1
                    continue
                if r['dist_id'] != '':
                    locs_done.add(('dist', r['dist_id']))
                    dist_done_count += 1
                    continue
                if r['state_id'] != '':
                    locs_done.add(('state', r['state_id']))
                    state_done_count += 1
                    continue
    else:
        with open(locs_file, 'w') as f:
            wr = csv.DictWriter(f, fieldnames=out_fields)
            wr.writeheader()

    asyncio.run(scrape_data(locs_done))

