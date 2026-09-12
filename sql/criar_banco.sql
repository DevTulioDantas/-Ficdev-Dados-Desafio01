-- =====================================================================
-- Script de criação do banco relacional (PostgreSQL)
-- =====================================================================

-- Extensão necessária para armazenar embeddings.
CREATE EXTENSION IF NOT EXISTS vector;

-- Categorias temáticas dos conteúdos. 
CREATE TABLE IF NOT EXISTS categoria (
    categoria_id    SERIAL PRIMARY KEY,
    nome            VARCHAR(100) NOT NULL UNIQUE
);

-- Usuários que aparecem nas interações. Não existe uma fonte de dados
-- própria de usuário; a tabela é populada com os usuario_id distintos
-- vistos ao carregar as interações.
CREATE TABLE IF NOT EXISTS usuario (
    usuario_id      INTEGER PRIMARY KEY
);

-- Catálogo de conteúdos educacionais.
CREATE TABLE IF NOT EXISTS conteudo (
    conteudo_id         INTEGER PRIMARY KEY,
    titulo              VARCHAR(255) NOT NULL,
    tipo                VARCHAR(20) NOT NULL,
    categoria_id        INTEGER NOT NULL REFERENCES categoria(categoria_id),
    nivel               VARCHAR(20) NOT NULL,
    carga_horaria_min   INTEGER,
    data_publicacao     DATE,
    descricao           TEXT,
    autor               VARCHAR(150)
);

-- Interações dos usuários com os conteúdos (visualização, curtida,
-- conclusão, etc). A restrição UNIQUE impede que a mesma interação
-- seja gravada mais de uma vez em execuções repetidas do pipeline.
CREATE TABLE IF NOT EXISTS interacao (
    interacao_id          BIGSERIAL PRIMARY KEY,
    usuario_id            INTEGER NOT NULL REFERENCES usuario(usuario_id),
    conteudo_id           INTEGER NOT NULL REFERENCES conteudo(conteudo_id),
    tipo_interacao        VARCHAR(20) NOT NULL,
    data_hora             TIMESTAMP NOT NULL,
    tempo_consumido       INTEGER,
    percentual_conclusao  NUMERIC(5,2),
    avaliacao_atribuida   SMALLINT,
    UNIQUE (usuario_id, conteudo_id, tipo_interacao, data_hora)
);

-- Representação vetorial de cada conteúdo, usada na busca semântica.
CREATE TABLE IF NOT EXISTS conteudo_embedding (
    conteudo_id     INTEGER PRIMARY KEY REFERENCES conteudo(conteudo_id),
    embedding       VECTOR(384),
    modelo          VARCHAR(100) NOT NULL,
    texto_origem    TEXT
);

-- Recomendações geradas para cada usuário, com a pontuação e o status
-- calculados pelo motor de recomendação.
CREATE TABLE IF NOT EXISTS recomendacao (
    recomendacao_id  BIGSERIAL PRIMARY KEY,
    usuario_id       INTEGER NOT NULL REFERENCES usuario(usuario_id),
    conteudo_id      INTEGER NOT NULL REFERENCES conteudo(conteudo_id),
    pontuacao        NUMERIC(5,2) NOT NULL,
    posicao          INTEGER NOT NULL,
    status           VARCHAR(20) NOT NULL,
    data_geracao     TIMESTAMP NOT NULL DEFAULT now()
);