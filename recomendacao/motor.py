"""
RF10/RF11 — Motor de recomendação e persistência.

Calcula, para cada usuário, a pontuação de afinidade com cada conteúdo
que ele ainda não concluiu:

    Pontuacao = ((Ivis + Icur) / 2) * 100 * Iconc

- Ivis (afinidade temática): proporção do tempo que o usuário consumiu
  na mesma categoria do conteúdo candidato, em relação à categoria em
  que ele mais consumiu tempo (0.0 a 1.0).
- Icur (interesse explícito): proporção de interações positivas
  (curtida, ou avaliação >= nota_minima_curtida) do usuário dentro da
  mesma categoria do conteúdo candidato (0.0 a 1.0).
- Iconc (filtro de conclusão): conteúdos já concluídos pelo usuário são
  removidos do conjunto de candidatos antes do cálculo — por isso Iconc
  é sempre 1 para os candidatos considerados aqui.

Cada execução grava uma nova leva de recomendações): ela funciona como um histórico de gerações, e
data_geracao marca quando cada uma aconteceu.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

import psycopg2

logger = logging.getLogger("desafio_dados")


def _conectar(cfg):
    return psycopg2.connect(**cfg.postgres_dsn)


def _buscar_interacoes_por_usuario(cur) -> dict[int, list[dict]]:
    """Retorna, por usuario_id, a lista de interações com a categoria
    do conteúdo já resolvida via join."""
    cur.execute(
        """
        SELECT i.usuario_id, i.conteudo_id, i.tipo_interacao,
               i.tempo_consumido, i.avaliacao_atribuida, c.categoria_id
        FROM interacao i
        JOIN conteudo c ON c.conteudo_id = i.conteudo_id;
        """
    )
    por_usuario: dict[int, list[dict]] = defaultdict(list)
    for usuario_id, conteudo_id, tipo, tempo, avaliacao, categoria_id in cur.fetchall():
        por_usuario[usuario_id].append({
            "conteudo_id": conteudo_id,
            "tipo": tipo,
            "tempo": tempo or 0,
            "avaliacao": avaliacao,
            "categoria_id": categoria_id,
        })
    return por_usuario


def _buscar_conteudos(cur) -> list[tuple[int, int]]:
    """Retorna (conteudo_id, categoria_id) de todos os conteúdos."""
    cur.execute("SELECT conteudo_id, categoria_id FROM conteudo;")
    return cur.fetchall()


def _calcular_perfil_usuario(interacoes: list[dict], nota_minima_curtida: int) -> dict:
    """A partir das interações de um usuário, calcula por categoria: tempo
    total consumido, interações positivas e total de interações; e o
    conjunto de conteúdos já concluídos."""
    tempo_por_categoria: dict[int, float] = defaultdict(float)
    positivas_por_categoria: dict[int, int] = defaultdict(int)
    total_por_categoria: dict[int, int] = defaultdict(int)
    concluidos: set[int] = set()

    for it in interacoes:
        cat = it["categoria_id"]
        tempo_por_categoria[cat] += it["tempo"]
        total_por_categoria[cat] += 1

        positiva = it["tipo"] == "curtida" or (
            it["avaliacao"] is not None and it["avaliacao"] >= nota_minima_curtida
        )
        if positiva:
            positivas_por_categoria[cat] += 1

        if it["tipo"] == "conclusao":
            concluidos.add(it["conteudo_id"])

    maior_tempo = max(tempo_por_categoria.values(), default=0)

    return {
        "tempo_por_categoria": tempo_por_categoria,
        "positivas_por_categoria": positivas_por_categoria,
        "total_por_categoria": total_por_categoria,
        "maior_tempo": maior_tempo,
        "concluidos": concluidos,
    }


def _classificar(pontuacao: float) -> str:
    if pontuacao >= 70:
        return "positivo"
    if pontuacao > 40:
        return "estavel"
    return "negativo"


def gerar_recomendacoes(cfg) -> dict:
    """Gera e persiste as recomendações de todos os usuários com
    histórico de interação (RF10/RF11)."""
    nota_minima_curtida = cfg.get("recomendacao", "nota_minima_curtida", padrao=4)
    top_n = cfg.get("recomendacao", "top_n_padrao", padrao=5)

    conn = _conectar(cfg)
    try:
        with conn:
            with conn.cursor() as cur:
                interacoes_por_usuario = _buscar_interacoes_por_usuario(cur)
                conteudos = _buscar_conteudos(cur)

                agora = datetime.now()
                total_geradas = 0

                for usuario_id, interacoes in interacoes_por_usuario.items():
                    perfil = _calcular_perfil_usuario(interacoes, nota_minima_curtida)

                    candidatos = []
                    for conteudo_id, categoria_id in conteudos:
                        if conteudo_id in perfil["concluidos"]:
                            continue  # já concluído: removido do conjunto de candidatos

                        ivis = (
                            perfil["tempo_por_categoria"].get(categoria_id, 0) / perfil["maior_tempo"]
                            if perfil["maior_tempo"] > 0 else 0.0
                        )
                        total_cat = perfil["total_por_categoria"].get(categoria_id, 0)
                        icur = (
                            perfil["positivas_por_categoria"].get(categoria_id, 0) / total_cat
                            if total_cat > 0 else 0.0
                        )
                        iconc = 1  # candidatos já excluem os concluídos

                        pontuacao = round(((ivis + icur) / 2) * 100 * iconc, 2)
                        candidatos.append((conteudo_id, pontuacao))

                    candidatos.sort(key=lambda item: item[1], reverse=True)

                    for posicao, (conteudo_id, pontuacao) in enumerate(candidatos[:top_n], start=1):
                        status = _classificar(pontuacao)
                        cur.execute(
                            """
                            INSERT INTO recomendacao
                                (usuario_id, conteudo_id, pontuacao, posicao, status, data_geracao)
                            VALUES (%s, %s, %s, %s, %s, %s);
                            """,
                            (usuario_id, conteudo_id, pontuacao, posicao, status, agora),
                        )
                        total_geradas += 1

        logger.info("Recomendações geradas: %d.", total_geradas)
        return {"geradas": total_geradas}
    finally:
        conn.close()