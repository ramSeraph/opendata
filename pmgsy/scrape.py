import json
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

"""
  --data-raw 'states=Kerala&layers=Proposals&__RequestVerificationToken=CfDJ8DmqCuVoP1lDk1fv5fm5urMMbHLK1JCCp7vOopG2Wbh9wPzbrZYwm-gSjV4T6IdxDbq5smq04dOO5BlEH6LShUSuCqGxwvdb7lsV0f6gPOuQTLDjb4Rzo7nhUzMjc7HM5Q0Tp-9AQRXA0EsxY32lYBM',
"""


masterdata_url = 'https://geosadak-pmgsy.nic.in/MsFiles/MasterData.xls'
base_url = 'https://geosadak-pmgsy.nic.in/opendata/'
download_url = 'https://geosadak-pmgsy.nic.in/OpenData/DownloadShapefile'

base_headers = {
    'authority': 'geosadak-pmgsy.nic.in',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'origin': 'https://geosadak-pmgsy.nic.in',
    'pragma': 'no-cache',
    'referer': 'https://geosadak-pmgsy.nic.in/opendata/',
    'sec-ch-ua': '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
}



def get_session():
    session = requests.session()
    headers = {} 
    headers.update(base_headers)
    del headers['referer']
    resp = session.get(base_url, headers=headers)
    if not resp.ok:
        raise Exception('unable to get base page to get cookies')
    soup = BeautifulSoup(resp.text, 'html.parser')
    form = soup.find('form')
    token_field = '__RequestVerificationToken'
    inp = form.find('input', { 'name': token_field })
    token_value = inp.attrs['value']
    return session, { token_field: token_value }

def get_list(session, suburl):
    headers = {}
    headers.update(base_headers)
    headers['accept'] = '*/*'
    headers['x-requested-with'] = 'XMLHttpRequest'
    resp = session.get(base_url + suburl, headers=headers)
    if not resp.ok:
        raise Exception(f'unable to get {suburl}')
    return json.loads(resp.text)
    
def get_states(session):
    return get_list(session, 'getallstates')

def get_layers(session):
    layers = get_list(session, 'getalllayers')
    if 'Bound_Block' not in layers:
        layers += ['Bound_Block']
    return layers
        

def get_data(session, form_data, layer, state):
    date = datetime.now()
    date_str = date.strftime('%d%b%Y')
    file = Path(f'data/raw/{date_str}/{layer}/{state}.zip')
    if file.exists():
        return
    print(f'downlaoding {file}')
    file.parent.mkdir(exist_ok=True, parents=True)
    headers = {}
    headers.update(base_headers)
    headers['content-type'] = 'application/x-www-form-urlencoded'
    data = {}
    data.update(form_data)
    form_data['states'] = state
    form_data['layers'] = layer
    resp = session.post(download_url, data=form_data)
    if not resp.ok:
        raise Exception(f'unable to get {layer} for {state}')
    with open(file, 'wb') as f:
        f.write(resp.content)

def get_master_data(session):
    date = datetime.now()
    date_str = date.strftime('%d%b%Y')
    file = Path(f'data/raw/{date_str}/MasterData.xls')
    if file.exists():
        return
    print(f'downlaoding {file}')
    file.parent.mkdir(exist_ok=True, parents=True)
    headers = {}
    headers.update(base_headers)
    headers['accept'] = '*/*'
    resp = session.get(masterdata_url, headers=headers)
    if not resp.ok:
        raise Exception(f'unable to get masterdata')
    with open(file, 'wb') as f:
        f.write(resp.content)

if __name__ == '__main__':
    session, form_data = get_session()
    get_master_data(session)
    layers = get_layers(session)
    #print(layers)
    #exit(0)
    #layers = ['Facilities', 'Habitation', 'Proposal PMGSY-I', 'Proposal PMGSY-II', 'Proposal PMGSY-III', 'Proposal RCPLWEA', 'Railway', 'Road(Candidate)', 'Road(DRRP)', 'Tourist Place', 'Bound_Block']
    states = get_states(session)
    #print(layers, states)
    #exit(0)
    for layer in layers:
        for state in states:
            get_data(session, form_data, layer, state)

