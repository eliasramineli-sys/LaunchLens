"""Processo gerador conhecido para fins didáticos; não representa o mercado real."""
import numpy as np
import pandas as pd
from scipy.special import expit
from .config import SEED, FEATURES, NUMERIC, CATEGORICAL, TARGET, RANGES, ALLOWED


def generate_features(n, seed=SEED, prefix="APP", candidates=False):
    if n < 20:
        raise ValueError("Use pelo menos 20 registros.")
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "app_id": [f"{prefix}-{i+1:05d}" for i in range(n)],
        "nome_app": [f"{prefix} Conceito {i+1:04d}" for i in range(n)],
        "data_avaliacao": pd.to_datetime(rng.integers(0, 2100, n), unit="D", origin="2020-01-01"),
        "categoria": rng.choice(ALLOWED["categoria"], n),
        "plataforma": rng.choice(ALLOWED["plataforma"], n, p=[.4,.2,.4]),
        "monetizacao": rng.choice(ALLOWED["monetizacao"], n, p=[.35,.45,.2]),
        "mercado_mil": rng.lognormal(5.5, .7, n).clip(20,2500),
        "crescimento_mercado": rng.normal(.12,.10,n).clip(-.20,.5),
        "concorrentes": rng.poisson(12,n),
        "diferenciacao": rng.beta(2.5,2,n)*10,
        "nota_beta": 1+rng.beta(4,2,n)*4,
        "retencao_beta_d7": rng.beta(3,4,n),
        "ativacao_beta": rng.beta(5,3,n),
        "intencao_pagar": rng.beta(2,5,n),
        "preco_mensal": rng.uniform(9.9,79.9,n),
        "cac_estimado": rng.lognormal(3.5,.5,n).clip(8,220),
        "custo_desenvolvimento": rng.lognormal(11.8,.55,n).clip(30000,700000),
        "marketing_mensal": rng.lognormal(8.7,.55,n).clip(1000,30000),
        "experiencia_equipe": rng.integers(0,16,n),
        "prazo_meses": rng.integers(3,19,n),
    })
    if candidates:
        df["data_avaliacao"] = pd.to_datetime("2026-10-01") + pd.to_timedelta(rng.integers(0,20,n),unit="D")
    for col in NUMERIC:
        df[col] = df[col].round(4 if col in ["crescimento_mercado","retencao_beta_d7","ativacao_beta","intencao_pagar"] else 2)
    return df


def simulate_outcomes(df, seed=SEED+1):
    rng = np.random.default_rng(seed)
    x=df
    # Demanda, execução e concorrência são hipóteses do simulador. Ruído evita alvo determinístico.
    score = (1.5*(x.retencao_beta_d7-.4) + 1.0*(x.ativacao_beta-.6)
             + 1.4*(x.intencao_pagar-.28) + .12*(x.diferenciacao-5)
             + .28*(x.nota_beta-3.5) + .7*x.crescimento_mercado
             - .035*(x.concorrentes-12) + .025*(x.experiencia_equipe-6)
             + .20*np.log(x.mercado_mil/250)
             - .17*np.log(x.cac_estimado/35) - .12*np.log(x.custo_desenvolvimento/130000)
             + .16*(x.monetizacao=="Assinatura") - .15*(x.monetizacao=="Publicidade"))
    cost = x.custo_desenvolvimento + 12*x.marketing_mensal + 12*10000
    # Receita / custo em escala log: sucesso = ROI observado >=20% em 12 meses.
    ratio = np.exp(-.10 + score + rng.normal(0,.65,len(x)))
    result=df.copy()
    result["data_desfecho"] = result.data_avaliacao + pd.DateOffset(months=12)
    result["custo_total_12m"] = cost.round(2)
    result["receita_12m"] = (cost*ratio).round(2)
    result["roi_12m"] = ((result.receita_12m-result.custo_total_12m)/result.custo_total_12m).round(6)
    result[TARGET] = (result.roi_12m>=.20).astype(int)
    return result


def generate_data(n=5000, seed=SEED):
    hist=simulate_outcomes(generate_features(n,seed),seed+1)
    candidates=generate_features(60,seed+2,prefix="NOVO",candidates=True)
    # Ausências realistas só depois de gerar os desfechos: o simulador conhece o sinal latente.
    rng=np.random.default_rng(seed+3)
    for df in [hist,candidates]:
        for c in ["nota_beta","retencao_beta_d7","intencao_pagar"]:
            df.loc[rng.random(len(df))<.02,c]=np.nan
        df["data_avaliacao"]=df.data_avaliacao.dt.strftime("%Y-%m-%d")
        if "data_desfecho" in df: df["data_desfecho"]=df.data_desfecho.dt.strftime("%Y-%m-%d")
    return hist.sort_values(["data_avaliacao","app_id"]).reset_index(drop=True), candidates


def validate_features(df):
    missing=set(FEATURES)-set(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(missing)}")
    if df.empty:
        raise ValueError("A entrada não pode estar vazia.")
    if "app_id" in df and (df.app_id.isna().any() or df.app_id.duplicated().any()):
        raise ValueError("app_id deve ser preenchido e único.")
    for c in NUMERIC:
        if not pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any():
            raise ValueError(f"{c}: informe números, sem símbolos monetários.")
        lo,hi=RANGES[c]
        present=df[c].dropna()
        if (not np.isfinite(present).all()) or ((present<lo)|(present>hi)).any():
            raise ValueError(f"{c}: valores devem estar entre {lo} e {hi}.")
    for c in CATEGORICAL:
        bad=set(df[c].dropna())-set(ALLOWED[c])
        if bad:
            raise ValueError(f"{c}: categorias desconhecidas: {sorted(bad)}")
    if df[FEATURES].isna().mean().max()>.25:
        raise ValueError("Mais de 25% de ausência em uma variável; revise a coleta.")
    return df[FEATURES].copy()


def chronological_split(df):
    if len(df)<200:
        raise ValueError("São necessários pelo menos 200 aplicativos históricos.")
    x=df.sort_values(["data_avaliacao","app_id"]).reset_index(drop=True)
    # Desfecho só fica conhecido 12 meses depois. Embargos evitam usar rótulos do futuro.
    parts=[x[x.data_avaliacao<"2022-01-01"].copy(),
           x[(x.data_avaliacao>="2023-01-01")&(x.data_avaliacao<"2024-01-01")].copy(),
           x[x.data_avaliacao>="2025-01-01"].copy()]
    if "data_desfecho" not in x:
        raise ValueError("É necessário informar data_desfecho para controlar maturação do alvo.")
    if parts[0].data_desfecho.max() >= parts[1].data_avaliacao.min() or parts[1].data_desfecho.max() >= parts[2].data_avaliacao.min():
        raise ValueError("Desfechos não estavam maduros antes da partição seguinte.")
    for p in parts:
        if len(p)<30 or p[TARGET].nunique()!=2:
            raise ValueError("Cada período deve ter ao menos 30 registros e as duas classes.")
    return parts
