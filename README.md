# Projeto Integrador P15 — Demanda de bicicletas e meteorologia

**Autor:** Marlon Caldas Barbosa  
**Disciplina:** Banco de Dados e Engenharia de Dados — BDED-2026.1  
**Instituição:** UNIFAP Digital  
**Professor:** Dr. Adolfo Colares

Pipeline completo com **duas fontes reais e independentes**, PostgreSQL persistente, ETL Python, engenharia de features, regressão e avaliação temporal. O notebook final está em [notebooks/Projeto_Integrador_P15.ipynb](notebooks/Projeto_Integrador_P15.ipynb), com saídas reais de execução.

**Repositório público:** https://github.com/marlon9995/projeto-integrador-bded-2026

## Problema e escopo

Estimar a quantidade diária de viagens do Capital Bikeshare, em Washington DC e região, a partir de calendário, tendência temporal e meteorologia observada. O objetivo é estudar a demanda histórica e demonstrar a integração de fontes; **não se trata de previsão antecipada**, pois o clima completo do próprio dia é conhecido retrospectivamente.

Fonte 1: [UCI Bike Sharing](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset), contagens e calendário, licença CC BY 4.0. Fonte 2: [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/), temperatura, umidade, vento e precipitação. Ambas cobrem os 731 dias de 2011–2012. Documentação de procedência, atribuição, unidades e limitações em [docs/FONTES.md](docs/FONTES.md).

```text
UCI ZIP/CSV ──┐
              ├─> validação/ETL Python ─> tabelas PostgreSQL ─> JOIN SQL
NASA API/JSON ┘                                               │
            métricas/resultados <─ avaliação <─ modelos <─ features
```

## Reprodução do zero

Pré-requisitos: **Python 3.12**, PowerShell no Windows, acesso a downloads somente para instalar dependências/PostgreSQL ou atualizar fontes. Os snapshots originais estão incluídos; a execução padrão não depende da disponibilidade das APIs. O PostgreSQL portátil é baixado da distribuição oficial EDB quando não está disponível.

Na raiz deste repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\prepare_postgres.ps1
.\.venv\Scripts\python.exe -m src.run_pipeline
.\.venv\Scripts\python.exe validate.py
.\.venv\Scripts\python.exe export_database.py
.\.venv\Scripts\python.exe build_notebook.py
```

O último comando **reexecuta o fluxo completo**, testa o banco/modelo e grava o notebook com as novas saídas. Não é necessário executá-lo para apenas ler o notebook entregue. O script usa o mesmo interpretador que o iniciou, sem instalar kernel global. Se a política local impedir scripts PowerShell, abra o script para revisão e siga a política da máquina; o projeto não altera políticas do sistema.

`requirements.txt` lista dependências diretas; `requirements-lock.txt` registra também as transitivas instaladas no ambiente validado. Para obter o projeto via Git, antes dos comandos acima:

```text
git clone https://github.com/marlon9995/projeto-integrador-bded-2026.git
cd projeto-integrador-bded-2026
```

O log `logs/pipeline.log` corresponde à última execução e é renovado a cada rodada. As métricas também são regeneradas. Para testar a restauração do dump em uma base nova, execute `python verify_restore.py` com o mesmo ambiente; esse teste exige permissão de criação de banco e remove somente a base exclusiva criada por ele.

A reprodução foi verificada por clone público sem autenticação, ambiente Python instalado separadamente e base vazia: dataset integrado, splits e resultados ficaram idênticos. Evidência em `reports/metrics/reproducao.json`, com commit validado. O comando `python verify_reproduction.py` repete esse teste; exige Git, rede e permissão de criar banco. A base exclusiva do teste é removida; a cópia do clone fica em `.cache`, fora do versionamento.

`prepare_postgres.ps1` cria banco **mobilidade**, porta **55433**, cluster persistente em `runtime/pgdata`. Usa autenticação integrada **SSPI** com a conta Windows que criou o cluster; não grava senha e não instala serviço do Windows. A pasta `runtime` é local e não é versionada. O banco não é descartado após execução. Para parar o servidor preservando os dados:

```powershell
.\prepare_postgres.ps1 -Stop
```

Para iniciar novamente, execute o mesmo script sem `-Stop`. Não há autoinicialização ao ligar o computador.

### PostgreSQL já instalado ou outro sistema operacional

Crie um banco de desenvolvimento dedicado e configure a conexão por variável de ambiente `DATABASE_URL` no formato aceito por psycopg. Exemplo sem senha embutida:

```powershell
$env:DATABASE_URL='host=127.0.0.1 port=5432 dbname=mobilidade user=seu_usuario'
```

O exemplo requer substituir o usuário pela conta existente e configurar autenticação local/arquivo de senhas de modo apropriado. Não coloque credenciais no Git. Em Linux/macOS use `python3 -m venv .venv` e `.venv/bin/python` nos comandos, com PostgreSQL configurado. A execução validada foi no Windows; outras plataformas não foram testadas.

O usuário do banco deve poder criar schema/tabelas no banco dedicado. Não aponte para produção. O ETL reexecutável substitui apenas fatos da localidade 1 no schema `mobilidade`, em transação. Não remove schemas nem tabelas de outros projetos. Modelagem, grão, chaves e limites em [docs/MODELAGEM.md](docs/MODELAGEM.md).

### Coletar novamente das duas fontes

```powershell
.\.venv\Scripts\python.exe -m src.run_pipeline --refresh
```

Sem `--refresh`, as fontes são lidas dos snapshots e seus hashes são conferidos. Uma alteração manual do snapshot interrompe a execução. Nova coleta pode produzir dados diferentes por revisão do provedor; os resultados então devem ser regenerados e documentados. O ZIP UCI, o JSON NASA e seus metadados originais estão em `data/raw`.

## Tratamento e features

Não foram criados dados sintéticos. As fontes recebidas não têm nulos ou duplicatas nas datas e não precisaram de remoções. O ETL valida cobertura, datas, domínios meteorológicos e soma das parcelas do alvo. Erros estruturais interrompem a carga; sentinelas meteorológicas viram nulos. A imputação fica dentro do treinamento, sem estimar parâmetros no teste.

São 17 features antes e 36 após encoding: calendário, tendência, sazonalidade cíclica, meteorologia e transformações. Dicionário em [docs/FEATURES.md](docs/FEATURES.md). As parcelas `casual`/`registered` e o clima da própria UCI foram excluídos dos preditores. O conjunto integrado usado no ML é **lido do PostgreSQL via SQL**, e não unido diretamente em memória contornando o banco.

## Validação e resultados

- Treino: 01/01/2011–30/09/2012, **639 dias**.
- Teste reservado: 01/10/2012–31/12/2012, **92 dias**.
- Cinco folds temporais, treino expansivo, 90 dias de validação por fold, sem embaralhamento.
- Seleção pelo menor RMSE médio na CV de treino, antes de avaliar o teste.
- Ridge, Random Forest, Gradient Boosting e baseline da média histórica. Hiperparâmetros fixos, sem busca orientada pelo teste.
- Imputação, scaling e encoding são ajustados dentro de cada fold. Estimativas negativas são truncadas a zero, tanto na CV quanto na inferência.

| Resultado no teste | Ridge selecionado | Baseline média |
|---|---:|---:|
| RMSE (viagens/dia) | 1.251,43 | 2.063,12 |
| MAE (viagens/dia) | 848,98 | 1.755,02 |
| R² | 0,5750 | -0,1552 |

Redução de RMSE de **39,34%** frente ao baseline. Na ablação em CV, o RMSE da Ridge passou de **1.191,64**, com calendário, para **931,42**, com calendário+clima. Isso evidencia uma contribuição mensurável da segunda fonte neste desenho experimental.

Análise de erros, variação mensal e limitações em [docs/RESULTADOS.md](docs/RESULTADOS.md). RMSE/MAE/R² são métricas de regressão; accuracy/F1 não se aplicam ao alvo de contagem deste projeto.

## Estrutura

```text
src/                  coleta, ETL/SQL, features, treinamento e inferência
sql/schema.sql        tabelas, constraints e view de integração
sql/mobilidade_dump.sql dump PostgreSQL real, sem proprietário/senha
data/raw/             snapshots públicos e proveniência
data/processed/       tabelas tratadas e dataset lido da view SQL
data/splits/          X_train, X_test, y_train, y_test (índice data)
models/               pipeline .pkl com preprocessamento e regressor
notebooks/            notebook final executado
reports/figures/      EDA, correlações, CV, previsões e resíduos
reports/metrics/      auditoria, resultados, folds e verificações
logs/                 logs reais de execução
docs/                 fontes, modelagem, features e resultados
```

Nos splits, `data` é índice de alinhamento e não preditor. Leia com `pd.read_csv(..., index_col='data')`. O `.pkl` deve ser carregado apenas de origem confiável, com versões compatíveis.

## Inferência e restauração

Um CSV de entrada para inferência deve seguir o schema de `data/processed/dataset_integrado.csv`; o alvo `viagens` é opcional e ignorado no cálculo de features. Os campos de calendário e clima precisam estar preenchidos no formato do dataset. Execute:

```powershell
.\.venv\Scripts\python.exe -m src.predict data/processed/dataset_integrado.csv reports/metrics/inferencia.csv
```

Para restaurar em **outro banco vazio**, usando `psql` do seu PostgreSQL:

```text
psql --dbname=NOME_DO_BANCO_VAZIO -v ON_ERROR_STOP=1 -f sql/mobilidade_dump.sql
```

O dump contém schema, dados e constraints; não restaure sobre um schema `mobilidade` já existente. A restauração foi testada em banco separado e suas contagens comparadas. Para exportar novamente, `export_database.py` procura `pg_dump` no PATH, na instalação portátil ou em `PG_BIN`. Credenciais de uma conexão alternativa são transmitidas por variáveis de ambiente, não incluídas no comando/dump.

## Git e entrega no Moodle

O projeto deve ficar em repositório Git acessível ao avaliador. Versione código, snapshots públicos, notebook, documentação, métricas, modelo e SQL. Não envie `runtime`, `.tools`, `.venv`, caches ou `.env`. O `.gitignore` já exclui esses itens.

Uma cópia ZIP de segurança pode ser gerada com `python package_project.py`. O script empacota somente arquivos versionados, cria manifesto SHA-256 e verifica a integridade do ZIP em `dist/Projeto_Integrador_P15.zip`. A pasta `dist` não é versionada.

No Moodle, informe o **link do repositório** e anexe **notebooks/Projeto_Integrador_P15.ipynb**. O ZIP é somente uma cópia de segurança; não substitui o link e o notebook exigidos.

## Critérios P15

| Exigência | Evidência |
|---|---|
| Duas ou mais fontes | `src/collect.py`, snapshots e `docs/FONTES.md` |
| PostgreSQL modelado | `sql/schema.sql`, `docs/MODELAGEM.md`, métricas SQL |
| ETL Python | `src/etl.py`, logs e auditoria |
| Features documentadas | `src/train.py`, `docs/FEATURES.md` |
| Modelo e avaliação | pipeline .pkl, CV temporal e métricas de teste |
| EDA e interpretação | notebook, figuras e `docs/RESULTADOS.md` |
| Organização/reprodução | README, requirements, scripts e histórico Git |

Código e documentação originais sob MIT; dados externos mantêm suas atribuições próprias. Consulte LICENSE e docs/FONTES.md.
