"""Verificacoes de integridade, isolamento temporal e persistencia real."""
import json, hashlib
import numpy as np
import pandas as pd
import joblib, psycopg
from src.collect import ROOT,sha
from src.etl import connect
from src.train import make_features,predict,NUMS,CATS

def validate():
    checks={}
    provenance=json.loads((ROOT/'data/raw/proveniencia.json').read_text(encoding='utf-8'))
    checks['snapshots_sha256']=all(sha(ROOT/'data/raw'/n)==m['sha256'] for n,m in provenance.items())
    df=pd.read_csv(ROOT/'data/processed/dataset_integrado.csv',parse_dates=['data'])
    xt=pd.read_csv(ROOT/'data/splits/X_train.csv',index_col='data');xv=pd.read_csv(ROOT/'data/splits/X_test.csv',index_col='data')
    # Preservar representacao categorica usada no ajuste.
    for x in [xt,xv]:x[CATS]=x[CATS].astype(str)
    dates_train=pd.to_datetime(xt.index);dates_test=pd.to_datetime(xv.index)
    checks['split_temporal_sem_sobreposicao']=bool(dates_train.max()<dates_test.min() and set(dates_train).isdisjoint(dates_test))
    checks['features_sem_alvo_ou_parcelas']=not bool(set(xt.columns)&{'viagens','cnt','casual','registered','casuais','cadastrados','instant'})
    checks['join_um_para_um']=len(df)==731 and df.data.nunique()==731
    model=joblib.load(ROOT/'models/demanda_bicicletas.pkl')
    expected=pd.read_csv(ROOT/'reports/metrics/predicoes_teste.csv')
    checks['modelo_recarregado_mesmas_predicoes']=bool(np.allclose(predict(model,xv),expected.previsto))
    numeric=model.named_steps['preprocessamento'].named_transformers_['numericas']
    imputed=numeric.named_steps['imputacao'].transform(xt[NUMS])
    checks['scaling_ajustado_somente_treino']=bool(np.allclose(numeric.named_steps['scaling'].mean_,imputed.mean(axis=0)))
    checks['nasa_efetivamente_utilizada']=all(c in model.named_steps['preprocessamento'].feature_names_in_ for c in ['temperatura','umidade','vento','precipitacao'])
    x_without_target=make_features(df.drop(columns=['viagens']))
    checks['features_independem_do_alvo']=list(x_without_target.columns)==list(xt.columns)
    with connect() as conn:
        n,s=conn.execute('SELECT count(*), sum(viagens) FROM mobilidade.dataset_integrado').fetchone()
        checks['sql_confere_csv']=n==len(df) and s==int(df.viagens.sum())
        trials={
            'pk_impede_duplicata':('INSERT INTO mobilidade.demanda_diaria SELECT * FROM mobilidade.demanda_diaria LIMIT 1',psycopg.errors.UniqueViolation),
            'check_impede_contagem_incoerente':("UPDATE mobilidade.demanda_diaria SET viagens=viagens+1 WHERE data='2011-01-01'",psycopg.errors.CheckViolation),
            'fk_impede_localidade_orfa':("INSERT INTO mobilidade.clima_diario(localidade_id,data) VALUES(32767,'2011-01-01')",psycopg.errors.ForeignKeyViolation)}
        for name,(sql,error) in trials.items():
            checks[name]=False
            try:
                with conn.transaction():conn.execute(sql)
            except error:checks[name]=True
        conn.rollback()
    result={'aprovado':all(checks.values()),'verificacoes':checks}
    (ROOT/'reports/metrics/validacao.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not result['aprovado']:raise AssertionError(result)
    print(json.dumps(result,indent=2));return result
if __name__=='__main__':validate()
