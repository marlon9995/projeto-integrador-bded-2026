# Procedência, atribuição e integração

Autor do projeto: **Marlon Caldas Barbosa**. Dados reais, sem geração sintética nem alterações artificiais para criar problemas de qualidade.

## Fonte 1 - UCI / Capital Bikeshare

- Fanaee-T, H. (2013). *Bike Sharing* [Dataset]. UCI Machine Learning Repository. DOI: https://doi.org/10.24432/C5W894.
- Catálogo e licença **CC BY 4.0**: https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset.
- Download: https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip.
- Arquivo utilizado: `day.csv`, 731 observações diárias de 2011–2012. `Readme.txt` original preservado para atribuição e consulta. A adaptação consiste em selecionar campos, padronizar datas e carregar tabelas relacionais.
- Origem operacional: Capital Bikeshare, Washington DC e região metropolitana, conforme documentação da UCI. O conjunto é uma agregação histórica publicada; não é conexão ao sistema operacional atual.
- `cnt` é o alvo; `casual` e `registered` são suas parcelas. Nenhuma das parcelas entra como feature. O clima já presente na UCI também não é utilizado: a informação meteorológica do modelo vem da fonte independente NASA.

## Fonte 2 - NASA POWER

- API oficial: https://power.larc.nasa.gov/docs/services/api/temporal/daily/.
- URL exata da consulta e SHA-256 em `data/raw/proveniencia.json`.
- Serviço **POWER Daily API v2.10.0**, acesso em **10/10/2026**; produtos MERRA2 e POWER, segundo o cabeçalho da resposta original.
- Ponto de referência: latitude 38,9072 e longitude -77,0369; período 01/01/2011–31/12/2012.
- Parâmetros: T2M (°C), RH2M (%), WS2M (m/s), PRECTOTCORR (mm/dia).
- Os dados foram obtidos do projeto Prediction Of Worldwide Energy Resources (POWER), NASA Langley Research Center, financiado pela NASA Earth Science Division. Atribuição e orientações: https://power.larc.nasa.gov/docs/referencing/.
- Os dados são de produto meteorológico em grade, derivado de observações/modelos, e não de sensor em cada estação de bicicletas. O arquivo original mantém cabeçalhos e metadados.

## Chave e limites da integração

Uma linha por `localidade_id=1` e `data` em cada fato. A junção SQL é **1:1**, validada para 731 datas únicas; não se repetem linhas nem se multiplicam viagens.

Washington DC é uma aproximação espacial para o sistema metropolitano agregado. NASA usa **LST (hora solar local)** neste snapshot; UCI fornece a data diária do sistema. A associação pela data nominal é uma aproximação em escala diária: não garante equivalência exata dos limites horários, especialmente com horário de verão. Isso limita a análise; não se faz alegação de correspondência por estação/hora.

O estudo estima demanda histórica condicionada a clima observado. A meteorologia completa do próprio dia só fica disponível retrospectivamente; este projeto **não é previsão antecipada de demanda**. Converter a solução para planejamento futuro exigiria previsões meteorológicas disponíveis no momento da decisão e uma nova avaliação.

Snapshots originais são mantidos para reprodução sem novas chamadas externas. `--refresh` faz nova coleta explícita, pois revisões na NASA podem alterar valores e resultados. O timestamp de proveniência é o registro local do snapshot; a data de acesso é informada separadamente, sem atribuir um horário de download não registrado.
