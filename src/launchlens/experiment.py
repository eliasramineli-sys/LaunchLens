"""Experimento reproduzível: treino -> seleção/limiar -> teste intocado -> candidatos."""
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_curve, ConfusionMatrixDisplay
from sklearn.calibration import calibration_curve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .config import SEED, FEATURES, TARGET
from .data import generate_data, validate_features, chronological_split
from .modeling import build_models,evaluate,choose_threshold,recommend


def json_save(path,obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")


def auc_interval(y,p,reps=500):
    rng=np.random.default_rng(SEED);scores=[]
    for _ in range(reps):
        idx=rng.integers(0,len(y),len(y));a=np.asarray(y)[idx]
        if np.unique(a).size==2:scores.append(roc_auc_score(a,np.asarray(p)[idx]))
    return [float(x) for x in np.quantile(scores,[.025,.975])]


def make_figures(test,p,threshold,importance,candidates,figdir):
    plt.rcParams.update({"figure.facecolor":"#f4f7fb","axes.facecolor":"white","axes.spines.top":False,
                         "axes.spines.right":False,"font.size":10,"axes.titleweight":"bold","savefig.dpi":160})
    fig,ax=plt.subplots(2,2,figsize=(12,8),layout="constrained")
    fpr,tpr,_=roc_curve(test[TARGET],p);ax[0,0].plot(fpr,tpr,color="#2463eb",lw=2,label=f"AUC {roc_auc_score(test[TARGET],p):.3f}")
    ax[0,0].plot([0,1],[0,1],"--",color="#a0aec0");ax[0,0].legend();ax[0,0].set(title="Discriminação | teste temporal",xlabel="Taxa de falsos positivos",ylabel="Taxa de verdadeiros positivos")
    precision,recall,_=precision_recall_curve(test[TARGET],p);ax[0,1].plot(recall,precision,color="#0c9c86",lw=2)
    ax[0,1].axhline(test[TARGET].mean(),ls="--",color="#a0aec0");ax[0,1].set(title="Precisão × recall",xlabel="Recall",ylabel="Precisão",ylim=(0,1.05))
    true,pred=calibration_curve(test[TARGET],p,n_bins=8,strategy="quantile")
    ax[1,0].plot(pred,true,"o-",color="#2463eb");ax[1,0].plot([0,1],[0,1],"--",color="#a0aec0")
    ax[1,0].set(title="Calibração | frequência observada",xlabel="Probabilidade média",ylabel="Frequência de sucesso",xlim=(0,1),ylim=(0,1))
    ConfusionMatrixDisplay.from_predictions(test[TARGET],p>=threshold,labels=[0,1],display_labels=["Insucesso","Sucesso"],ax=ax[1,1],colorbar=False,cmap="Blues")
    ax[1,1].set_title(f"Classificação binária | limiar {threshold:.2f}")
    fig.suptitle("LaunchLens • avaliação em dados SINTÉTICOS",fontsize=16);fig.savefig(figdir/"avaliacao_modelo.png");plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,6),layout="constrained")
    imp=importance.head(10).iloc[::-1]
    ax.barh(imp.variavel,imp.importancia_auc,color="#2463eb",xerr=imp.desvio_padrao)
    ax.set(title="Fatores associados às previsões | validação",xlabel="Queda de ROC-AUC ao permutar (média ± desvio)")
    fig.savefig(figdir/"fatores_modelo.png");plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(12,4.8),layout="constrained")
    order=["Lancar","Validar mais","Adiar"]
    counts=candidates.recomendacao.value_counts().reindex(order,fill_value=0)
    ax[0].bar(order,counts,color=["#0c9c86","#f1b44c","#d35465"])
    ax[0].set(title="Decisões sugeridas | 60 candidatos",ylabel="Aplicativos")
    group=candidates.groupby("categoria").prob_sucesso.mean().sort_values()
    ax[1].barh(group.index,group,color="#2463eb");ax[1].set(title="Probabilidade média por categoria",xlabel="Probabilidade estimada",xlim=(0,1))
    fig.suptitle("Simulação de portfólio • revisão humana necessária",fontsize=15)
    fig.savefig(figdir/"portfolio_candidatos.png");plt.close(fig)


def run_experiment(root):
    root=Path(root).resolve()
    for p in ["data/raw","data/processed","models","reports/figures"]:(root/p).mkdir(parents=True,exist_ok=True)
    historical,candidates=generate_data()
    historical.to_csv(root/"data/raw/historico_apps.csv",index=False)
    candidates.to_csv(root/"data/raw/candidatos_apps.csv",index=False)
    validate_features(historical);validate_features(candidates)
    train,valid,test=chronological_split(historical)
    xtr=validate_features(train);xv=validate_features(valid);xt=validate_features(test)
    models=build_models();rows=[];valid_probs={}
    for name,model in models.items():
        model.fit(xtr,train[TARGET]);vp=model.predict_proba(xv)[:,1];valid_probs[name]=vp
        rows.append({"modelo":name,"conjunto":"validacao",**evaluate(valid[TARGET],vp)})
    leaderboard=pd.DataFrame(rows).sort_values(["brier","roc_auc"],ascending=[True,False])
    winner=leaderboard.iloc[0].modelo;model=models[winner]
    threshold,sensitivity=choose_threshold(valid[TARGET],valid_probs[winner]);band=.10
    # Nenhum fit ou escolha consulta o teste. Mantemos o modelo congelado, sem retreino após validação.
    p=model.predict_proba(xt)[:,1];test_metrics=evaluate(test[TARGET],p,threshold)
    rows.append({"modelo":winner,"conjunto":"teste",**test_metrics})
    metrics=pd.DataFrame(rows)
    importance=permutation_importance(model,xv,valid[TARGET],scoring="roc_auc",n_repeats=8,random_state=SEED,n_jobs=1)
    imp=pd.DataFrame({"variavel":FEATURES,"importancia_auc":importance.importances_mean,"desvio_padrao":importance.importances_std}).sort_values("importancia_auc",ascending=False)
    candidate_scores=candidates.copy();candidate_scores["prob_sucesso"]=model.predict_proba(validate_features(candidates))[:,1]
    candidate_scores["recomendacao"]=recommend(candidate_scores.prob_sucesso,threshold,band)
    candidate_scores["limiar_binario"]=threshold;candidate_scores["limiar_adiar"]=max(0,threshold-band)
    candidate_scores["limiar_lancar"]=min(1,threshold+band)
    candidate_scores["ranking"]=candidate_scores.prob_sucesso.rank(method="first",ascending=False).astype(int)
    candidate_scores["dados_sinteticos"]="Sim"
    candidate_scores=candidate_scores.sort_values("ranking")
    scored=test.copy();scored["prob_sucesso"]=p;scored["classe_prevista"]=(p>=threshold).astype(int)
    scored["recomendacao"]=recommend(p,threshold,band)
    scored["classe_real"]=np.where(scored[TARGET]==1,"Sucesso","Insucesso")
    scored["classe_modelo"]=np.where(scored.classe_prevista==1,"Sucesso","Insucesso")
    scored["tp"]=((scored[TARGET]==1)&(scored.classe_prevista==1)).astype(int)
    scored["fp"]=((scored[TARGET]==0)&(scored.classe_prevista==1)).astype(int)
    scored["fn"]=((scored[TARGET]==1)&(scored.classe_prevista==0)).astype(int)
    scored["tn"]=((scored[TARGET]==0)&(scored.classe_prevista==0)).astype(int)
    scored["erro_brier"]=(scored.prob_sucesso-scored[TARGET])**2
    for name,frame in [("candidatos_pontuados",candidate_scores),("avaliacao_teste",scored),("metricas_modelos",metrics),("importancia_variaveis",imp),("sensibilidade_limiar",sensitivity)]:
        frame.to_csv(root/f"data/processed/{name}.csv",index=False,float_format="%.8f")
    splits=[]
    for name,part in [("treino",train),("validacao",valid),("teste",test)]:
        splits.extend({"app_id":a,"conjunto":name} for a in part.app_id)
    used={r["app_id"] for r in splits}
    splits.extend({"app_id":a,"conjunto":"embargo"} for a in historical.app_id if a not in used)
    pd.DataFrame(splits).to_csv(root/"data/processed/particoes.csv",index=False)
    joblib.dump({"model":model,"threshold":threshold,"band":band,"features":FEATURES,
                 "sklearn_version":sklearn.__version__,"synthetic_only":True},root/"models/launchlens.joblib")
    ci=auc_interval(test[TARGET],p)
    summary={"seed":SEED,"dados_sinteticos":True,"selected_model":winner,"test":test_metrics,"roc_auc_ic95_bootstrap":ci,
             "limiar_binario":threshold,"faixa_revisao":band,"limiar_lancar":min(1,threshold+band),"limiar_adiar":max(0,threshold-band),
             "particoes":{name:{"n":len(part),"inicio":part.data_avaliacao.min(),"fim":part.data_avaliacao.max(),"taxa_sucesso":float(part[TARGET].mean())} for name,part in [("treino",train),("validacao",valid),("teste",test)]},
             "n_embargo":len(historical)-len(train)-len(valid)-len(test),
             "recomendacoes":candidate_scores.recomendacao.value_counts().to_dict(),
             "melhor_categoria_media":candidate_scores.groupby("categoria").prob_sucesso.mean().idxmax(),
             "top_fatores":imp.head(5).variavel.tolist(),"versao_sklearn":sklearn.__version__}
    json_save(root/"reports/resumo_resultados.json",summary)
    manifest={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((root/"data").rglob("*.csv"))}
    json_save(root/"reports/data_sha256.json",manifest)
    make_figures(test,p,threshold,imp,candidate_scores,root/"reports/figures")
    write_business_report(root,summary,candidate_scores,imp,leaderboard)
    return summary


def write_business_report(root,s,candidates,imp,leaderboard):
    m=s["test"];counts=s["recomendacoes"]
    top=candidates.head(5)
    table="\n".join(f"| {r.app_id} | {r.categoria} | {r.prob_sucesso:.1%} | {r.recomendacao} |" for r in top.itertuples())
    text=f'''# Resultado executivo — LaunchLens

> Estudo de portfólio com dados 100% fictícios. Não é uma validação de mercado.

## Decisão que o estudo apoia

Priorizar pesquisas e pilotos de aplicativos. O alvo é **ROI observado em 12 meses >=20%**;
a recomendação é uma política aplicada à probabilidade de sucesso, e não uma verdade observada.

## Respostas às perguntas de negócio

1. **Quais aplicativos priorizar?** Dos 60 candidatos, {counts.get('Lancar',0)} recebem `Lancar`,
   {counts.get('Validar mais',0)} recebem `Validar mais` e {counts.get('Adiar',0)} recebem `Adiar`.
   A tabela abaixo lista os cinco maiores escores; não significa que todos passaram o corte de lançamento.
2. **Que categoria tem maior escore médio?** `{s['melhor_categoria_media']}` nesta amostra sintética.
   Comparar também a quantidade por categoria; média de grupo pequeno não prova oportunidade real.
3. **O modelo é melhor que uma referência simples?** A tabela de comparação está em
   `data/processed/metricas_modelos.csv`. A seleção por menor Brier na validação escolheu `{s['selected_model']}`.
   Só o vencedor foi avaliado no teste final: ROC-AUC {m['roc_auc']:.3f}, Brier {m['brier']:.3f},
   PR-AUC (average precision) {m['pr_auc_ap']:.3f}. São métricas do simulador, não do mercado.
4. **Quanto risco há ao classificar?** No teste: {m['fp']} falsos positivos e {m['fn']} falsos negativos;
   precisão {m['precisao']:.1%}, recall {m['recall']:.1%}, no corte binário {s['limiar_binario']:.2f}.
   Esses números descrevem a classificação binária, que é diferente da política com três decisões.
5. **Quais sinais estão associados às previsões?** Principais variáveis por permutação na validação:
   {', '.join(s['top_fatores'])}. Associação preditiva não comprova causa nem efeito de uma intervenção.
6. **Quanto capital está associado às propostas?** O painel soma `custo_desenvolvimento` por recomendação;
   trata-se de custo informado antes do lançamento, não lucro esperado ou orçamento otimizado.

| Aplicativo | Categoria | Probabilidade | Recomendação |
| --- | --- | --- | --- |
{table}

## Como a política foi definida

O corte binário minimiza `2 × FP + FN` dividido pelo número de casos na validação.
Os pesos são uma hipótese didática, sem unidade monetária. Nenhum lucro esperado é previsto.
Uma margem de 0,10 cria a revisão humana: `Lancar` se p >= {s['limiar_lancar']:.2f};
`Adiar` se p < {s['limiar_adiar']:.2f}; demais casos recebem `Validar mais`.
A margem é uma regra de governança ilustrativa, não intervalo de confiança.
O IC bootstrap de 95% para ROC-AUC é [{s['roc_auc_ic95_bootstrap'][0]:.3f}, {s['roc_auc_ic95_bootstrap'][1]:.3f}].
Não é um intervalo individual de probabilidade e assume independência entre aplicativos.

## Próxima decisão humana

Para um caso real, coletar evidências de demanda, custo e retenção em piloto; obter desfechos maduros;
reavaliar seleção dos aplicativos históricos, viés de sobrevivência, custos de erro e calibração.
Não converter estas recomendações sintéticas em autorização de investimento.

## Onde analisar

- `powerbi/LaunchLens.pbip`: portfólio, qualidade do modelo e fatores.
- `notebooks/01_launchlens_end_to_end.ipynb`: investigação executada e reproduzível.
- `reports/figures/`: gráficos exportados do experimento.
'''
    (root/"reports/resultado_executivo.md").write_text(text,encoding="utf-8")
