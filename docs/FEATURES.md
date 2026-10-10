# Dicionário de features

Alvo: `viagens`, contagem diária total de aluguéis, UCI `cnt`. Unidade: viagens/dia.

| Feature | Fonte / cálculo | Significado e preparação |
|---|---|---|
| dias_desde_inicio | data - 01/01/2011 | Tendência de crescimento do sistema; escala padronizada |
| mes_sin | sin(2π × mês / 12) | Sazonalidade cíclica |
| mes_cos | cos(2π × mês / 12) | Complemento da sazonalidade mensal |
| dia_ano_sin | sin(2π × (dia do ano - 1) / 365,25) | Sazonalidade anual suavizada; aproximação para anos bissextos |
| dia_ano_cos | cos(2π × (dia do ano - 1) / 365,25) | Complemento da sazonalidade anual |
| fim_de_semana | dia da semana >= 5 | Diferença de comportamento semanal |
| temperatura | NASA T2M | Temperatura média diária em °C |
| umidade | NASA RH2M | Umidade relativa diária em % |
| vento | NASA WS2M | Velocidade média do vento a 2 m em m/s |
| precipitacao | NASA PRECTOTCORR | Precipitação corrigida diária em mm/dia |
| temperatura_quadrado | temperatura² | Permite relação não linear com temperatura em regressão linear |
| chuva | precipitação >= 1 mm | Indicador de dia com chuva; mantém nulo quando precipitação ausente |
| log_precipitacao | log(1 + precipitação) | Reduz assimetria da precipitação |
| dia_semana | Data, segunda=0 … domingo=6 | One-hot, sem ordem linear artificial |
| mes | Data, 1 … 12 | One-hot; permite efeitos mensais específicos |
| feriado | UCI holiday | Indicador oficial do dataset, convertido a categoria |
| dia_util | UCI workingday | Dia útil segundo a fonte; coerência com calendário validada |

São **17 features de entrada** e **36 colunas após encoding** no treinamento final executado. As representações cíclicas e one-hot são parcialmente redundantes, assim como fim de semana/dia útil; Ridge regulariza coeficientes. Correlações individuais não medem importância causal.

Numéricas: `SimpleImputer(median)` seguido de `StandardScaler`. Categóricas: imputação pela moda e `OneHotEncoder(handle_unknown='ignore')`. Cada fold ajusta seu próprio preprocessamento somente nas datas de treino. Não há scaling ou imputação ajustados em todo o dataset.

Excluídos: `casual`, `registered`, identificadores, `cnt` como entrada e todos os campos meteorológicos da UCI. O ano bruto foi substituído por tendência temporal calculada com origem fixa. Nenhum lag ou agregação do alvo foi usado. Não se calcula média móvel com dados futuros.

As fontes já fornecem **agregações diárias**: contagem de viagens e estatísticas diárias de meteorologia. O ETL preserva esse grão. A P15 não exige criar artificialmente agregações adicionais ou alcançar um número específico de features.
