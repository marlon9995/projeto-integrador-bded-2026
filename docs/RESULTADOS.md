# Resultados e interpretação

Autor: Marlon Caldas Barbosa. Resultados obtidos por execução real com os snapshots públicos incluídos. Valores completos e previsões individuais em `reports/metrics/`.

## Seleção sem usar o teste

O treino contém 639 dias até 30/09/2012. Os 92 dias finais de 2012 foram reservados. Usaram-se cinco folds temporais de 90 dias, com treino expansivo. Os hiperparâmetros são fixos no código. Não houve ajuste posterior orientado pelo trimestre de teste.

| Modelo | RMSE médio CV | Desvio entre folds | MAE médio CV |
|---|---:|---:|---:|
| Ridge | 931,42 | 306,70 | 753,30 |
| Gradient Boosting | 1.009,77 | 309,65 | 817,96 |
| Random Forest | 1.045,91 | 357,89 | 845,84 |
| Baseline da média | 2.064,51 | 816,86 | 1.856,19 |

Selecionou-se **Ridge**, menor RMSE médio de CV. O desvio representa variação entre janelas e não intervalo de confiança. A Ridge é regularizada e consegue representar tendência temporal linear; árvores têm limitações de extrapolação. Isso ajuda a interpretar a escolha neste conjunto, sem provar uma causa única para a diferença de desempenho.

## Teste reservado

| Métrica | Ridge | Baseline média |
|---|---:|---:|
| RMSE | 1.251,43 | 2.063,12 |
| MAE | 848,98 | 1.755,02 |
| R² | 0,57496 | -0,15522 |

O modelo reduz RMSE em **39,34%** e MAE em aproximadamente **51,63%** frente à média do treino. RMSE e MAE são expressos em **viagens/dia**. R²=0,575 indica redução de erro quadrático em relação à média do próprio teste; não é accuracy, porcentagem de previsões corretas ou evidência causal.

O baseline usa exclusivamente a média histórica de treino, também recalculada em cada fold. O teste não é usado para reajustar o modelo entregue. Não se reportam métricas de todos os candidatos no teste para escolher retrospectivamente outro vencedor.

## Contribuição mensurável da NASA

Ablação na CV de treino, mantendo Ridge(alpha=10) e o mesmo desenho temporal:

- Calendário e tendência: RMSE **1.191,64**.
- Calendário, tendência e clima NASA: RMSE **931,42**.
- Redução aproximada: **21,84%**.

A integração da segunda fonte participa efetivamente da estimativa, em vez de aparecer apenas como arquivo acessório. A comparação é limitada a este dataset/desenho; não demonstra causalidade nem garante ganho em outro local.

## Erro por mês e dias difíceis

| Mês do teste | RMSE | MAE | R² |
|---|---:|---:|---:|
| Outubro/2012 | 1.000,91 | 807,09 | 0,72545 |
| Novembro/2012 | 1.064,86 | 618,41 | 0,08092 |
| Dezembro/2012 | 1.596,42 | 1.114,01 | 0,19010 |

O desempenho piora no fim do trimestre. O R² mensal depende também da variabilidade dentro de cada mês; não é comparável apenas pelo RMSE. A interpretação não deve se limitar à média global.

| Data | Real | Estimado | Erro absoluto |
|---|---:|---:|---:|
| 25/12/2012 | 1.013 | 4.785,07 | 3.772,07 |
| 22/11/2012 | 2.425 | 5.695,43 | 3.270,43 |
| 24/12/2012 | 920 | 3.965,26 | 3.045,26 |
| 23/12/2012 | 1.787 | 4.817,84 | 3.030,84 |
| 22/12/2012 | 1.749 | 4.749,41 | 3.000,41 |

O agrupamento de grandes superestimações em datas do fim do ano sugere efeitos de calendário não totalmente capturados. É uma hipótese gerada pela análise de erros, não uma conclusão causal. Não se adicionaram features escolhidas a partir dessas datas e não se retreinou para melhorar artificialmente o teste.

## Qualidade e integridade

As duas fontes apresentaram 731 datas, sem duplicatas e sem nulos nos campos usados. O ETL preservou todos os registros válidos; não inventou problemas de qualidade. As tabelas PostgreSQL foram populadas e o dataset integrado foi lido da view SQL. PK, FK e CHECKs foram testados com operações inválidas revertidas.

`reports/metrics/validacao.json` registra verificações de hashes, cronologia, uso da NASA, ausência de parcelas do alvo, scaling ajustado no treino, recarga do modelo e concordância SQL/CSV. O dump foi restaurado em outro banco, com contagens comparadas. Notebook inclui saídas reais; logs e ambiente registram versões e execução.

## Limitações e continuidade

- Dois anos e um sistema metropolitano não validam generalização para outras cidades ou para 2026.
- NASA representa um ponto em grade; os limites diários em LST não equivalem exatamente aos da agregação UCI. A junção usa datas nominais, com aproximação espacial e temporal declarada.
- O clima completo do próprio dia é retrospectivo. Para planejamento antecipado, seriam necessárias previsões meteorológicas disponíveis na decisão e novo backtest.
- Crescimento do sistema, oferta de bicicletas, eventos e calendário mais detalhado não foram integralmente representados.
- Features de calendário parcialmente redundantes são tratadas por regularização, mas não possuem interpretação causal isolada.
- Não há avaliação de equidade individual, pois o grão é agregado e não contém perfis pessoais.
- Evoluções devem ser avaliadas em uma nova janela futura, preservando o teste original. Não há promessa de desempenho produtivo nem serviço publicado.

O resultado atende ao problema de **regressão retrospectiva condicionada ao clima observado**, com evidências de coleta, integração, persistência, treinamento e avaliação.
