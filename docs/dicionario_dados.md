# Dicionário de dados

Dados fictícios; taxas em fração 0–1, valores monetários em BRL, mercado em milhares de pessoas.

| Variável | Domínio |
| --- | --- |
| mercado_mil | 1 a 5000 |
| crescimento_mercado | -0.5 a 1 |
| concorrentes | 0 a 200 |
| diferenciacao | 0 a 10 |
| nota_beta | 1 a 5 |
| retencao_beta_d7 | 0 a 1 |
| ativacao_beta | 0 a 1 |
| intencao_pagar | 0 a 1 |
| preco_mensal | 0 a 500 |
| cac_estimado | 1 a 1000 |
| custo_desenvolvimento | 1000 a 5000000 |
| marketing_mensal | 100 a 1000000 |
| experiencia_equipe | 0 a 30 |
| prazo_meses | 1 a 48 |
| categoria | Educacao, Produtividade, Saude, Financas, Entretenimento |
| plataforma | Android, iOS, Multiplataforma |
| monetizacao | Assinatura, Freemium, Publicidade |

`app_id`: identificador único; `nome_app`: nome fictício; `data_avaliacao`: data de decisão; `data_desfecho`: disponibilidade do resultado 12 meses depois. `receita_12m`, `custo_total_12m`, `roi_12m` e `sucesso_12m` são desfechos excluídos das features. Candidatos não têm desfecho. Retenção D7 é fração de usuários retidos no beta; ativação é fração que conclui a primeira ação; intenção de pagar é fração de respostas positivas. Nota beta: 1–5; diferenciação: 0–10; experiência: anos; prazo: meses.
