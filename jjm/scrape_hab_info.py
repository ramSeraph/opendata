import re
import csv
import json
import asyncio
import traceback

from pathlib import Path
from pprint import pprint

from aiohttp.client_exceptions import ServerDisconnectedError, ClientOSError
from aiohttp_retry import RetryClient, JitterRetry
import aiohttp
import aiofiles
from aiopath import AsyncPath

from bs4 import BeautifulSoup

hab_file = Path('data/habitations.csv')

hab_info_file = Path('data/hab_info.jsonl')

#hab_errors_dir = Path('data/hab_info_errors')
#hab_errors_dir.mkdir(exist_ok=True, parents=True)

hab_inter_dir = Path('data/hab_info_inter')
hab_inter_dir.mkdir(exist_ok=True, parents=True)
nb_processes = 20
nb_processes = 1

def get_client():
    retry_options = JitterRetry(exceptions=[ServerDisconnectedError, ClientOSError, asyncio.TimeoutError])
    retry_client = RetryClient(raise_for_status=False, retry_options=retry_options)
    return retry_client


class KnownParseException(Exception):
    def __init__(self, html):
        super().__init__()
        self.html = html

def parse_water_sources(water_sources_table, has_thead=True):
    #print(water_sources_table)
    w_trs = water_sources_table.find_all('tr', recursive=False)
    water_sources_title = w_trs[0].text.strip()
    w_table = w_trs[1].find('table')
    if has_thead:
        w_head = w_table.find('thead')
        w_h_trs = w_head.find_all('tr')
        rows = w_table.find_all('tr', recursive=False)
    else:
        w_table = w_trs[1].find('table')
        w_t_trs = w_table.find_all('tr', recursive=False)
        w_h_trs = w_t_trs[:2]
        rows = w_t_trs[2:]

    w_ths_1 = w_h_trs[0].find_all('th')
    w_ths_2 = w_h_trs[1].find_all('th')
    keys1 = []
    keys2 = []
    for th in w_ths_1:
        val = th.text.strip()
        if th.attrs.get('rowspan') == "2":
            keys1.append(val)
            keys2.append(val)
        else:
            colspan = th.attrs.get('colspan')
            colspan = int(colspan)
            keys1.extend([val] * colspan)
            keys2.extend([None] * colspan)

    for th in w_ths_2:
        val = th.text.strip()
        for i, k in enumerate(keys2):
            if k is not None:
                continue
            keys2[i] = val
            break
     
    #print(keys1)
    #print(keys2)
    data = []
    for row in rows:
        cols = list(row.find_all('td'))
        entry = {}
        for i, col in enumerate(cols):
            if keys1[i] == keys2[i]:
                entry[keys1[i]] = col.text.strip()
            else:
                if keys1[i] not in entry:
                    entry[keys1[i]] = {}
                entry[keys1[i]][keys2[i]] = col.text.strip()
        data.append(entry)
    return water_sources_title, data

def parse_facilities(table):
    f_trs = table.find_all('tr', recursive=False)
    f_title = f_trs[0].text.strip()
    f_table = f_trs[-1].find('table')
    if f_table is None:
        return f_title, []
    f_d_trs = list(f_table.find_all('tr', recursive=False))
    f_d_ths = f_d_trs[0].find_all('th')
    keys = [ th.text.strip() for th in f_d_ths ]
    f_d_trs = f_d_trs[1:]
    data = []
    for tr in f_d_trs:
        cols = tr.find_all('td')
        vals = [ c.text.strip() for c in cols ]
        data.append(dict(zip(keys, vals)))
    return f_title, data



def parse_hab_info(html):
    full_data = {}
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find('div', { 'id': 'ContentPlaceHolder_reportContent' })
    if div is None:
        raise KnownParseException(html)
    table = div.find('table')
    table_nested = table.find('table')

    trs = list(table_nested.find_all('tr', recursive=False))
    num_trs = len(trs)

    i = 0
    while True:
        if i >= num_trs:
            break
        curr_tr = trs[i]
        if i == 0:
            header_title = trs[i].text.strip()
            i += 3
            header_table = trs[i].find('table')
            header_tds = header_table.find_all('td')
            header_data = {}
            for h_td in header_tds:
                spans = h_td.find_all('span')
                key = spans[0].text.strip()
                val = spans[1].text.strip()
                header_data[key] = val
            full_data[header_title] = header_data
            i += 1

            abstract_title = trs[i].text.strip()
            i += 1
            abstract_data = {}
            abstract_table = trs[i].find('table')
            abstract_trs = abstract_table.find_all('tr', recursive=False)
            for tr in abstract_trs:
                tds = tr.find_all('td', recursive=False)
                key = tds[0].text.strip()
                table = tds[1].find('table')
                if table is None:
                    val = tds[1].text.strip()
                else:
                    table_style = table.attrs.get('style', '')
                    if table_style.find('display:none') != -1:
                        span = tds[1].find('span', recursive=False)
                        val = span.text.strip()
                    else:
                        val = {}
                        sub_tds = table.find_all('td')
                        for sub_td in sub_tds:
                            spans = sub_td.find_all('span')
                            sub_key = spans[0].text.strip()
                            sub_val = spans[1].text.strip()
                            val[sub_key] = sub_val
                abstract_data[key] = val
            full_data[abstract_title] = abstract_data
            i += 1
            continue

        # optional tables
        curr_tr_id = curr_tr.attrs.get('id', None)
        if curr_tr_id in [ 'ContentPlaceHolder_tr_SPOTSourcesReported',
                           'ContentPlaceHolder_tr_DeliveryPointReported' ]:
            table_title, data = parse_water_sources(curr_tr.find('table'))
            full_data[table_title] = data
            i += 1
            continue
        if curr_tr_id == 'ContentPlaceHolder_tr_HouseConnectionsReported':
            table_title, data = parse_water_sources(curr_tr.find('table'), has_thead=False)
            full_data[table_title] = data
            i += 1
            continue
        if curr_tr_id in [ 'ContentPlaceHolder_tr_SurfaceWaterbodySourceReported',
                           'ContentPlaceHolder_tr_TapConnection',
                           'ContentPlaceHolder_tr_TreatmentPlan',
                           'ContentPlaceHolder_tr_ExistingPrivatePublicSourcesReported',
                           'ContentPlaceHolder_tr_SestaniblityStracture' ]:
            table_title, data = parse_facilities(curr_tr.find('table'))
            full_data[table_title] = data
            i += 1
            continue
   
        if curr_tr.text.strip() == '':
            i += 1
            continue

        # unexpected:
        print(f'found unexpected tr at {i}: {curr_tr}')
        raise Exception('unexpected tr')
    return full_data

def fix_html(html):
    html = re.sub(r'(<th rowspan="2" >[\s]+Block Name[\s]+)</td>', r'\1</th>', html)
    html = re.sub(r'(<th rowspan="2" >[\s]+[^\n]*Village Name[^\n]*[\s]+)</td>', r'\1</th>', html)
    return html

async def get_hab_info(session, hab_id, url_id, task_id=None):
    print(f'{task_id=} handling {hab_id=}, {url_id=}')
    url = f'https://ejalshakti.gov.in/imisreports/Reports/Profile/rpt_HabitationProfile.aspx?Rep=Y&Id={url_id}'
    resp = await session.get(url)
    if not resp.ok:
        raise Exception(f'{task_id=} unable to get hab info for {url_id=}')
    html = await resp.text()
    html = fix_html(html)

    html_file = hab_inter_dir / f'{hab_id}.html'
    async with aiofiles.open(str(html_file), mode='w') as f:
        await f.write(html)

    try:
        res = parse_hab_info(html)
    except KnownParseException:
        print(f'{task_id=} got known exception while parsing {hab_id=}, {url_id=}')
        #traceback.print_exc()
        res = { 'error': 'no_data' }
    res['url_id'] = url_id
    res['hab_id'] = hab_id
    html_file.unlink()
    return res

def get_all_url_ids():
    ids = []
    with open(hab_file, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            ids.append((r['id'], r['url_id']))
    return set(ids)

def get_done_url_ids():
    if not hab_info_file.exists():
        return set()

    done = set()
    with open(hab_info_file, 'r') as f:
        for line in f:
            info = json.loads(line)
            done.add((info['hab_id'], info['url_id']))
    return done

def get_leftover_url_ids():
    print('getting all ids')
    all_ids = get_all_url_ids()
    print('getting done ids')
    done_ids = get_done_url_ids()
    return all_ids - done_ids

async def runner(task_id, j_q, r_q):
    #async with aiohttp.ClientSession() as session:
    async with get_client() as session:
        while True:
            hab_id, url_id = await j_q.get()
            try:
                res = await get_hab_info(session, hab_id, url_id, task_id=task_id)
            except Exception:
                print(f'RUNNER {task_id} FAILED')
                traceback.print_exc()
                return
            await r_q.put((res, hab_id, url_id))



async def writer(total, r_j_q):
    i = 0
    async with aiofiles.open(str(hab_info_file), mode='a') as f:
        while True:
            res = await r_j_q.get()
            if res is None:
                r_j_q.task_done()
                break
            details, hab_id, url_id = res
            if details is None:
                print(f'failed to get details for {hab_id=} {url_id=}')
                continue
            line = json.dumps(details)
            await f.write(line + '\n')
            await f.flush()
            r_j_q.task_done()
            i += 1
            print(f'done - {i}/{total}')



async def writer_wrap(total, r_j_q):
    try:
        await writer(total, r_j_q)
    except:
        print('WRITER FAILED')
        traceback.print_exc()

async def submitter(id_tuples, queue):
    for id_tuple in id_tuples:
        await queue.put(id_tuple)
    await queue.put(None)


async def get_all_hab_infos(todo_ids):
    total = len(todo_ids)
    job_queue = asyncio.Queue(maxsize=2*nb_processes)
    res_queue = asyncio.Queue()
    s_task = asyncio.create_task(submitter(todo_ids, job_queue))
    w_task = asyncio.create_task(writer_wrap(total, res_queue))
    all_tasks = []
    all_tasks.extend([s_task, w_task])
    for i in range(nb_processes):
        r_task = asyncio.create_task(runner(i, job_queue, res_queue))
        all_tasks.append(r_task)


    await asyncio.sleep(5)
    try:
        await asyncio.gather(*all_tasks, return_exceptions=False)
    except Exception as ex:
        print(f'got exception from one of the tasks, {ex}')



if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        html = Path(sys.argv[1]).read_text()
        html = fix_html(html)
        #html = re.sub(r'(<th rowspan="2" >\n[\s]+Block Name\n[\s]+)</td>', r'\1</th>', html)
        #html = re.sub(r'(<th rowspan="2" >\n[\s]+[^\n]*Village Name[^\n]*\n[\s]+)</td>', r'\1</th>', html)
        res = parse_hab_info(html)
        pprint(res, sort_dicts=False)
        exit(0)

    todo_ids = get_leftover_url_ids()
    print(f'{len(todo_ids)=}')
    asyncio.run(get_all_hab_infos(todo_ids))

