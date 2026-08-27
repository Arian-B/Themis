import os, json, requests
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv('.env')

key = os.environ.get('N8N_API_KEY')
headers = {'X-N8N-API-KEY': key, 'Content-Type': 'application/json'}
resp = requests.get('http://localhost:5678/api/v1/workflows', headers=headers, timeout=10)
print('GET /workflows status:', resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    wfs = data.get('data', [])
    print(f'Total workflows: {len(wfs)}')
    for w in wfs:
        print(f"  id={w.get('id')} name={w.get('name')} active={w.get('active')} nodes={[n.get('name') for n in w.get('nodes',[])]}")
    if not wfs:
        print('No workflows found. Importing and activating high-risk webhook...')
        with open('automation/n8n_high_risk_webhook.json') as f:
            wd = json.load(f)
        wd['settings'] = {}
        wd.pop('active', None)
        r2 = requests.post('http://localhost:5678/api/v1/workflows', headers=headers, json=wd, timeout=15)
        print('Import status:', r2.status_code, r2.text[:200])
        if r2.status_code == 200:
            wid = r2.json().get('id')
            r3 = requests.post(f'http://localhost:5678/api/v1/workflows/{wid}/activate', headers=headers, timeout=10)
            print('Activate status:', r3.status_code, r3.text[:200])
else:
    print('Failed:', resp.text[:300])
