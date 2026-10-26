# Resultado executivo — LaunchLens

> Estudo de portfólio com dados 100% fictícios. Não é uma validação de mercado.

## Decisão que o estudo apoia

Priorizar pesquisas e pilotos de aplicativos. O alvo é **ROI observado em 12 meses >=20%**;
a recomendação é uma política aplicada à probabilidade de sucesso, e não uma verdade observada.

## Respostas às perguntas de negócio

1. **Quais aplicativos priorizar?** Dos 60 candidatos, 15 recebem `Lancar`,
   13 recebem `Validar mais` e 32 recebem `Adiar`.
   A tabela abaixo lista os cinco maiores escores; não significa que todos passaram o corte de lançamento.
2. **Que categoria tem maior escore médio?** `Financas` nesta amostra sintética.
   Comparar também a quantidade por categoria; média de grupo pequeno não prova oportunidade real.
3. **O modelo é melhor que uma referência simples?** A tabela de comparação está em
   `data/processed/metricas_modelos.csv`. A seleção por menor Brier na validação escolheu `Regressao_Logistica`.
   Só o vencedor foi avaliado no teste final: ROC-AUC 0.805, Brier 0.180,
   PR-AUC (average precision) 0.829. São métricas do simulador, não do mercado.
4. **Quanto risco há ao classificar?** No teste: 42 falsos positivos e 152 falsos negativos;
   precisão 82.1%, recall 55.9%, no corte binário 0.68.
   Esses números descrevem a classificação binária, que é diferente da política com três decisões.
5. **Quais sinais estão associados às previsões?** Principais variáveis por permutação na validação:
   diferenciacao, retencao_beta_d7, nota_beta, intencao_pagar, ativacao_beta. Associação preditiva não comprova causa nem efeito de uma intervenção.
6. **Quanto capital está associado às propostas?** O painel soma `custo_desenvolvimento` por recomendação;
   trata-se de custo informado antes do lançamento, não lucro esperado ou orçamento otimizado.

| Aplicativo | Categoria | Probabilidade | Recomendação |
| --- | --- | --- | --- |
| NOVO-00042 | Financas | 93.3% | Lancar |
| NOVO-00038 | Financas | 92.5% | Lancar |
| NOVO-00014 | Entretenimento | 92.3% | Lancar |
| NOVO-00032 | Entretenimento | 91.5% | Lancar |
| NOVO-00003 | Produtividade | 87.7% | Lancar |

## Como a política foi definida

O corte binário minimiza `2 × FP + FN` dividido pelo número de casos na validação.
Os pesos são uma hipótese didática, sem unidade monetária. Nenhum lucro esperado é previsto.
Uma margem de 0,10 cria a revisão humana: `Lancar` se p >= 0.78;
`Adiar` se p < 0.58; demais casos recebem `Validar mais`.
A margem é uma regra de governança ilustrativa, não intervalo de confiança.
O IC bootstrap de 95% para ROC-AUC é [0.773, 0.837].
Não é um intervalo individual de probabilidade e assume independência entre aplicativos.

## Próxima decisão humana

Para um caso real, coletar evidências de demanda, custo e retenção em piloto; obter desfechos maduros;
reavaliar seleção dos aplicativos históricos, viés de sobrevivência, custos de erro e calibração.
Não converter estas recomendações sintéticas em autorização de investimento.

## Onde analisar

- `powerbi/LaunchLens.pbip`: portfólio, qualidade do modelo e fatores.
- `notebooks/01_launchlens_end_to_end.ipynb`: investigação executada e reproduzível.
- `reports/figures/`: gráficos exportados do experimento.
