"""Inferencia em CSV integrado com calendario e meteorologia observada."""
import argparse
import joblib
import pandas as pd
from .collect import ROOT
from .train import make_features,predict
def main():
    p=argparse.ArgumentParser();p.add_argument('entrada');p.add_argument('saida');a=p.parse_args()
    data=pd.read_csv(a.entrada,parse_dates=['data'])
    model=joblib.load(ROOT/'models/demanda_bicicletas.pkl')
    result=pd.DataFrame({'data':data.data,'viagens_estimadas':predict(model,make_features(data))})
    result.to_csv(a.saida,index=False)
if __name__=='__main__':main()
