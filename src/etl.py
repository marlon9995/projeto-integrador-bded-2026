"""Transforma fontes, carrega tabelas e le o dataset integrado via SQL."""
from pathlib import Path
import json, os
import numpy as np
import pandas as pd
import psycopg
from .collect import ROOT

def connect():
    return psycopg.connect(os.environ.get('DATABASE_URL','host=127.0.0.1 port=55433 dbname=mobilidade user=integrador'))
def transform():
    raw=ROOT/'data/raw'; b=pd.read_csv(raw/'day.csv');j=json.loads((raw/'nasa_power.json').read_text())
    initial={'bicicletas':{'linhas':len(b),'duplicatas_data':int(b.dteday.duplicated().sum()),'nulos':int(b.isna().sum().sum())}}
    b['data']=pd.to_datetime(b.dteday,errors='coerce')
    if b.data.isna().any() or b.data.duplicated().any():raise ValueError('Datas invalidas/duplicadas na UCI')
    if not (b['cnt']==b.casual+b.registered).all():raise ValueError('Contagens inconsistentes')
    if (b[['cnt','casual','registered']]<0).any().any():raise ValueError('Contagem negativa')
    dates=pd.date_range('2011-01-01','2012-12-31')
    if set(b.data)!=set(dates):raise ValueError('Cobertura UCI inesperada')
    w=pd.DataFrame(j['properties']['parameter']);w.index=pd.to_datetime(w.index,format='%Y%m%d');w=w.rename(columns={'T2M':'temperatura','RH2M':'umidade','WS2M':'vento','PRECTOTCORR':'precipitacao'}).rename_axis('data').reset_index()
    sentinels=int((w.select_dtypes('number')==j['header']['fill_value']).sum().sum())
    w=w.replace(j['header']['fill_value'],np.nan)
    for c,low,high in [('temperatura',-90,65),('umidade',0,100),('vento',0,150),('precipitacao',0,2000)]:
        w.loc[~w[c].between(low,high),c]=np.nan
    if w.data.duplicated().any() or set(w.data)!=set(dates):raise ValueError('Cobertura NASA inesperada')
    initial['clima']={'linhas':len(w),'sentinelas':sentinels,'nulos_apos_validacao':int(w.isna().sum().sum()),'duplicatas_data':int(w.data.duplicated().sum())}
    # Nao forcar remocoes: dados reais validos sao preservados. Imputacao fica no treino.
    cal=pd.DataFrame({'data':b.data,'ano':b.data.dt.year,'mes':b.data.dt.month,'dia_semana':b.data.dt.dayofweek,'feriado':b.holiday.astype(bool),'dia_util':b.workingday.astype(bool)})
    if not (cal.dia_util==((cal.dia_semana<5)&~cal.feriado)).all():raise ValueError('Calendario incoerente')
    demand=pd.DataFrame({'localidade_id':1,'data':b.data,'viagens':b.cnt,'casuais':b.casual,'cadastrados':b.registered})
    w.insert(0,'localidade_id',1)
    audit={'antes':initial,'depois':{'calendario':len(cal),'demanda':len(demand),'clima':len(w)},'linhas_removidas':0,'politica':'Datas e contagens invalidas interrompem ETL; clima invalido vira nulo; imputacao por mediana exclusivamente no treino.'}
    return cal,demand,w,audit

def load(manifest):
    cal,demand,weather,audit=transform()
    with connect() as conn:
        conn.execute((ROOT/'sql/schema.sql').read_text())
        conn.execute("INSERT INTO mobilidade.localidade VALUES (1,'Washington DC / Capital Bikeshare',38.9072,-77.0369) ON CONFLICT(localidade_id) DO UPDATE SET nome=EXCLUDED.nome,latitude=EXCLUDED.latitude,longitude=EXCLUDED.longitude")
        # Escopo fixo, transacao atomica; nao toca em tabelas de outros projetos.
        for table in ['demanda_diaria','clima_diario']:conn.execute(f'DELETE FROM mobilidade.{table} WHERE localidade_id=1')
        cols=','.join(cal.columns)
        with conn.cursor() as cur:
            for row in cal.itertuples(index=False,name=None):
                cur.execute(f'INSERT INTO mobilidade.calendario({cols}) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(data) DO UPDATE SET ano=EXCLUDED.ano,mes=EXCLUDED.mes,dia_semana=EXCLUDED.dia_semana,feriado=EXCLUDED.feriado,dia_util=EXCLUDED.dia_util',row)
        for table,frame in [('demanda_diaria',demand),('clima_diario',weather)]:
            with conn.cursor().copy(f'COPY mobilidade.{table} ({",".join(frame.columns)}) FROM STDIN') as cp:
                for row in frame.itertuples(index=False,name=None):cp.write_row(tuple(None if pd.isna(x) else x for x in row))
        for name,key in [('uci','bike_sharing.zip'),('nasa','nasa_power.json')]:
            m=manifest[key]
            conn.execute('INSERT INTO mobilidade.carga_fonte(fonte,url,sha256,linhas) VALUES (%s,%s,%s,731) ON CONFLICT(fonte) DO UPDATE SET url=EXCLUDED.url,sha256=EXCLUDED.sha256,linhas=EXCLUDED.linhas,carregado_em=CURRENT_TIMESTAMP',(name,m['url'],m['sha256']))
        cur=conn.execute('SELECT * FROM mobilidade.dataset_integrado ORDER BY data'); data=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description]);data['data']=pd.to_datetime(data.data)
        checks={t:conn.execute(f'SELECT count(*) FROM mobilidade.{t}').fetchone()[0] for t in ['localidade','calendario','demanda_diaria','clima_diario','carga_fonte']}
        checks.update({'join_linhas':len(data),'datas_unicas':int(data.data.nunique()),'soma_viagens_sql':int(conn.execute('SELECT sum(viagens) FROM mobilidade.dataset_integrado').fetchone()[0]),'versao_postgresql':conn.execute('SELECT version()').fetchone()[0]})
    assert len(data)==731 and data.data.nunique()==731
    assert checks['soma_viagens_sql']==int(demand.viagens.sum())
    (ROOT/'data/processed').mkdir(parents=True,exist_ok=True)
    data.to_csv(ROOT/'data/processed/dataset_integrado.csv',index=False)
    for name,frame in [('calendario',cal),('demanda_diaria',demand),('clima_diario',weather)]:frame.to_csv(ROOT/f'data/processed/{name}.csv',index=False)
    return data,audit,checks
