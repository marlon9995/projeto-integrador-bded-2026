"""Validacao temporal, comparacao de modelos e avaliacao reservada."""
import os
from .collect import ROOT
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import joblib
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_validate
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

WEATHER=['temperatura','umidade','vento','precipitacao','temperatura_quadrado','chuva','log_precipitacao']
CATS=['dia_semana','mes','feriado','dia_util']
NUMS=['dias_desde_inicio','mes_sin','mes_cos','dia_ano_sin','dia_ano_cos','fim_de_semana']+WEATHER
def make_features(df):
    x=df.copy();dt=pd.to_datetime(x.data)
    x['dias_desde_inicio']=(dt-pd.Timestamp('2011-01-01')).dt.days
    x['mes_sin']=np.sin(2*np.pi*x.mes/12);x['mes_cos']=np.cos(2*np.pi*x.mes/12)
    x['dia_ano_sin']=np.sin(2*np.pi*(dt.dt.dayofyear-1)/365.25)
    x['dia_ano_cos']=np.cos(2*np.pi*(dt.dt.dayofyear-1)/365.25)
    x['fim_de_semana']=(x.dia_semana>=5).astype(int)
    x['temperatura_quadrado']=x.temperatura**2
    x['chuva']=np.where(x.precipitacao.isna(),np.nan,(x.precipitacao>=1).astype(float))
    x['log_precipitacao']=np.log1p(x.precipitacao)
    x[CATS]=x[CATS].astype(str)
    return x[NUMS+CATS]

def pipeline(est,weather=True):
    nums=NUMS if weather else [c for c in NUMS if c not in WEATHER]
    pre=ColumnTransformer([
        ('numericas',Pipeline([('imputacao',SimpleImputer(strategy='median')),('scaling',StandardScaler())]),nums),
        ('categoricas',Pipeline([('imputacao',SimpleImputer(strategy='most_frequent')),('encoding',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),CATS)])
    return Pipeline([('preprocessamento',pre),('regressor',est)])
def predict(model,x):return np.maximum(model.predict(x),0)
def scores(y,p):return {'rmse':float(np.sqrt(mean_squared_error(y,p))),'mae':float(mean_absolute_error(y,p)),'r2':float(r2_score(y,p))}

def train(data):
    data=data.sort_values('data').reset_index(drop=True)
    x=make_features(data);y=data.viagens
    mask=data.data<pd.Timestamp('2012-10-01');xt,xv=x[mask],x[~mask];yt,yv=y[mask],y[~mask]
    assert data.loc[mask,'data'].max()<data.loc[~mask,'data'].min()
    for name,frame in [('X_train',xt),('X_test',xv),('y_train',yt.to_frame()),('y_test',yv.to_frame())]:
        frame.assign(data=data.loc[frame.index,'data']).set_index('data').to_csv(ROOT/f'data/splits/{name}.csv')
    cv=TimeSeriesSplit(n_splits=5,test_size=90,gap=0)
    fold_docs=[]
    for i,(tr,va) in enumerate(cv.split(xt),1):
        assert tr.max()<va.min()
        fold_docs.append({'fold':i,'treino_inicio':str(data.data.iloc[tr.min()].date()),'treino_fim':str(data.data.iloc[tr.max()].date()),'validacao_inicio':str(data.data.iloc[va.min()].date()),'validacao_fim':str(data.data.iloc[va.max()].date()),'n_treino':len(tr),'n_validacao':len(va)})
    estimators={
        'Ridge':Ridge(alpha=10),
        'Random Forest':RandomForestRegressor(n_estimators=250,min_samples_leaf=3,max_features=.9,random_state=42,n_jobs=1),
        'Gradient Boosting':GradientBoostingRegressor(n_estimators=200,learning_rate=.04,max_depth=2,min_samples_leaf=8,loss='huber',random_state=42),
        'Baseline media':DummyRegressor(strategy='mean')}
    # Avaliacao consistente com inferencia: truncar contagens negativas em zero.
    def neg_rmse(est,xx,yy):return -scores(yy,predict(est,xx))['rmse']
    def neg_mae(est,xx,yy):return -scores(yy,predict(est,xx))['mae']
    comparisons=[]; models={}; folds=[]
    for name,est in estimators.items():
        pipe=pipeline(est)
        result=cross_validate(pipe,xt,yt,cv=cv,scoring={'rmse':neg_rmse,'mae':neg_mae},error_score='raise')
        comparisons.append({'modelo':name,'cv_rmse':float(-result['test_rmse'].mean()),'cv_rmse_std':float(result['test_rmse'].std()),'cv_mae':float(-result['test_mae'].mean())})
        for f,rmse,mae in zip(fold_docs,-result['test_rmse'],-result['test_mae']):folds.append(dict(f,modelo=name,rmse=float(rmse),mae=float(mae)))
        models[name]=pipe
    comparison=pd.DataFrame(comparisons).sort_values('cv_rmse');best=comparison.iloc[0].modelo
    # Escolha congelada antes de calcular metricas no teste.
    model=models[best];model.fit(xt,yt)
    preds=predict(model,xv);test=scores(yv,preds)
    baseline=models['Baseline media'];baseline.fit(xt,yt);bp=predict(baseline,xv);baseline_test=scores(yv,bp)
    ablation=pipeline(Ridge(alpha=10),weather=False)
    ab=cross_validate(ablation,xt,yt,cv=cv,scoring={'rmse':neg_rmse},error_score='raise')
    ablation_result={'ridge_calendario_cv_rmse':float(-ab['test_rmse'].mean()),'ridge_calendario_clima_cv_rmse':float(comparison[comparison.modelo=='Ridge'].cv_rmse.iloc[0]),'objetivo':'Medir contribuicao da fonte meteorologica em validacao temporal de treino; nao selecionar pelo teste.'}
    comparison.to_csv(ROOT/'reports/metrics/comparacao_cv.csv',index=False)
    pd.DataFrame(folds).to_csv(ROOT/'reports/metrics/folds.csv',index=False)
    predictions=pd.DataFrame({'data':data.loc[~mask,'data'],'real':yv,'previsto':preds,'baseline_media':bp,'residuo':yv-preds});predictions.to_csv(ROOT/'reports/metrics/predicoes_teste.csv',index=False)
    joblib.dump(model,ROOT/'models/demanda_bicicletas.pkl')
    assert np.allclose(predict(joblib.load(ROOT/'models/demanda_bicicletas.pkl'),xv),preds)
    transformed=pd.DataFrame(model.named_steps['preprocessamento'].transform(xt),columns=model.named_steps['preprocessamento'].get_feature_names_out(),index=xt.index)
    corrs=transformed.assign(viagens=yt).corr()['viagens'].drop('viagens').dropna().sort_values()
    corrs.to_csv(ROOT/'reports/metrics/correlacoes_treino.csv')
    monthly=predictions.assign(mes=predictions.data.dt.to_period('M').astype(str)).groupby('mes').apply(lambda g:pd.Series(scores(g.real,g.previsto)),include_groups=False)
    monthly.to_csv(ROOT/'reports/metrics/metricas_mensais.csv')
    result={'modelo_escolhido':best,'criterio':'Menor RMSE medio em 5 folds temporais; alvo de teste nao participa da selecao','treino':{'n':len(xt),'inicio':str(data.loc[mask,'data'].min().date()),'fim':str(data.loc[mask,'data'].max().date())},'teste':{'n':len(xv),'inicio':str(data.loc[~mask,'data'].min().date()),'fim':str(data.loc[~mask,'data'].max().date()),**test},'baseline_teste':baseline_test,'reducao_rmse_vs_baseline_pct':100*(1-test['rmse']/baseline_test['rmse']),'features_antes_encoding':len(x.columns),'features_apos_encoding':len(transformed.columns),'ablacao':ablation_result,'folds':fold_docs,'semente':42,'limiar_chuva_mm':1,'escopo':'Estimativa retrospectiva da demanda diaria condicionada ao clima observado, sem promessa de previsao antecipada.'}
    eda(data,predictions,comparison,corrs)
    return result

def fig(name):plt.tight_layout();plt.savefig(ROOT/f'reports/figures/{name}.png',dpi=150);plt.close()
def eda(data,pred,comparison,corr):
    plt.figure(figsize=(11,4));plt.plot(data.data,data.viagens,lw=.8);plt.axvline(pd.Timestamp('2012-10-01'),color='red',ls='--',label='Inicio teste');plt.title('Demanda diaria real e separacao temporal');plt.xlabel('Data');plt.ylabel('Viagens/dia');plt.legend();fig('serie_temporal')
    f,ax=plt.subplots(1,2,figsize=(10,4));ax[0].hist(data.viagens,bins=30);ax[0].set(xlabel='Viagens/dia',ylabel='Dias',title='Distribuicao do alvo');ax[1].scatter(data.temperatura,data.viagens,s=8,alpha=.5);ax[1].set(xlabel='Temperatura NASA (C)',ylabel='Viagens/dia',title='Demanda e temperatura');fig('eda_demanda')
    f,ax=plt.subplots(1,2,figsize=(10,4));data.groupby('dia_semana').viagens.mean().plot.bar(ax=ax[0]);ax[0].set(xlabel='Dia da semana (segunda=0)',ylabel='Media de viagens',title='Padrao semanal descritivo');data.assign(chuva=data.precipitacao>=1).boxplot(column='viagens',by='chuva',ax=ax[1]);ax[1].set(xlabel='Precipitacao >= 1 mm/dia',ylabel='Viagens',title='Demanda por ocorrencia de chuva');plt.suptitle('');fig('eda_calendario_clima')
    plt.figure(figsize=(10,4));plt.plot(pred.data,pred.real,label='Real');plt.plot(pred.data,pred.previsto,label='Modelo');plt.plot(pred.data,pred.baseline_media,label='Baseline media',ls='--');plt.xlabel('Data do teste');plt.ylabel('Viagens/dia');plt.legend();fig('predicoes')
    plt.figure(figsize=(8,4));plt.barh(comparison.modelo,comparison.cv_rmse,xerr=comparison.cv_rmse_std);plt.xlabel('RMSE medio CV temporal (viagens/dia)');fig('comparacao_modelos')
    f,ax=plt.subplots(1,2,figsize=(10,4));ax[0].scatter(pred.previsto,pred.residuo,s=15);ax[0].axhline(0,color='black',ls='--');ax[0].set(xlabel='Previsto',ylabel='Real - previsto',title='Residuos no teste');ax[1].hist(pred.residuo,bins=20);ax[1].set(xlabel='Real - previsto',ylabel='Dias',title='Distribuicao dos erros');fig('residuos')
    plt.figure(figsize=(9,7));corr.plot.barh();plt.xlabel('Pearson com viagens (somente treino)');fig('correlacoes')
