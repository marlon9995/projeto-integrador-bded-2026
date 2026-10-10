"""Restaura dump em base nova e verifica equivalencia; limpa somente a base criada."""
import os,json,subprocess,uuid,shutil
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from src.collect import ROOT
from export_database import export

def verify():
    export()
    cfg=conninfo_to_dict(os.environ.get('DATABASE_URL','host=127.0.0.1 port=55433 dbname=mobilidade user=integrador'))
    target=cfg.get('dbname','mobilidade');name='p15_validacao_'+uuid.uuid4().hex[:12]
    base=dict(cfg,dbname='postgres')
    dirs=[os.environ.get('PG_BIN',''),str(ROOT/'.tools/pgsql/bin'),str(ROOT.parent/'.tools/pgsql/bin')]
    exe=next((str(Path(d)/'psql.exe') for d in dirs if d and (Path(d)/'psql.exe').exists()),None) or shutil.which('psql')
    if not exe:raise RuntimeError('psql ausente')
    with psycopg.connect(**base,autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            env=os.environ.copy()
            for k,ek in [('host','PGHOST'),('port','PGPORT'),('user','PGUSER'),('password','PGPASSWORD'),('sslmode','PGSSLMODE')]:
                if k in cfg:env[ek]=cfg[k]
            env['PGDATABASE']=name
            subprocess.run([exe,'-v','ON_ERROR_STOP=1','-f',str(ROOT/'sql/mobilidade_dump.sql')],env=env,check=True,capture_output=True,text=True)
            tables=['localidade','calendario','demanda_diaria','clima_diario','carga_fonte']
            with psycopg.connect(**cfg) as source,psycopg.connect(**dict(cfg,dbname=name)) as restored:
                counts={t:{'original':source.execute(f'SELECT count(*) FROM mobilidade.{t}').fetchone()[0],'restaurado':restored.execute(f'SELECT count(*) FROM mobilidade.{t}').fetchone()[0]} for t in tables}
                a=source.execute('SELECT * FROM mobilidade.dataset_integrado ORDER BY data').fetchall()
                b=restored.execute('SELECT * FROM mobilidade.dataset_integrado ORDER BY data').fetchall()
                assert a==b and all(v['original']==v['restaurado'] for v in counts.values())
                result={'restauracao_aprovada':True,'tabelas':counts,'dataset_sql_identico':True,'linhas_integradas':len(b)}
                (ROOT/'reports/metrics/restauracao.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
                print(json.dumps(result,indent=2))
        finally:
            # Identificador exclusivo foi criado acima; nao remove bases preexistentes.
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    return result
if __name__=='__main__':verify()
