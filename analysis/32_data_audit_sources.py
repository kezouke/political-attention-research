"""Acquire and pin audit metadata; no outcome estimation or model fitting.

Usage: python analysis/32_data_audit_sources.py
Raw responses stay in ignored data/raw/audit_20261106. Successful responses are
cached; a manifest records provenance, hashes and HTTP status. Do not infer that
a dataset is usable simply because its metadata were downloaded.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin
import hashlib
import json
import re
import threading
from datetime import datetime, timezone
import requests
import argparse
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
OUT = ROOT / 'data/processed/audit_20261106'
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
MANIFEST = OUT / 'acquisition_manifest.json'
records = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
lock = threading.Lock()

def fetch(key, url, suffix='.txt', max_bytes=150_000_000, expected_sha256=None):
    path = RAW / (key + suffix)
    old = records.get(key)
    if path.exists() and old and old.get('status') == 200 and old.get('url') == url:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == old['sha256']
        return path
    try:
        r = requests.get(url, timeout=(15, 60), stream=True)
        data = bytearray()
        for chunk in r.iter_content(1024 * 1024):
            data.extend(chunk)
            if len(data) > max_bytes:
                raise ValueError(f'response exceeds {max_bytes} bytes')
        rec = {'url': url, 'resolved_url': r.url, 'status': r.status_code,
               'retrieved_utc': datetime.now(timezone.utc).isoformat(),
               'bytes': len(data), 'content_type': r.headers.get('Content-Type'),
               'sha256': hashlib.sha256(data).hexdigest(),
               'local_path': str(path.relative_to(ROOT))}
        if expected_sha256 and (r.status_code != 200 or rec['sha256'] != expected_sha256):
            raise ValueError('Pinned source changed or became unavailable; refusing to replace audit snapshot.')
        path.write_bytes(data)
    except Exception as exc:
        if expected_sha256:
            raise RuntimeError(f'Cannot replay pinned source {key}: {exc}') from exc
        rec = {'url': url, 'status': 'error', 'error': str(exc),
               'retrieved_utc': datetime.now(timezone.utc).isoformat()}
    with lock:
        records[key] = rec
        MANIFEST.write_text(json.dumps(records, indent=2, ensure_ascii=False) + '\n')
    print(key, rec['status'], rec.get('bytes', 0), flush=True)
    return path if rec['status'] == 200 else None

def run_jobs(jobs):
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(lambda a: fetch(*a), jobs))

def main():
    pages = {
        'cses2_page':'https://cses.org/data-download/cses-module-2-2001-2006/',
        'cses3_page':'https://cses.org/data-download/cses-module-3-2006-2011-2/',
        'cses4_page':'https://cses.org/data-download/module-4-2011-2016/',
        'cses5_page':'https://cses.org/data-download/cses-module-5-2016-2021/',
        'cses_imd_page':'https://cses.org/data-download/cses-integrated-module-dataset-imd/',
        'cses_variable_table':'https://cses.org/data-download/download-data-documentation/variable-table/',
        'eurobarometer_mip':'https://www.gesis.org/en/eurobarometer-data-service/overview/eb-trends-trend-files/list-of-trends/polit-issues-national',
        'manifestoberta_page':'https://manifestoproject.wzb.eu/information/documents/manifestoberta',
        'parlamint_readme':'https://raw.githubusercontent.com/clarin-eric/ParlaMint/main/README.md',
        'popbert_dataverse':'https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/HZMSUR',
    }
    run_jobs([(key, url, '.html' if 'cses' in key or key.endswith('page') else '.txt') for key, url in pages.items()])
    links = []
    for key, base in pages.items():
        if not key.startswith('cses'):
            continue
        page = RAW / (key + '.html')
        if not page.exists():
            continue
        soup = BeautifulSoup(page.read_text(errors='replace'), 'html.parser')
        for a in soup.select('a[href]'):
            url = urljoin(base, a['href'])
            if re.search(r'\.zip|\.txt|[Qq]uestionnaire|[Cc]odebook', url):
                links.append({'source': key, 'label': a.get_text(' ', strip=True), 'url': url})
    (OUT/'cses_discovered_links.json').write_text(json.dumps(links,indent=2,ensure_ascii=False)+'\n')
    jobs=[]
    for row in links:
        name=row['url'].rsplit('/',1)[-1]
        if name.endswith('_csv.zip') or name.endswith('.txt'):
            jobs.append((name.rsplit('.',1)[0],row['url'],'.'+name.rsplit('.',1)[1]))
    run_jobs(sorted(set(jobs)))
    queries = ['populism','manifesto','ParlaMint','ParlSpeech','anti-elitism','political trust']
    run_jobs([('hf_search_'+re.sub(r'[^a-z0-9]+','_',q.lower()),
               'https://huggingface.co/api/datasets?search='+requests.utils.quote(q)+'&limit=100&full=true','.json') for q in queries])
    candidates = [
        ('dataset','parisaslanidis/populism-eu-speeches'),
        ('dataset','parisaslanidis/populism-trump-2016'),
        ('dataset','siacus/manifesto'),
        ('dataset','maiammar/Manifesto_dataset'),
        ('dataset','aarabil/clcp_manifesto'),
        ('dataset','cjvt/ParlaMint3'),
        ('dataset','FrancophonIA/ParlaMint_4.1'),
        ('dataset','sstoeckl/populism-llm'),
        ('model','luerhard/PopBERT'),
        ('model','manifesto-project/manifestoberta-xlm-roberta-56policy-topics-sentence-2026-1-1'),
    ]
    run_jobs([('hf_'+kind+'_'+repo.replace('/','__'),f'https://huggingface.co/api/{kind}s/{repo}','.json') for kind,repo in candidates])
    jobs=[]
    for kind,repo in candidates:
        key='hf_'+kind+'_'+repo.replace('/','__')
        if records.get(key,{}).get('status')!=200:
            continue
        info=json.loads((RAW/(key+'.json')).read_text())
        sha=info['sha']
        prefix='datasets/' if kind=='dataset' else ''
        jobs.append((key+'_card',f'https://huggingface.co/{prefix}{repo}/resolve/{sha}/README.md','.md'))
    run_jobs(jobs)
    print('Recorded sources',len(records))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--replay-manifest',action='store_true',
                        help='Restore successful pinned acquisitions, including sources found during the audit.')
    args=parser.parse_args()
    if args.replay_manifest:
        jobs=[(key,rec['url'],Path(rec['local_path']).suffix,150_000_000,rec['sha256'])
              for key,rec in list(records.items()) if rec.get('status')==200]
        run_jobs(jobs)
    else:
        main()
