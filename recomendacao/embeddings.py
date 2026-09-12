"""
RF08 — Geração e armazenamento de embeddings.

Gera um embedding por conteúdo a partir da concatenação de título e
descrição, com o modelo
configurado em config.json (embeddings.modelo). Evita gerar de novo
para conteúdos que já têm embedding salvo, apenas busca no banco os que
ainda não têm.
"""
from __future__ import annotations

import logging

import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("desafio_dados")

# Como o modelo é pesado pra carregar guardamos aqui pra não recarregar a
# cada chamada dentro da mesma execução do pipeline.
_modelo_carregado: SentenceTransformer | None = None
_nome_modelo_carregado: str | None = None


def _conectar(cfg):
    conn = psycopg2.connect(**cfg.postgres_dsn)
    register_vector(conn)  # permite inserir listas/arrays direto na coluna vector
    return conn


def _obter_modelo(nome_modelo: str) -> SentenceTransformer:
    global _modelo_carregado, _nome_modelo_carregado
    if _modelo_carregado is None or _nome_modelo_carregado != nome_modelo:
        logger.info("Carregando modelo de embeddings: %s", nome_modelo)
        _modelo_carregado = SentenceTransformer(nome_modelo)
        _nome_modelo_carregado = nome_modelo
    return _modelo_carregado


def _buscar_conteudos_sem_embedding(cur) -> list[tuple[int, str, str]]:
    """Retorna (conteudo_id, titulo, descricao) só dos conteúdos que
    ainda não têm embedding salvo."""
    cur.execute(
        """
        SELECT c.conteudo_id, c.titulo, c.descricao
        FROM conteudo c
        LEFT JOIN conteudo_embedding ce ON ce.conteudo_id = c.conteudo_id
        WHERE ce.conteudo_id IS NULL;
        """
    )
    return cur.fetchall()


def gerar_embeddings(cfg) -> dict:
    """Gera e salva embeddings pros conteúdos pendentes. Retorna a
    contagem de embeddings gerados nesta execução."""
    nome_modelo = cfg.get(
        "embeddings", "modelo",
        padrao="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    modelo = _obter_modelo(nome_modelo)

    conn = _conectar(cfg)
    try:
        with conn:
            with conn.cursor() as cur:
                pendentes = _buscar_conteudos_sem_embedding(cur)

                if not pendentes:
                    logger.info("Nenhum conteúdo pendente de embedding.")
                    return {"gerados": 0}

                textos = [f"{titulo}. {descricao}" for _, titulo, descricao in pendentes]
                vetores = modelo.encode(textos, show_progress_bar=False)

                for (conteudo_id, _, _), texto, vetor in zip(pendentes, textos, vetores):
                    cur.execute(
                        """
                        INSERT INTO conteudo_embedding (conteudo_id, embedding, modelo, texto_origem)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (conteudo_id) DO NOTHING;
                        """,
                        (conteudo_id, vetor, nome_modelo, texto),
                    )

        logger.info("Embeddings gerados: %d.", len(pendentes))
        return {"gerados": len(pendentes)}
    finally:
        conn.close()