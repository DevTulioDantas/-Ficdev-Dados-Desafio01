"""
RF03 — Validação dos dados.

Cada registro é classificado como: válido, inválido, incompleto ou
duplicado. O motivo é sempre registrado quando o registro não é válido.

Prioridade de classificação: duplicado > incompleto > inválido > válido.

Observação sobre identificadores: o catálogo tem um identificador natural
(conteudo_id), usado para detectar duplicidade. Interações e comentários
NÃO têm um identificador próprio nos dados reais recebidos — por isso,
duplicidade neles é detectada por igualdade de conteúdo (o mesmo registro,
com todos os campos iguais, aparecendo mais de uma vez).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("desafio_dados")

STATUS_VALIDO = "valido"
STATUS_INVALIDO = "invalido"
STATUS_INCOMPLETO = "incompleto"
STATUS_DUPLICADO = "duplicado"


def _norm(valor: Any) -> str:
    return str(valor).strip().lower() if valor is not None else ""


def _data_valida(data_str: str, formato: str) -> bool:
    try:
        datetime.strptime(str(data_str).strip(), formato)
        return True
    except (ValueError, TypeError):
        return False


def _chave_conteudo_registro(registro: dict) -> tuple:
    """Assinatura do registro (todos os campos, ordenados) — usada para
    detectar duplicidade quando não há um identificador natural."""
    return tuple(sorted((k, str(v)) for k, v in registro.items()))


def _marcar(registro: dict, status: str, motivo: str = "") -> dict:
    registro["_status"] = status
    registro["_motivo"] = motivo
    return registro


# --------------------------------------------------------------------------
# Catálogo de conteúdos
# --------------------------------------------------------------------------
def validar_catalogo(registros: list[dict], cfg) -> list[dict]:
    categorias_validas = {c.lower() for c in cfg.get("validacao", "categorias_validas", padrao=[])}
    tipos_validos = {t.lower() for t in cfg.get("validacao", "tipos_conteudo_validos", padrao=[])}
    niveis_validos = {n.lower() for n in cfg.get("validacao", "niveis_validos", padrao=[])}
    formato_data = cfg.get("validacao", "formato_data_catalogo", padrao="%Y-%m-%d")

    vistos: set[str] = set()
    resultado = []

    for reg in registros:
        r = dict(reg)
        chave = _norm(r.get("conteudo_id"))

        # A checagem de duplicidade é feita ANTES de qualquer outra validação
        # e independe do restante do registro ser válido — dois registros com
        # o mesmo conteudo_id são duplicados mesmo que o primeiro deles seja
        # inválido por outro motivo.
        if chave:
            if chave in vistos:
                resultado.append(_marcar(r, STATUS_DUPLICADO, "conteudo_id repetido"))
                continue
            vistos.add(chave)

        if not r.get("conteudo_id") or not r.get("titulo", "").strip() \
                or not r.get("descricao", "").strip() or not r.get("autor", "").strip():
            resultado.append(_marcar(r, STATUS_INCOMPLETO, "campo obrigatório ausente (id/título/descrição/autor)"))
            continue

        if _norm(r.get("categoria")) not in categorias_validas:
            resultado.append(_marcar(r, STATUS_INVALIDO, f"categoria fora do domínio: '{r.get('categoria')}'"))
            continue

        if _norm(r.get("tipo")) not in tipos_validos:
            resultado.append(_marcar(r, STATUS_INVALIDO, f"tipo fora do domínio: '{r.get('tipo')}'"))
            continue

        if _norm(r.get("nivel")) not in niveis_validos:
            resultado.append(_marcar(r, STATUS_INVALIDO, f"nível fora do domínio: '{r.get('nivel')}'"))
            continue

        try:
            carga = float(r.get("carga_horaria_min"))
            if carga <= 0:
                resultado.append(_marcar(r, STATUS_INVALIDO, "carga_horaria_min não positiva"))
                continue
        except (TypeError, ValueError):
            resultado.append(_marcar(r, STATUS_INVALIDO, "carga_horaria_min não numérica"))
            continue

        if not _data_valida(r.get("data_publicacao"), formato_data):
            resultado.append(_marcar(r, STATUS_INVALIDO, f"data_publicacao inválida: '{r.get('data_publicacao')}'"))
            continue

        resultado.append(_marcar(r, STATUS_VALIDO))

    _log_resumo("catálogo", resultado)
    return resultado


# --------------------------------------------------------------------------
# Interações dos usuários
# --------------------------------------------------------------------------
def validar_interacoes(registros: list[dict], cfg, ids_conteudo_validos: set[str]) -> list[dict]:
    tipos_validos = {t.lower() for t in cfg.get("validacao", "tipos_interacao_validos", padrao=[])}
    formato_data = cfg.get("validacao", "formato_data_interacao", padrao="%Y-%m-%dT%H:%M:%S")
    usuario_min = cfg.get("validacao", "usuario_id_min", padrao=1)
    usuario_max = cfg.get("validacao", "usuario_id_max", padrao=10_000)
    aval_min = cfg.get("validacao", "avaliacao_min", padrao=1)
    aval_max = cfg.get("validacao", "avaliacao_max", padrao=5)

    vistos: set[tuple] = set()
    resultado = []

    for reg in registros:
        r = dict(reg)
        chave = _chave_conteudo_registro(reg)

        if chave in vistos:
            resultado.append(_marcar(r, STATUS_DUPLICADO, "registro idêntico já processado"))
            continue
        vistos.add(chave)

        if r.get("usuario_id") in (None, "") or r.get("conteudo_id") in (None, "") \
                or not r.get("tipo_interacao") or not r.get("data_hora"):
            resultado.append(_marcar(r, STATUS_INCOMPLETO,
                                      "campo obrigatório ausente (usuário/conteúdo/tipo/data)"))
            continue

        try:
            usuario_id = int(r["usuario_id"])
        except (TypeError, ValueError):
            resultado.append(_marcar(r, STATUS_INVALIDO, "usuario_id não numérico"))
            continue
        if not (usuario_min <= usuario_id <= usuario_max):
            resultado.append(_marcar(r, STATUS_INVALIDO, f"usuario_id inexistente: {usuario_id}"))
            continue

        if _norm(r.get("conteudo_id")) not in ids_conteudo_validos:
            resultado.append(_marcar(r, STATUS_INVALIDO, f"conteudo_id inexistente: {r.get('conteudo_id')}"))
            continue

        if _norm(r.get("tipo_interacao")) not in tipos_validos:
            resultado.append(_marcar(r, STATUS_INVALIDO, f"tipo_interacao fora do domínio: '{r.get('tipo_interacao')}'"))
            continue

        if not _data_valida(r.get("data_hora"), formato_data):
            resultado.append(_marcar(r, STATUS_INVALIDO, f"data_hora inválida: '{r.get('data_hora')}'"))
            continue

        tempo = r.get("tempo_consumido")
        if tempo is not None:
            try:
                if float(tempo) < 0:
                    resultado.append(_marcar(r, STATUS_INVALIDO, "tempo_consumido negativo"))
                    continue
            except (TypeError, ValueError):
                resultado.append(_marcar(r, STATUS_INVALIDO, "tempo_consumido não numérico"))
                continue

        percentual = r.get("percentual_conclusao")
        if percentual is not None:
            try:
                if not (0 <= float(percentual) <= 100):
                    resultado.append(_marcar(r, STATUS_INVALIDO, "percentual_conclusao fora de 0-100"))
                    continue
            except (TypeError, ValueError):
                resultado.append(_marcar(r, STATUS_INVALIDO, "percentual_conclusao não numérico"))
                continue

        # avaliacao_atribuida é opcional e pode aparecer em qualquer tipo de
        # interação (não só 'avaliação') — os dados reais confirmam isso.
        # Quando presente, só precisa estar dentro da faixa permitida.
        avaliacao = r.get("avaliacao_atribuida")
        if avaliacao is not None:
            try:
                avaliacao_num = float(avaliacao)
                if not (aval_min <= avaliacao_num <= aval_max):
                    resultado.append(_marcar(r, STATUS_INVALIDO, f"avaliacao_atribuida fora de {aval_min}-{aval_max}"))
                    continue
            except (TypeError, ValueError):
                resultado.append(_marcar(r, STATUS_INVALIDO, "avaliacao_atribuida não numérica"))
                continue

        resultado.append(_marcar(r, STATUS_VALIDO))

    _log_resumo("interações", resultado)
    return resultado


# --------------------------------------------------------------------------
# Comentários e avaliações
# --------------------------------------------------------------------------
def validar_comentarios(registros: list[dict], cfg, ids_conteudo_validos: set[str]) -> list[dict]:
    formato_data = cfg.get("validacao", "formato_data_comentario", padrao="%Y-%m-%d")
    usuario_min = cfg.get("validacao", "usuario_id_min", padrao=1)
    usuario_max = cfg.get("validacao", "usuario_id_max", padrao=10_000)
    aval_min = cfg.get("validacao", "avaliacao_min", padrao=1)
    aval_max = cfg.get("validacao", "avaliacao_max", padrao=5)

    vistos: set[tuple] = set()
    resultado = []

    for reg in registros:
        r = dict(reg)
        chave = _chave_conteudo_registro(reg)

        if chave in vistos:
            resultado.append(_marcar(r, STATUS_DUPLICADO, "registro idêntico já processado"))
            continue
        vistos.add(chave)

        if r.get("usuario_id") in (None, "") or r.get("conteudo_id") in (None, "") \
                or not str(r.get("comentario", "")).strip():
            resultado.append(_marcar(r, STATUS_INCOMPLETO, "campo obrigatório ausente (usuário/conteúdo/comentário)"))
            continue

        try:
            usuario_id = int(r["usuario_id"])
        except (TypeError, ValueError):
            resultado.append(_marcar(r, STATUS_INVALIDO, "usuario_id não numérico"))
            continue
        if not (usuario_min <= usuario_id <= usuario_max):
            resultado.append(_marcar(r, STATUS_INVALIDO, f"usuario_id inexistente: {usuario_id}"))
            continue

        if _norm(r.get("conteudo_id")) not in ids_conteudo_validos:
            resultado.append(_marcar(r, STATUS_INVALIDO, f"conteudo_id inexistente: {r.get('conteudo_id')}"))
            continue

        try:
            avaliacao_num = float(r.get("avaliacao"))
            if not (aval_min <= avaliacao_num <= aval_max):
                resultado.append(_marcar(r, STATUS_INVALIDO, f"avaliação fora de {aval_min}-{aval_max}"))
                continue
        except (TypeError, ValueError):
            resultado.append(_marcar(r, STATUS_INVALIDO, "avaliação ausente/inválida"))
            continue

        if not _data_valida(r.get("data"), formato_data):
            resultado.append(_marcar(r, STATUS_INVALIDO, f"data inválida: '{r.get('data')}'"))
            continue

        resultado.append(_marcar(r, STATUS_VALIDO))

    _log_resumo("comentários", resultado)
    return resultado


def _log_resumo(nome_fonte: str, resultado: list[dict]) -> None:
    contagem = {STATUS_VALIDO: 0, STATUS_INVALIDO: 0, STATUS_INCOMPLETO: 0, STATUS_DUPLICADO: 0}
    for r in resultado:
        contagem[r["_status"]] = contagem.get(r["_status"], 0) + 1
    logger.info(
        "Validação [%s]: válidos=%d inválidos=%d incompletos=%d duplicados=%d",
        nome_fonte, contagem[STATUS_VALIDO], contagem[STATUS_INVALIDO],
        contagem[STATUS_INCOMPLETO], contagem[STATUS_DUPLICADO],
    )
