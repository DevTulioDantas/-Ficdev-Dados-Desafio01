"""
RF14 — Registro de execução.

Segue o padrão de logging ensinado na Aula 05 (Mini-lab — Leitor Robusto
de Dados com Logs): logger nomeado, dois handlers — console mostrando
apenas INFO e acima (visão limpa para quem está rodando o pipeline) e
um arquivo rotativo (RotatingFileHandler) registrando DEBUG e acima
(histórico completo para diagnóstico), evitando handlers duplicados se
a função for chamada mais de uma vez.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configurar_logger(
    diretorio: str = "logs",
    arquivo: str = "logs/execucao.log",
    nivel_console: int = logging.INFO,
) -> logging.Logger:
    """Configura (ou reaproveita) o logger 'desafio_dados'.

    - Console: nivel_console e acima (por padrão, INFO) — visão limpa.
    - Arquivo rotativo: DEBUG e acima — histórico completo, máx. 1 MB
      por arquivo, mantendo até 3 backups (execucao.log.1, .2, .3).
    """
    Path(diretorio).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("desafio_dados")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:  # evita handlers duplicados se chamado mais de uma vez
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(nivel_console)
    console.setFormatter(fmt)

    arquivo_handler = RotatingFileHandler(
        arquivo, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    arquivo_handler.setLevel(logging.DEBUG)
    arquivo_handler.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(arquivo_handler)

    return logger
