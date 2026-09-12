"""
RF09 — Busca por similaridade semântica.

Recebe uma consulta em linguagem natural, gera o embedding dela com o
mesmo modelo usado no RF08, e busca os conteúdos mais parecidos no
PostgreSQL usando o operador de distância de cosseno do pgvector.
"""
from __future__ import annotations

import logging

import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("desafio_dados")

_modelo_carregado: SentenceTransformer | None = None
_nome_modelo_carregado: str | None = None


def _conectar(cfg):
    conn = psycopg2.connect(**cfg.postgres_dsn)
    register_vector(conn)
    return conn


def _obter_modelo(nome_modelo: str) -> SentenceTransformer:
    global _modelo_carregado, _nome_modelo_carregado
    if _modelo_carregado is None or _nome_modelo_carregado != nome_modelo:
        logger.info("Carregando modelo de embeddings: %s", nome_modelo)
        _modelo_carregado = SentenceTransformer(nome_modelo)
        _nome_modelo_carregado = nome_modelo
    return _modelo_carregado


def buscar_conteudos_similares(cfg, consulta: str, top_n: int | None = None) -> list[dict]:
    """Retorna os conteúdos mais similares semanticamente à consulta,
    com posição, id, título, categoria, tipo e a similaridade/distância."""
    nome_modelo = cfg.get(
        "embeddings", "modelo",
        padrao="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    top_n = top_n or cfg.get("recomendacao", "top_n_padrao", padrao=5)

    modelo = _obter_modelo(nome_modelo)
    vetor_consulta = modelo.encode(consulta)

    conn = _conectar(cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.conteudo_id,
                    c.titulo,
                    cat.nome AS categoria,
                    c.tipo,
                    ce.embedding <=> %s AS distancia
                FROM conteudo_embedding ce
                JOIN conteudo c ON c.conteudo_id = ce.conteudo_id
                JOIN categoria cat ON cat.categoria_id = c.categoria_id
                ORDER BY distancia ASC
                LIMIT %s;
                """,
                (vetor_consulta, top_n),
            )
            linhas = cur.fetchall()
    finally:
        conn.close()

    resultados = []
    for posicao, (conteudo_id, titulo, categoria, tipo, distancia) in enumerate(linhas, start=1):
        resultados.append({
            "posicao": posicao,
            "conteudo_id": conteudo_id,
            "titulo": titulo,
            "categoria": categoria,
            "tipo": tipo,
            "distancia": float(distancia),
            "similaridade": round(1 - float(distancia), 4),
        })
    return resultados


if __name__ == "__main__":
    # Demonstração exigida pelo RF09: pelo menos 3 consultas diferentes.
    # Rodar com: python -m recomendacao.busca_semantica 
    from src.config import ConfiguracaoPipeline

    cfg = ConfiguracaoPipeline("config.json")
    consultas_demo = [
        "Quero aprender os fundamentos de banco de dados para inteligência artificial.",
        "Como criar dashboards e visualizações de dados.",
        "Boas práticas de segurança e governança de dados.",
    ]

    for consulta in consultas_demo:
        print(f"\nConsulta: {consulta}")
        for r in buscar_conteudos_similares(cfg, consulta):
            print(
                f"  {r['posicao']}. [{r['conteudo_id']}] {r['titulo']} "
                f"({r['categoria']} / {r['tipo']}) - similaridade={r['similaridade']}"
            )