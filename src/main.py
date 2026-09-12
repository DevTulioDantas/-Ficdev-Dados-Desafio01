"""
Ponto de entrada do pipeline.

Uso:
    python -m src.main

O RF01 exige que o sistema seja executado por esse comando e que
apresente mensagens indicando início e término do processamento — isso é
feito tanto aqui (para quem está olhando o terminal) quanto via logger
(RF14, para quem for investigar depois em logs/execucao.log).
"""
from __future__ import annotations

import sys

from src.config import ConfiguracaoPipeline
from src.logger import configurar_logger
from src.db.setup import criar_tabelas
from ingestao.pipeline import executar_ingestao, gravar_resumo
from persistencia.postgres import carregar_dados_postgres
from persistencia.mongo import carregar_dados_mongo


def main() -> int:
    print(">> Iniciando pipeline do Desafio Prático 1 — Fundamentos de Dados para IA")

    try:
        cfg = ConfiguracaoPipeline("config.json")
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERRO] {exc}")
        return 1

    logger = configurar_logger(
        diretorio=cfg.get("logging", "diretorio", padrao="logs"),
        arquivo=cfg.get("logging", "arquivo", padrao="logs/execucao.log"),
    )

    try:
        criar_tabelas()
        resumo, dados_tratados = executar_ingestao(cfg)

        contagens_postgres = carregar_dados_postgres(
            cfg, dados_tratados["catalogo"], dados_tratados["interacoes"]
        )
        contagens_mongo = carregar_dados_mongo(cfg, dados_tratados["comentarios"])

        resumo["registros_carregados_por_banco"]["postgresql"] = contagens_postgres["total"]
        resumo["registros_carregados_por_banco"]["mongodb"] = contagens_mongo["total"]
        gravar_resumo(cfg, resumo)
    except Exception as exc:  # noqa: BLE001 - qualquer falha do pipeline deve ser registrada
        logger.exception("Falha não tratada durante o processamento: %s", exc)
        print(f"[ERRO] Processamento interrompido: {exc}")
        return 1

    print("\nResumo da ingestão:")
    print(f"  Lidos:       {resumo['registros_lidos']['total']}")
    print(f"  Válidos:     {resumo['registros_validos']['total']}")
    print(f"  Inválidos:   {resumo['registros_invalidos']['total']}")
    print(f"  Incompletos: {resumo['registros_incompletos']['total']}")
    print(f"  Duplicados:  {resumo['registros_duplicados']['total']}")
    print(f"  Corrigidos:  {resumo['registros_corrigidos']['total']}")
    print(f"  Tempo total: {resumo['tempo_total_processamento_segundos']}s")
    print("\n>> Processamento concluído. Veja logs/execucao.log para detalhes.")
    print(">> Próxima fase (PostgreSQL, MongoDB, embeddings, recomendação e")
    print("   dashboard) será adicionada nas próximas etapas — ver README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())