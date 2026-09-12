"""
Orquestra RF02 (leitura) -> RF03 (validação) -> RF04 (tratamento) e produz
o resumo exigido pelo RF05.

Os registros tratados (apenas válidos, já padronizados) são gravados em
dados/processados/. Os registros rejeitados (inválidos, incompletos ou
duplicados), com o motivo, são gravados separadamente para rastreabilidade
— isso apoia o RF14 (registro de execução), permitindo investigar depois
por que um registro específico não entrou no processamento.
"""
from __future__ import annotations

import csv
import json
import logging
import time
from pathlib import Path

from ingestao.leitura import ler_todas_as_fontes
from ingestao.tratamento import tratar_catalogo, tratar_comentarios, tratar_interacoes
from ingestao.validacao import (
    STATUS_DUPLICADO,
    STATUS_INCOMPLETO,
    STATUS_INVALIDO,
    STATUS_VALIDO,
    validar_catalogo,
    validar_comentarios,
    validar_interacoes,
)

logger = logging.getLogger("desafio_dados")


def _contar_status(registros: list[dict]) -> dict[str, int]:
    contagem = {STATUS_VALIDO: 0, STATUS_INVALIDO: 0, STATUS_INCOMPLETO: 0, STATUS_DUPLICADO: 0}
    for r in registros:
        contagem[r["_status"]] = contagem.get(r["_status"], 0) + 1
    return contagem


def _gravar_rejeitados(diretorio: Path, nome_fonte: str, registros: list[dict]) -> None:
    rejeitados = [
        {k: v for k, v in r.items() if not k.startswith("_")} | {
            "status": r["_status"], "motivo": r["_motivo"]
        }
        for r in registros if r["_status"] != STATUS_VALIDO
    ]
    if not rejeitados:
        return
    caminho = diretorio / f"rejeitados_{nome_fonte}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(rejeitados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Registros rejeitados de '%s' gravados em %s (%d registros).",
                nome_fonte, caminho, len(rejeitados))


def _gravar_csv(caminho: Path, registros: list[dict]) -> None:
    if not registros:
        caminho.write_text("", encoding="utf-8")
        return
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(registros[0].keys()))
        writer.writeheader()
        writer.writerows(registros)


def _gravar_json(caminho: Path, registros: list[dict]) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2, default=str)


def executar_ingestao(cfg) -> dict:
    """Executa RF02->RF05 e retorna o dicionário de resumo (RF05)."""
    t0 = time.perf_counter()
    logger.info("=" * 70)
    logger.info("INÍCIO DO PROCESSAMENTO DE INGESTÃO")
    logger.info("=" * 70)

    diretorio_saida = Path(cfg.get("saida", "diretorio_processados", padrao="dados/processados"))
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    # RF02 — leitura
    brutos = ler_todas_as_fontes(cfg)
    qtd_lidos = {nome: len(regs) for nome, regs in brutos.items()}

    # RF03 — validação (catálogo primeiro, pois interações/comentários
    # precisam saber quais conteúdos são válidos para checar referências)
    catalogo_validado = validar_catalogo(brutos["catalogo"], cfg)
    ids_conteudo_validos = {
        str(r["conteudo_id"]) for r in catalogo_validado if r["_status"] == STATUS_VALIDO
    }
    interacoes_validadas = validar_interacoes(brutos["interacoes"], cfg, ids_conteudo_validos)
    comentarios_validados = validar_comentarios(brutos["comentarios"], cfg, ids_conteudo_validos)

    # RF04 — tratamento e padronização (apenas dos válidos)
    catalogo_tratado, corrigidos_catalogo = tratar_catalogo(catalogo_validado, cfg)
    interacoes_tratadas, corrigidos_interacoes = tratar_interacoes(interacoes_validadas, cfg)
    comentarios_tratados, corrigidos_comentarios = tratar_comentarios(comentarios_validados, cfg)

    # gravação dos dados tratados (arquivos originais preservados em dados/brutos/)
    _gravar_csv(diretorio_saida / "catalogo_conteudos.csv", catalogo_tratado)
    _gravar_json(diretorio_saida / "interacoes_usuarios.json", interacoes_tratadas)
    _gravar_json(diretorio_saida / "comentarios_avaliacoes.json", comentarios_tratados)

    # gravação dos rejeitados (rastreabilidade)
    _gravar_rejeitados(diretorio_saida, "catalogo", catalogo_validado)
    _gravar_rejeitados(diretorio_saida, "interacoes", interacoes_validadas)
    _gravar_rejeitados(diretorio_saida, "comentarios", comentarios_validados)

    contagem_catalogo = _contar_status(catalogo_validado)
    contagem_interacoes = _contar_status(interacoes_validadas)
    contagem_comentarios = _contar_status(comentarios_validados)

    tempo_total = round(time.perf_counter() - t0, 3)

    def _soma(chave: str) -> int:
        return contagem_catalogo[chave] + contagem_interacoes[chave] + contagem_comentarios[chave]

    resumo = {
        "registros_lidos": {
            "catalogo": qtd_lidos["catalogo"],
            "interacoes": qtd_lidos["interacoes"],
            "comentarios": qtd_lidos["comentarios"],
            "total": sum(qtd_lidos.values()),
        },
        "registros_validos": {
            "catalogo": contagem_catalogo[STATUS_VALIDO],
            "interacoes": contagem_interacoes[STATUS_VALIDO],
            "comentarios": contagem_comentarios[STATUS_VALIDO],
            "total": _soma(STATUS_VALIDO),
        },
        "registros_invalidos": {
            "catalogo": contagem_catalogo[STATUS_INVALIDO],
            "interacoes": contagem_interacoes[STATUS_INVALIDO],
            "comentarios": contagem_comentarios[STATUS_INVALIDO],
            "total": _soma(STATUS_INVALIDO),
        },
        "registros_incompletos": {
            "catalogo": contagem_catalogo[STATUS_INCOMPLETO],
            "interacoes": contagem_interacoes[STATUS_INCOMPLETO],
            "comentarios": contagem_comentarios[STATUS_INCOMPLETO],
            "total": _soma(STATUS_INCOMPLETO),
        },
        "registros_duplicados": {
            "catalogo": contagem_catalogo[STATUS_DUPLICADO],
            "interacoes": contagem_interacoes[STATUS_DUPLICADO],
            "comentarios": contagem_comentarios[STATUS_DUPLICADO],
            "total": _soma(STATUS_DUPLICADO),
        },
        "registros_corrigidos": {
            "catalogo": corrigidos_catalogo,
            "interacoes": corrigidos_interacoes,
            "comentarios": corrigidos_comentarios,
            "total": corrigidos_catalogo + corrigidos_interacoes + corrigidos_comentarios,
        },
        # Preenchido nas fases de persistência (RF06/RF07), ainda em
        # desenvolvimento. Mantido em zero por enquanto para o esquema do
        # resumo já sair completo, conforme o RF05 exige.
        "registros_carregados_por_banco": {
            "postgresql": 0,
            "mongodb": 0,
        },
        "tempo_total_processamento_segundos": tempo_total,
    }

    gravar_resumo(cfg, resumo)

    logger.info("=" * 70)
    logger.info("TÉRMINO DO PROCESSAMENTO DE INGESTÃO (%.3fs)", tempo_total)
    logger.info("=" * 70)

    dados_tratados = {
        "catalogo": catalogo_tratado,
        "interacoes": interacoes_tratadas,
        "comentarios": comentarios_tratados,
    }
    return resumo, dados_tratados


def gravar_resumo(cfg, resumo: dict) -> None:
    """Grava (ou regrava) o resumo da ingestão em disco (RF05).

    Reaproveitada em dois momentos: ao final da ingestão (RF02-RF05) e
    depois da persistência (RF06/RF07), quando as contagens de
    registros carregados por banco são preenchidas.
    """
    caminho_resumo = cfg.get("saida", "arquivo_resumo_ingestao", padrao="dados/processados/resumo_ingestao.json")
    with open(caminho_resumo, "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)
    logger.info("Resumo da ingestão gravado em %s", caminho_resumo)