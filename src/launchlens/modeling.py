import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (roc_auc_score, average_precision_score, brier_score_loss,
    log_loss, precision_score, recall_score, f1_score, confusion_matrix, accuracy_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import StratifiedKFold
from .config import NUMERIC, CATEGORICAL, SEED


def preprocessing():
    return ColumnTransformer([
        ("num",Pipeline([("impute",SimpleImputer(strategy="median",keep_empty_features=True)),
                         ("scale",StandardScaler())]),NUMERIC),
        ("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),
                         ("encode",OneHotEncoder(handle_unknown="ignore",sparse_output=False))]),CATEGORICAL),
    ],remainder="drop")


def build_models():
    def pipe(model): return Pipeline([("prep",preprocessing()),("model",model)])
    return {
        "Baseline":pipe(DummyClassifier(strategy="prior")),
        "Regressao_Logistica":pipe(LogisticRegression(C=.3,max_iter=1500,random_state=SEED)),
        "Gradient_Boosting_Calibrado":CalibratedClassifierCV(
            pipe(HistGradientBoostingClassifier(max_iter=140,max_leaf_nodes=12,
                 learning_rate=.06,l2_regularization=8,random_state=SEED)),
            method="sigmoid",cv=StratifiedKFold(3,shuffle=True,random_state=SEED),ensemble=True),
    }


def evaluate(y,p,threshold=.5):
    pred=(np.asarray(p)>=threshold).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {"roc_auc":float(roc_auc_score(y,p)),"pr_auc_ap":float(average_precision_score(y,p)),
            "brier":float(brier_score_loss(y,p)),"log_loss":float(log_loss(y,p,labels=[0,1])),
            "acuracia":float(accuracy_score(y,pred)),"precisao":float(precision_score(y,pred,zero_division=0)),
            "recall":float(recall_score(y,pred,zero_division=0)),"f1":float(f1_score(y,pred,zero_division=0)),
            "tn":int(tn),"fp":int(fp),"fn":int(fn),"tp":int(tp),"n":len(y),
            "custo_relativo_por_app":float((2*fp+fn)/len(y)),"limiar":float(threshold)}


def choose_threshold(y,p):
    # Custo fictício: falso positivo=2 e falso negativo=1. Não são reais monetários.
    rows=[]
    for t in np.linspace(.05,.95,91):
        pred=np.asarray(p)>=t
        fp=int(((np.asarray(y)==0)&pred).sum());fn=int(((np.asarray(y)==1)&~pred).sum())
        rows.append({"limiar":round(float(t),2),"fp":fp,"fn":fn,"custo_relativo":(2*fp+fn)/len(y)})
    table=pd.DataFrame(rows)
    best=table.sort_values(["custo_relativo","limiar"],ascending=[True,False]).iloc[0]
    return float(best.limiar),table


def recommend(p,threshold,band=.10):
    low=max(0,threshold-band);high=min(1,threshold+band)
    return np.where(np.asarray(p)>=high,"Lancar",np.where(np.asarray(p)<low,"Adiar","Validar mais"))
