# Power BI — LaunchLens

Abra `LaunchLens.pbip` no Power BI Desktop para Windows e clique em Atualizar.
Mantenha as pastas Report e SemanticModel junto ao arquivo de entrada.
O projeto usa PBIR e modelo TMSL; não foi gerado um PBIX.

Páginas: decisão dos candidatos; qualidade e risco; fatores e sensibilidade do corte.
Os dados fictícios estão embutidos no modelo, sem necessidade de configurar caminho.
Para usar os CSVs locais, altere o parâmetro opcional PastaDados para o caminho absoluto da
pasta data/processed. Deixe vazio para usar o snapshot.

Após reproduzir o experimento, execute `python scripts/build_powerbi.py` na raiz para atualizar
o snapshot. `python scripts/validate_powerbi.py` valida os esquemas oficiais e referências.
Os esquemas públicos Microsoft estão em schema_cache.json para validação offline.

As cinco tabelas possuem populações e granularidades diferentes; são independentes, sem relações
artificiais. Filtros de candidatos não afetam avaliação histórica. As métricas de teste representam
o vencedor; a comparação dos três modelos é feita na validação. Medidas em medidas.dax.

Abertura, execução M/DAX e renderização no Desktop ainda não verificadas no ambiente Linux.
Caso o Desktop exija, habilite PBIP/PBIR nas opções ou atualize a instalação.
Para obter PBIX, abra o projeto no Desktop e use Salvar como.
