import os, requests
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv('.env')
key = os.environ.get('N8N_API_KEY')
headers = {'X-N8N-API-KEY': key}

wid = 'iOCitbp5vyK7lS7p'
resp = requests.get(f'http://localhost:5678/api/v1/workflows/{wid}', headers=headers, timeout=10)
print(f'Workflow {wid} status:', resp.status_code)
if resp.status_code == 200:
    w = resp.json()
    print(f"name: {w.get('name')}")
    print(f"active: {w.get('active')}")
    for n in w.get('nodes', []):
        print(f"  node: {n.get('name')} type={n.get('type')}")
        p = n.get('parameters', {})
        if 'path' in p: print(f"    webhook path: /webhook/{p['path']}")
        if 'url' in p: print(f"    HTTP url: {p['url']}")
        if 'method' in p: print(f"    HTTP method: {p['method']}")
        if 'sendBody' in p: print(f"    sendBody: {p['sendBody']}")
        if 'jsonBody' in p: print(f"    jsonBody: {p['jsonBody']}")
        if 'fileName' in p: print(f"    fileName: {p['fileName']}")
        if 'options' in p and p['options']: print(f"    options: {p['options']}")
