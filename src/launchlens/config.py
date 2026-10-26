from pathlib import Path

SEED = 42
NUMERIC = ["mercado_mil", "crescimento_mercado", "concorrentes", "diferenciacao",
           "nota_beta", "retencao_beta_d7", "ativacao_beta", "intencao_pagar",
           "preco_mensal", "cac_estimado", "custo_desenvolvimento", "marketing_mensal",
           "experiencia_equipe", "prazo_meses"]
CATEGORICAL = ["categoria", "plataforma", "monetizacao"]
FEATURES = NUMERIC + CATEGORICAL
TARGET = "sucesso_12m"
CATEGORIES = ["Educacao", "Produtividade", "Saude", "Financas", "Entretenimento"]
PLATFORMS = ["Android", "iOS", "Multiplataforma"]
MONETIZATIONS = ["Assinatura", "Freemium", "Publicidade"]
# Intervalos de domínio aceitos pelo contrato de entrada, não limites aprendidos.
RANGES = {
    "mercado_mil": (1, 5000), "crescimento_mercado": (-0.5, 1),
    "concorrentes": (0, 200), "diferenciacao": (0, 10), "nota_beta": (1, 5),
    "retencao_beta_d7": (0, 1), "ativacao_beta": (0, 1), "intencao_pagar": (0, 1),
    "preco_mensal": (0, 500), "cac_estimado": (1, 1000),
    "custo_desenvolvimento": (1000, 5000000), "marketing_mensal": (100, 1000000),
    "experiencia_equipe": (0, 30), "prazo_meses": (1, 48),
}
ALLOWED = {"categoria": CATEGORIES, "plataforma": PLATFORMS, "monetizacao": MONETIZATIONS}


def project_root() -> Path:
    # CLI aceita --root; o default é o diretório do usuário, sem dependência do local instalado.
    return Path.cwd()
