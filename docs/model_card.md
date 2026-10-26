# Model card — LaunchLens 1.0

| Item | Definição |
| --- | --- |
| Uso | Demonstração de ciência de dados e priorização de pesquisas/pilotos |
| População | Aplicativos fictícios avaliados antes do lançamento |
| Alvo | ROI observado em 12 meses >=20% |
| Entradas | 14 numéricas e 3 categóricas, pré-lançamento |
| Saídas | Probabilidade e política `Lancar` / `Validar mais` / `Adiar` |
| Treino | Somente partição 2020–2021 |
| Seleção | Brier na validação de 2023 |
| Teste | Casos de 2025, com desfechos maduros em 2026 |
| Resultado | `reports/resumo_resultados.json`, gerado pela execução |
| Persistência | `models/launchlens.joblib`, com modelo, features, versão e cortes |
| Responsável pelo estudo | Projeto educacional de portfólio; não há validação externa |

## Restrições de uso

Não usar para autorizar investimentos ou declarar viabilidade de um produto real. Não extrapolar o
resultado para categorias, mercados e custos fora do domínio. A tolerância do encoder a categoria
inesperada não substitui o contrato: a CLI rejeita categorias não cadastradas.

Nenhum atributo pessoal sensível foi gerado. Isso não comprova ausência de vieses em um uso real:
os dados não representam pessoas, empresas, regiões ou mercados reais. A categoria `Saude` descreve
um segmento de aplicativo e não representa validação clínica ou regulatória.

## Riscos metodológicos

O histórico contém somente lançamentos hipotéticos. Em uso real, decisões prévias e ausência de rótulos
dos produtos cancelados geram seleção. Custos estimados podem conter erros; intenções declaradas
podem não se converter em compra. Mudanças de preço/canal/concorrência podem romper a calibração.
O corte foi estimado numa única validação; não há teste externo, causal ou A/B.

## Condições para uma aplicação real

Definir sucesso com a equipe de negócio; obter base representativa e autorização de uso; registrar
datas de conhecimento dos sinais; tratar censura e maturação; separar empresas/produtos relacionados;
validar por período e por categoria; definir custo dos erros; executar piloto com revisão humana.
Monitorar ausência de dados, desvio das distribuições, Brier e precisão/recall após maturação dos rótulos.
Não retreinar automaticamente sem revisão e reavaliação temporal.

## Segurança e manutenção

Não há servidor público, autenticação, API externa nem telemetria. CSVs de exemplo não contêm dados
pessoais reais. Modelos joblib usam pickle: carregue apenas artefatos confiáveis. Reproduzir com versões
fixadas; ao atualizar scikit-learn, refaça o treinamento em vez de presumir compatibilidade de pickle.
