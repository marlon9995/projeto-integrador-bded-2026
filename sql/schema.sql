CREATE SCHEMA IF NOT EXISTS mobilidade;
CREATE TABLE IF NOT EXISTS mobilidade.localidade (
    localidade_id SMALLINT PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    latitude DOUBLE PRECISION NOT NULL CHECK(latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK(longitude BETWEEN -180 AND 180)
);
CREATE TABLE IF NOT EXISTS mobilidade.calendario (
    data DATE PRIMARY KEY,
    ano SMALLINT NOT NULL,
    mes SMALLINT NOT NULL CHECK(mes BETWEEN 1 AND 12),
    dia_semana SMALLINT NOT NULL CHECK(dia_semana BETWEEN 0 AND 6),
    feriado BOOLEAN NOT NULL,
    dia_util BOOLEAN NOT NULL
);
CREATE TABLE IF NOT EXISTS mobilidade.demanda_diaria (
    localidade_id SMALLINT NOT NULL REFERENCES mobilidade.localidade,
    data DATE NOT NULL REFERENCES mobilidade.calendario,
    viagens INTEGER NOT NULL CHECK(viagens >= 0),
    casuais INTEGER NOT NULL CHECK(casuais >= 0),
    cadastrados INTEGER NOT NULL CHECK(cadastrados >= 0),
    PRIMARY KEY(localidade_id, data),
    CHECK(viagens = casuais + cadastrados)
);
CREATE TABLE IF NOT EXISTS mobilidade.clima_diario (
    localidade_id SMALLINT NOT NULL REFERENCES mobilidade.localidade,
    data DATE NOT NULL REFERENCES mobilidade.calendario,
    temperatura DOUBLE PRECISION CHECK(temperatura BETWEEN -90 AND 65),
    umidade DOUBLE PRECISION CHECK(umidade BETWEEN 0 AND 100),
    vento DOUBLE PRECISION CHECK(vento >= 0),
    precipitacao DOUBLE PRECISION CHECK(precipitacao >= 0),
    PRIMARY KEY(localidade_id,data)
);
CREATE TABLE IF NOT EXISTS mobilidade.carga_fonte (
    fonte TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    linhas INTEGER NOT NULL CHECK(linhas > 0),
    carregado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE OR REPLACE VIEW mobilidade.dataset_integrado AS
SELECT d.data, d.viagens, c.feriado, c.dia_util, c.ano, c.mes, c.dia_semana,
       w.temperatura, w.umidade, w.vento, w.precipitacao
FROM mobilidade.demanda_diaria d
JOIN mobilidade.calendario c USING(data)
JOIN mobilidade.clima_diario w USING(localidade_id,data)
WHERE d.localidade_id = 1;
