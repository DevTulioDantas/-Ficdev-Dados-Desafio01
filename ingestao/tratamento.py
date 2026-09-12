"""
RF04 — Tratamento e padronização.

Aplica-se apenas aos registros classificados como 'valido' pelo RF03.
Registros inválidos/incompletos/duplicados não entram aqui — eles só
aparecem no relatório do RF05.

Decisões de tratamento:
  - espaços nas extremidades de campos textuais são removidos;
  - campos categóricos (tipo, categoria, nível, tipo_interacao) são
    normalizados para a grafia canônica definida em config.json (робusto
    a variações de caixa, mesmo que os dados reais recebidos já estejam
    consistentes);
  - datas são reconvertidas para o formato ISO 8601 (garante consistência
    mesmo que o formato de origem já seja ISO);
  - campos numéricos são convertidos para int/float conforme o caso
    (a leitura de CSV sempre traz string, então essa conversão é
    obrigatória mesmo quando o valor já "parece" um número);
  - tags de comentários são normalizadas (minúsculas, sem espaço,
    duplicatas removidas);
  - um registro só conta como "corrigido" (RF05) se algo de fato mudou
    além da conversão de tipo/formato — ou seja, se havia um problema
    cosmético real (espaço extra, caixa inconsistente).
"""
from __future__ import annotations

import logging
from datetime import datetime

from ingestao.validacao import STATUS_VALIDO

logger = logging.getLogger("desafio_dados")


def _canonico(valor: str, opcoes: list[str]) -> str:
    """Retorna a grafia canônica de 'valor' comparando sem caixa/espaços."""
    alvo = str(valor).strip().lower()
    for opcao in opcoes:
        if opcao.strip().lower() == alvo:
            return opcao
    return str(valor).strip()


def tratar_catalogo(registros: list[dict], cfg) -> tuple[list[dict], int]:
    categorias = cfg.get("validacao", "categorias_validas", padrao=[])
    tipos = cfg.get("validacao", "tipos_conteudo_validos", padrao=[])
    niveis = cfg.get("validacao", "niveis_validos", padrao=[])
    formato_data = cfg.get("validacao", "formato_data_catalogo", padrao="%Y-%m-%d")

    tratados = []
    corrigidos = 0
    for r in registros:
        if r.get("_status") != STATUS_VALIDO:
            continue

        titulo = " ".join(r["titulo"].strip().split())
        descricao = " ".join(r["descricao"].strip().split())
        autor = " ".join(r["autor"].strip().split())
        categoria = _canonico(r["categoria"], categorias)
        tipo = _canonico(r["tipo"], tipos)
        nivel = _canonico(r["nivel"], niveis)

        novo = {
            "conteudo_id": int(r["conteudo_id"]),
            "titulo": titulo,
            "tipo": tipo,
            "categoria": categoria,
            "nivel": nivel,
            "carga_horaria_min": int(float(r["carga_horaria_min"])),
            "data_publicacao": datetime.strptime(
                str(r["data_publicacao"]).strip(), formato_data
            ).strftime("%Y-%m-%d"),
            "descricao": descricao,
            "autor": autor,
        }

        # "corrigido" = havia diferença que não é apenas conversão de tipo
        # (ex.: espaço extra, caixa diferente da canônica) — não conta a
        # simples troca de string->número ou passagem pela mesma máscara
        # de data.
        if titulo != r["titulo"] or descricao != r["descricao"] or autor != r["autor"] \
                or categoria != r["categoria"].strip() or tipo != r["tipo"].strip() \
                or nivel != r["nivel"].strip():
            corrigidos += 1

        tratados.append(novo)

    logger.info("Tratamento [catálogo]: %d registros tratados (%d corrigidos).", len(tratados), corrigidos)
    return tratados, corrigidos


def tratar_interacoes(registros: list[dict], cfg) -> tuple[list[dict], int]:
    tipos = cfg.get("validacao", "tipos_interacao_validos", padrao=[])
    formato_data = cfg.get("validacao", "formato_data_interacao", padrao="%Y-%m-%dT%H:%M:%S")

    tratados = []
    corrigidos = 0
    for r in registros:
        if r.get("_status") != STATUS_VALIDO:
            continue

        tipo_original = r["tipo_interacao"]
        tipo_canonico = _canonico(tipo_original, tipos)

        percentual = r.get("percentual_conclusao")
        percentual = None if percentual in (None, "") else round(float(percentual), 1)

        tempo = r.get("tempo_consumido")
        tempo = None if tempo in (None, "") else int(float(tempo))

        avaliacao = r.get("avaliacao_atribuida")
        avaliacao = None if avaliacao in (None, "") else int(float(avaliacao))

        novo = {
            "usuario_id": int(r["usuario_id"]),
            "conteudo_id": int(r["conteudo_id"]),
            "tipo_interacao": tipo_canonico,
            "data_hora": datetime.strptime(
                str(r["data_hora"]).strip(), formato_data
            ).isoformat(),
            "tempo_consumido": tempo,
            "percentual_conclusao": percentual,
            "avaliacao_atribuida": avaliacao,
        }

        if tipo_canonico != tipo_original.strip():
            corrigidos += 1

        tratados.append(novo)

    logger.info("Tratamento [interações]: %d registros tratados (%d corrigidos).", len(tratados), corrigidos)
    return tratados, corrigidos


def tratar_comentarios(registros: list[dict], cfg) -> tuple[list[dict], int]:
    formato_data = cfg.get("validacao", "formato_data_comentario", padrao="%Y-%m-%d")

    tratados = []
    corrigidos = 0
    for r in registros:
        if r.get("_status") != STATUS_VALIDO:
            continue

        tags_originais = r.get("tags") or []
        tags_tratadas = sorted({str(t).strip().lower() for t in tags_originais if str(t).strip()})
        comentario_tratado = " ".join(str(r["comentario"]).strip().split())

        novo = {
            "usuario_id": int(r["usuario_id"]),
            "conteudo_id": int(r["conteudo_id"]),
            "avaliacao": int(float(r["avaliacao"])),
            "comentario": comentario_tratado,
            "tags": tags_tratadas,
            "data": datetime.strptime(str(r["data"]).strip(), formato_data).strftime("%Y-%m-%d"),
        }

        tags_originais_norm = {str(t).strip().lower() for t in tags_originais if str(t).strip()}
        if tags_originais_norm != set(tags_tratadas) or comentario_tratado != r["comentario"]:
            corrigidos += 1

        tratados.append(novo)

    logger.info("Tratamento [comentários]: %d registros tratados (%d corrigidos).", len(tratados), corrigidos)
    return tratados, corrigidos
