"""Coleta duas fontes independentes e registra procedencia e hashes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, urllib.request, zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
    'bike_sharing.zip':'https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip',
    'nasa_power.json':'https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,RH2M,WS2M,PRECTOTCORR&community=RE&longitude=-77.0369&latitude=38.9072&start=20110101&end=20121231&format=JSON'
}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def collect(refresh=False):
    raw=ROOT/'data/raw';raw.mkdir(parents=True,exist_ok=True)
    mp=raw/'proveniencia.json'
    old=json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else {}
    manifest={}
    for name,url in SOURCES.items():
        path=raw/name
        if refresh or not path.exists():
            req=urllib.request.Request(url,headers={'User-Agent':'ProjetoIntegrador-Mobilidade/1.0'})
            with urllib.request.urlopen(req,timeout=180) as r:content=r.read()
            path.write_bytes(content)
            old.pop(name,None)
        digest=sha(path)
        if name in old and old[name]['sha256']!=digest and not refresh:
            raise ValueError(f'Snapshot alterado: {name}. Use --refresh somente para nova coleta intencional.')
        manifest[name]={'url':url,'sha256':digest,'bytes':path.stat().st_size,
            'registrado_em_utc':old.get(name,{}).get('registrado_em_utc',datetime.now(timezone.utc).isoformat()),
            'nota':'Data de registro do snapshot local; as fontes foram coletadas em 10/10/2026.'}
    with zipfile.ZipFile(raw/'bike_sharing.zip') as z:
        for name in ['day.csv','Readme.txt']:(raw/name).write_bytes(z.read(name))
    manifest['day.csv']={'arquivo_pai':'bike_sharing.zip','sha256':sha(raw/'day.csv'),'bytes':(raw/'day.csv').stat().st_size}
    mp.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    return manifest
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true');print(json.dumps(collect(p.parse_args().refresh),indent=2))
