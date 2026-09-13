-- =====================================================================
-- Visões de apoio ao dashboard do Superset
-- =====================================================================
-- O Superset lê tabelas/visões, não os arquivos brutos. Concentrar as
-- junções aqui (em vez de repetir SQL em cada gráfico) faz com que todos
-- os gráficos compartilhem as mesmas colunas — condição para que um
-- único filtro nativo do Superset atinja o painel inteiro.
--
-- Executar depois da carga (python -m src.main):
--   psql -U postgres -h localhost -p 5432 -d desafio_dados -f sql/criar_visoes_dashboard.sql

-- Grão: uma linha por interação, enriquecida com os atributos do
-- conteúdo. É o dataset dos cartões, do gráfico de barras e do de linhas.
CREATE OR REPLACE VIEW vw_dashboard_interacoes AS
SELECT
    i.interacao_id,
    i.data_hora,
    i.tipo_interacao,
    i.tempo_consumido,
    i.percentual_conclusao,
    i.avaliacao_atribuida,
    i.usuario_id,
    c.conteudo_id,
    c.titulo,
    c.tipo              AS tipo_conteudo,
    c.nivel,
    c.autor,
    c.carga_horaria_min,
    c.data_publicacao,
    cat.nome            AS categoria
FROM interacao i
JOIN conteudo  c   ON c.conteudo_id  = i.conteudo_id
JOIN categoria cat ON cat.categoria_id = c.categoria_id;

-- Grão: uma linha por conteúdo do catálogo, inclusive os que nunca
-- receberam interação. Serve para indicadores de cobertura do catálogo.
-- Repete os nomes de coluna da visão acima de propósito: é assim que os
-- filtros nativos do Superset se aplicam aos dois datasets ao mesmo tempo.
CREATE OR REPLACE VIEW vw_dashboard_catalogo AS
SELECT
    c.conteudo_id,
    c.titulo,
    c.tipo              AS tipo_conteudo,
    c.nivel,
    c.autor,
    c.carga_horaria_min,
    c.data_publicacao,
    cat.nome            AS categoria,
    COUNT(i.interacao_id)        AS total_interacoes,
    COUNT(DISTINCT i.usuario_id) AS usuarios_alcancados,
    AVG(i.avaliacao_atribuida)   AS avaliacao_media,
    AVG(i.percentual_conclusao)  AS conclusao_media
FROM conteudo c
JOIN categoria cat ON cat.categoria_id = c.categoria_id
LEFT JOIN interacao i ON i.conteudo_id = c.conteudo_id
GROUP BY c.conteudo_id, c.titulo, c.tipo, c.nivel, c.autor,
         c.carga_horaria_min, c.data_publicacao, cat.nome;
