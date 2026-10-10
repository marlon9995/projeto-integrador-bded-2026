"""Entrada unica: coleta -> ETL -> SQL -> features -> modelo -> resultados."""
from datetime import datetime, timezone
import argparse, json, logging, platform
from importlib.metadata import version
from .collect import ROOT, collect
from .etl import load
from .train import train

def write(name,value):(ROOT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
def run(refresh=False):
    for d in ['data/processed','data/splits','reports/metrics','reports/figures','logs','models','notebooks','docs']:(ROOT/d).mkdir(parents=True,exist_ok=True)
    log=logging.getLogger('mobilidade');log.setLevel(logging.INFO)
    handler=logging.FileHandler(ROOT/'logs/pipeline.log',mode='w',encoding='utf-8');handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'));log.addHandler(handler)
    start=datetime.now(timezone.utc);log.info('Inicio pipeline')
    try:
        provenance=collect(refresh);log.info('Fontes validadas: UCI e NASA POWER')
        data,audit,db=load(provenance);write('reports/metrics/etl.json',audit);write('reports/metrics/postgresql.json',db);log.info('ETL/SQL: %s',db)
        result=train(data);write('reports/metrics/resultados.json',result);log.info('Treinamento: %s',result)
        write('reports/metrics/ambiente.json',{'inicio_utc':start,'fim_utc':datetime.now(timezone.utc),'python':platform.python_version(),'plataforma':platform.platform(),'versoes':{p:version(p) for p in ['pandas','numpy','scikit-learn','psycopg','matplotlib','joblib']}})
        print(json.dumps(result,indent=2,ensure_ascii=False));return result
    except Exception:
        log.exception('Pipeline interrompido');raise
    finally:log.removeHandler(handler);handler.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true');run(p.parse_args().refresh)
