"""
RF07 — Persistência no MongoDB.

Carrega os comentários/avaliações já tratados (RF04) na coleção
configurada em mongodb.colecao_comentarios (config.json). Um índice
único evita duplicar o mesmo comentário em execuções repetidas do
pipeline.
"""
from __future__ import annotations

import logging

from pymongo import ASCENDING, MongoClient

logger = logging.getLogger("desafio_dados")


def _conectar(cfg):
    client = MongoClient(cfg.mongodb_uri)
    return client, client[cfg.mongodb_db]


def _nome_colecao(cfg) -> str:
    return cfg.get("mongodb", "colecao_comentarios", padrao="comentarios_avaliacoes")


def _garantir_indices(colecao) -> None:
    """Cria os índices usados pelas consultas obrigatórias do RF07."""
    colecao.create_index(
        [
            ("usuario_id", ASCENDING),
            ("conteudo_id", ASCENDING),
            ("data", ASCENDING),
            ("comentario", ASCENDING),
        ],
        unique=True,
        name="uniq_comentario",
    )
    colecao.create_index("conteudo_id")
    colecao.create_index("tags")
    colecao.create_index("avaliacao")


def carregar_dados_mongo(cfg, comentarios_tratados: list[dict]) -> dict:
    """Insere os comentários tratados na coleção, ignorando os que já
    foram carregados antes (mesma combinação usuario/conteudo/data/comentario)."""
    client, db = _conectar(cfg)
    try:
        colecao = db[_nome_colecao(cfg)]
        _garantir_indices(colecao)

        inseridos = 0
        for doc in comentarios_tratados:
            resultado = colecao.update_one(
                {
                    "usuario_id": doc["usuario_id"],
                    "conteudo_id": doc["conteudo_id"],
                    "data": doc["data"],
                    "comentario": doc["comentario"],
                },
                {"$setOnInsert": doc},
                upsert=True,
            )
            if resultado.upserted_id is not None:
                inseridos += 1

        logger.info(
            "Comentários carregados no MongoDB: %d (de %d recebidos).",
            inseridos, len(comentarios_tratados),
        )
    finally:
        client.close()

    return {"comentarios": inseridos, "total": inseridos}


def contar_comentarios_por_categoria(cfg, cur_postgres) -> dict[str, int]:
    """Agrega a quantidade de comentários por categoria (RF07), cruzando
    a contagem por conteudo_id do MongoDB com a categoria de cada
    conteúdo, que só existe no PostgreSQL."""
    client, db = _conectar(cfg)
    try:
        colecao = db[_nome_colecao(cfg)]
        contagem_por_conteudo = {
            doc["_id"]: doc["quantidade"]
            for doc in colecao.aggregate([
                {"$group": {"_id": "$conteudo_id", "quantidade": {"$sum": 1}}}
            ])
        }
    finally:
        client.close()

    cur_postgres.execute(
        "SELECT c.conteudo_id, cat.nome FROM conteudo c "
        "JOIN categoria cat ON cat.categoria_id = c.categoria_id;"
    )
    categoria_por_conteudo = dict(cur_postgres.fetchall())

    resultado: dict[str, int] = {}
    for conteudo_id, quantidade in contagem_por_conteudo.items():
        categoria = categoria_por_conteudo.get(conteudo_id, "desconhecida")
        resultado[categoria] = resultado.get(categoria, 0) + quantidade

    return resultado