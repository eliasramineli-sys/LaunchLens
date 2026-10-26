# Perguntas de negócio e critérios de aceite

**Patrocinador hipotético:** equipe de produto que decide quais conceitos avançam para um piloto.
A decisão final pertence à equipe humana; o escore serve para organizar evidências.

| Pergunta | Cálculo ou evidência | Ação apoiada | Limitação |
| --- | --- | --- | --- |
| Qual conceito priorizar? | Ranking de probabilidade | Selecionar investigações e pilotos | Não comprova demanda real |
| Que categorias têm maior potencial? | Média do escore e quantidade por categoria | Comparar carteira | Não é estimativa causal de mercado |
| Quanto capital está associado às propostas? | Soma de custo de desenvolvimento | Dimensionar exposição informada | Não otimiza orçamento nem prevê lucro |
| Quanto confiar no modelo? | Brier, AUC, calibração e baseline | Aceitar ou rejeitar apoio automatizado | Apenas em dados sintéticos |
| Qual erro é mais relevante? | FP/FN e custo relativo | Definir tolerância ao risco | Pesos hipotéticos precisam de validação |
| Que sinais estão associados ao escore? | Permutação na validação | Investigar coleta e hipóteses | Não garante efeito de uma mudança |
| Onde solicitar mais evidências? | Faixa `Validar mais` | Direcionar pesquisa ou beta | Faixa não é intervalo estatístico |

## Critérios de conclusão desta entrega

- Gerador, treinamento e previsão executam com comandos documentados.
- Dados fictícios claramente identificados; candidatos não recebem rótulos inventados.
- Nenhum desfecho futuro entra como feature; teste não escolhe modelo ou corte.
- Notebook contém saídas reais e não depende de caminhos absolutos.
- Projeto Power BI inclui relatório, modelo e dados de demonstração; validação Desktop fica explícita.
- Resultados de negócio são gerados a partir dos CSVs, sem números manuais na documentação executiva.
- Testes exercitam contratos de entrada, maturação temporal, política e fluxo integrado.
