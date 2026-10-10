"""Clona o repositorio publico e reexecuta em banco novo e isolado."""
from pathlib import Path
import os,sys,json,subprocess,uuid,hashlib
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from src.collect import ROOT

def verify():
    cfg=conninfo_to_dict(os.environ.get('DATABASE_URL','host=127.0.0.1 port=55433 dbname=mobilidade user=integrador'))
    run_id=uuid.uuid4().hex[:12];name='p15_repro_'+run_id
    clone=ROOT/'.cache'/('repro_'+run_id);clone.parent.mkdir(exist_ok=True)
    url='https://github.com/marlon9995/projeto-integrador-bded-2026.git'
    env=os.environ.copy();env['GIT_TERMINAL_PROMPT']='0';env['GCM_INTERACTIVE']='never'
    subprocess.run(['git','clone','--quiet',url,str(clone)],env=env,check=True)
    with psycopg.connect(**dict(cfg,dbname='postgres'),autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            from psycopg.conninfo import make_conninfo
            env['DATABASE_URL']=make_conninfo(**dict(cfg,dbname=name))
            subprocess.run([sys.executable,'-m','src.run_pipeline'],cwd=clone,env=env,check=True,capture_output=True,text=True)
            comparable=['data/processed/dataset_integrado.csv','data/splits/X_train.csv','data/splits/X_test.csv','reports/metrics/comparacao_cv.csv','reports/metrics/predicoes_teste.csv','reports/metrics/resultados.json']
            checks={n:(ROOT/n).read_bytes()==(clone/n).read_bytes() for n in comparable}
            assert all(checks.values()),checks
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=clone,text=True).strip()
            result={'aprovado':True,'clone_publico_sem_autenticacao':True,'repositorio':url,'commit_validado':commit,'banco_novo_isolado':True,'artefatos_identicos':checks,'python':sys.version.split()[0]}
            (ROOT/'reports/metrics/reproducao.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps(result,indent=2));return result
        finally:
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
if __name__=='__main__':verify()
