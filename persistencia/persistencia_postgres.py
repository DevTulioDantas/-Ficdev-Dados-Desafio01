"""
RF06 — Persistência no PostgreSQL.

Carrega os dados já tratados (RF04) nas tabelas definidas em
sql/criar_banco.sql. A ordem de carga respeita as dependências de
chave estrangeira: categoria -> conteudo, e usuario -> interacao.

Toda a carga acontece dentro de uma única transação (RF06 exige uso de
transações): se qualquer inserção falhar, nada é gravado.
"""
from __future__ import annotations

import logging

import psycopg2

logger = logging.getLogger("desafio_dados")


def _conectar(cfg):
    return psycopg2.connect(**cfg.postgres_dsn)


def _carregar_categorias(cur, catalogo_tratado: list[dict]) -> dict[str, int]:
    """Insere as categorias distintas do catálogo e devolve um mapa nome -> categoria_id."""
    nomes = sorted({r["categoria"] for r in catalogo_tratado})
    mapa: dict[str, int] = {}
    for nome in nomes:
        cur.execute(
            """
            INSERT INTO categoria (nome) VALUES (%s)
            ON CONFLICT (nome) DO UPDATE SET nome = EXCLUDED.nome
            RETURNING categoria_id;
            """,
            (nome,),
        )
        mapa[nome] = cur.fetchone()[0]
    logger.info("Categorias carregadas: %d.", len(mapa))
    return mapa


def _carregar_usuarios(cur, interacoes_tratadas: list[dict]) -> int:
    """Popula usuario com os usuario_id distintos vistos nas interações."""
    usuario_ids = sorted({r["usuario_id"] for r in interacoes_tratadas})
    for usuario_id in usuario_ids:
        cur.execute(
            "INSERT INTO usuario (usuario_id) VALUES (%s) ON CONFLICT (usuario_id) DO NOTHING;",
            (usuario_id,),
        )
    logger.info("Usuários carregados: %d.", len(usuario_ids))
    return len(usuario_ids)


def _carregar_conteudos(cur, catalogo_tratado: list[dict], mapa_categorias: dict[str, int]) -> int:
    """Insere ou atualiza cada conteúdo do catálogo tratado."""
    for r in catalogo_tratado:
        cur.execute(
            """
            INSERT INTO conteudo
                (conteudo_id, titulo, tipo, categoria_id, nivel,
                 carga_horaria_min, data_publicacao, descricao, autor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (conteudo_id) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                tipo = EXCLUDED.tipo,
                categoria_id = EXCLUDED.categoria_id,
                nivel = EXCLUDED.nivel,
                carga_horaria_min = EXCLUDED.carga_horaria_min,
                data_publicacao = EXCLUDED.data_publicacao,
                descricao = EXCLUDED.descricao,
                autor = EXCLUDED.autor;
            """,
            (
                r["conteudo_id"], r["titulo"], r["tipo"],
                mapa_categorias[r["categoria"]], r["nivel"],
                r["carga_horaria_min"], r["data_publicacao"],
                r["descricao"], r["autor"],
            ),
        )
    logger.info("Conteúdos carregados: %d.", len(catalogo_tratado))
    return len(catalogo_tratado)


def _carregar_interacoes(cur, interacoes_tratadas: list[dict]) -> int:
    """Insere as interações, ignorando as que já foram carregadas antes
    (mesma combinação usuario/conteudo/tipo/data_hora)."""
    inseridos = 0
    for r in interacoes_tratadas:
        cur.execute(
            """
            INSERT INTO interacao
                (usuario_id, conteudo_id, tipo_interacao, data_hora,
                 tempo_consumido, percentual_conclusao, avaliacao_atribuida)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (usuario_id, conteudo_id, tipo_interacao, data_hora) DO NOTHING;
            """,
            (
                r["usuario_id"], r["conteudo_id"], r["tipo_interacao"], r["data_hora"],
                r["tempo_consumido"], r["percentual_conclusao"], r["avaliacao_atribuida"],
            ),
        )
        inseridos += cur.rowcount
    logger.info("Interações carregadas: %d (de %d recebidas).", inseridos, len(interacoes_tratadas))
    return inseridos


def carregar_dados_postgres(cfg, catalogo_tratado: list[dict], interacoes_tratadas: list[dict]) -> dict:
    """Executa a carga completa no PostgreSQL e retorna as contagens por entidade."""
    conn = _conectar(cfg)
    try:
        with conn:
            with conn.cursor() as cur:
                mapa_categorias = _carregar_categorias(cur, catalogo_tratado)
                qtd_usuarios = _carregar_usuarios(cur, interacoes_tratadas)
                qtd_conteudos = _carregar_conteudos(cur, catalogo_tratado, mapa_categorias)
                qtd_interacoes = _carregar_interacoes(cur, interacoes_tratadas)
        logger.info("Carga no PostgreSQL concluída.")
    except Exception:
        logger.exception("Falha na carga do PostgreSQL — transação revertida.")
        raise
    finally:
        conn.close()

    return {
        "categorias": len(mapa_categorias),
        "usuarios": qtd_usuarios,
        "conteudos": qtd_conteudos,
        "interacoes": qtd_interacoes,
        "total": qtd_conteudos + qtd_interacoes,
    }