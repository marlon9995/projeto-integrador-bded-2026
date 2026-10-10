"""Exporta dump PostgreSQL sem incluir senha ou proprietario externo."""
from pathlib import Path
import os, shutil, subprocess
from psycopg.conninfo import conninfo_to_dict
from src.collect import ROOT
def export():
    options=[os.environ.get('PG_BIN',''),str(ROOT/'.tools/pgsql/bin'),str(ROOT.parent/'.tools/pgsql/bin')]
    exe=next((str(Path(d)/'pg_dump.exe') for d in options if d and (Path(d)/'pg_dump.exe').exists()),None) or shutil.which('pg_dump')
    if not exe:raise RuntimeError('pg_dump ausente. Defina PG_BIN ou instale as ferramentas PostgreSQL.')
    dsn=conninfo_to_dict(os.environ.get('DATABASE_URL','host=127.0.0.1 port=55433 dbname=mobilidade user=integrador'))
    env=os.environ.copy()
    names={'host':'PGHOST','port':'PGPORT','dbname':'PGDATABASE','user':'PGUSER','password':'PGPASSWORD','sslmode':'PGSSLMODE','service':'PGSERVICE','passfile':'PGPASSFILE'}
    unsupported=set(dsn)-set(names)
    if unsupported:raise ValueError(f'Opcoes nao suportadas na exportacao: {unsupported}')
    for k,v in dsn.items():env[names[k]]=str(v)
    subprocess.run([exe,'--schema=mobilidade','--no-owner','--no-privileges','--file',str(ROOT/'sql/mobilidade_dump.sql')],env=env,check=True)
    print('Dump exportado: sql/mobilidade_dump.sql')
if __name__=='__main__':export()
