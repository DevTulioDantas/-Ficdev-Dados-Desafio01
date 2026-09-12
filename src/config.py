"""
RF01 — Inicialização e configuração.

Segue o padrão de leitura de configuração ensinado na Aula 05
(carregar_configuracao: JSON + try/except específico), estendido para
também carregar credenciais de um arquivo .env (Aula 12/17), de forma que
senhas nunca fiquem no código-fonte nem no config.json versionado.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def carregar_configuracao(caminho: str = "config.json") -> dict[str, Any]:
    """Carrega o arquivo de configuração em JSON.

    Mesma estratégia de tratamento de erro vista na Aula 05: se o arquivo
    não existir ou tiver um JSON mal formado, o problema é reportado de
    forma clara em vez de deixar o programa quebrar com um traceback cru.
    """
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {Path(caminho).resolve()}"
        ) from None
    except json.JSONDecodeError as e:
        raise ValueError(f"Erro ao interpretar '{caminho}' como JSON: {e}") from e


class ConfiguracaoPipeline:
    """Reúne o config.json (parâmetros) e o .env (credenciais) em um só
    ponto de acesso, para o resto do pipeline nunca precisar ler esses
    arquivos diretamente."""

    def __init__(self, caminho_config: str = "config.json") -> None:
        self.dados = carregar_configuracao(caminho_config)
        load_dotenv()  # carrega variáveis do .env, se existir; não falha se ausente

    def get(self, *chaves: str, padrao: Any = None) -> Any:
        """Acessa valores aninhados do config.json: get('postgres', 'host')."""
        atual: Any = self.dados
        for chave in chaves:
            if not isinstance(atual, dict) or chave not in atual:
                return padrao
            atual = atual[chave]
        return atual

    # --- credenciais sensíveis: sempre via variáveis de ambiente (.env) ----
    @property
    def postgres_dsn(self) -> dict[str, Any]:
        return {
            "host": os.getenv("POSTGRES_HOST", self.get("postgres", "host", padrao="localhost")),
            "port": int(os.getenv("POSTGRES_PORT", self.get("postgres", "porta", padrao=5432))),
            "dbname": os.getenv("POSTGRES_DB", self.get("postgres", "banco", padrao="desafio_dados")),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", ""),
        }

    @property
    def mongodb_uri(self) -> str:
        return os.getenv(
            "MONGODB_URI",
            f"mongodb://{self.get('mongodb', 'host', padrao='localhost')}:"
            f"{self.get('mongodb', 'porta', padrao=27017)}",
        )

    @property
    def mongodb_db(self) -> str:
        return os.getenv("MONGODB_DB", self.get("mongodb", "banco", padrao="desafio_dados"))
