"""
RF02 — Leitura das fontes de dados.

Lê o CSV do catálogo de conteúdos e os JSONs de interações e de
comentários/avaliações. Para cada fonte, informa o nome do arquivo e a
quantidade de registros encontrados (exigência explícita do RF02).

O logger é obtido por nome ("desafio_dados"), a mesma instância que
src/logger.py configura uma única vez em src/main.py — por isso este
módulo não precisa receber o logger por parâmetro.
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("desafio_dados")


def _validar_existencia(caminho: str) -> Path:
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"Fonte de dados não encontrada: {p.resolve()}")
    return p


def ler_catalogo_csv(caminho: str) -> list[dict[str, Any]]:
    p = _validar_existencia(caminho)
    with open(p, "r", encoding="utf-8", newline="") as f:
        registros = list(csv.DictReader(f))
    logger.info("Fonte '%s': %d registros encontrados.", p.name, len(registros))
    return registros


def ler_json(caminho: str) -> list[dict[str, Any]]:
    p = _validar_existencia(caminho)
    with open(p, "r", encoding="utf-8") as f:
        registros = json.load(f)
    if not isinstance(registros, list):
        raise ValueError(f"Esperava uma lista de registros em {p.name}, recebeu {type(registros)}")
    logger.info("Fonte '%s': %d registros encontrados.", p.name, len(registros))
    return registros


def ler_todas_as_fontes(cfg) -> dict[str, list[dict[str, Any]]]:
    """Lê as três fontes obrigatórias (RF02) e retorna os dados brutos."""
    logger.info("Iniciando leitura das fontes de dados...")

    catalogo = ler_catalogo_csv(cfg.get("fontes", "catalogo_csv"))
    interacoes = ler_json(cfg.get("fontes", "interacoes_json"))
    comentarios = ler_json(cfg.get("fontes", "comentarios_json"))

    logger.info(
        "Leitura concluída: %d catálogo | %d interações | %d comentários.",
        len(catalogo), len(interacoes), len(comentarios),
    )
    return {"catalogo": catalogo, "interacoes": interacoes, "comentarios": comentarios}
