# Dashboard — Superset

Painel analítico sobre o consumo de conteúdos educacionais, construído no Apache
Superset sobre o PostgreSQL carregado pelo pipeline (`python -m src.main`).

---

## 1. Perguntas de negócio

O dashboard responde a duas perguntas. Cada componente existe porque responde a
uma delas — não há gráfico decorativo.

### Pergunta 1 — Onde a plataforma deve investir na produção de conteúdo?

> **Quais categorias temáticas concentram o maior engajamento dos usuários, e em
> que formato (Curso, Vídeo, Artigo ou Podcast) esse engajamento acontece?**

Por que importa: o catálogo tem 1.000 conteúdos em 8 categorias e 4 formatos, mas
a capacidade de produzir novos conteúdos é limitada. Saber que uma categoria
engaja muito em Curso e pouco em Podcast diz onde alocar esforço e onde parar.

Respondida por: **gráfico de barras** (interações por categoria, separadas por
formato) + cartões de **Total de interações** e **Usuários ativos**.

### Pergunta 2 — O engajamento está crescendo ou perdendo tração ao longo de 2026?

> **Como o volume de interações evoluiu mês a mês, e a variação se concentra em
> algum tipo de interação específico?**

Por que importa: uma queda no total é um alarme, mas não uma instrução. Separar
por tipo de interação distingue dois problemas diferentes: perder *visualizações*
é falha de descoberta/divulgação; perder *conclusões* mantendo as visualizações é
falha de qualidade do conteúdo.

Respondida por: **gráfico de linhas** (interações por mês, uma linha por tipo) +
cartão de **Avaliação média**.

---

## 2. Componentes

Mínimo exigido: 3 cartões, 1 gráfico de barras, 1 gráfico de linhas, 2 filtros.
Todos usam o dataset `vw_dashboard_interacoes`.

### Cartões de indicadores (Big Number)

| # | Cartão | Métrica | Valor atual | Formato |
|---|---|---|---|---|
| 1 | Total de interações | `COUNT(*)` | 1.000 | inteiro |
| 2 | Usuários ativos | `COUNT(DISTINCT usuario_id)` | 150 | inteiro |
| 3 | Avaliação média | `AVG(avaliacao_atribuida)` | 4,48 | 1 decimal, sufixo `/5` |
| 4 (opcional) | Conclusão média | `AVG(percentual_conclusao)` | 54,5% | percentual |

> A avaliação só existe em 356 das 1.000 interações — só os tipos *avaliação* e
> *curtida* trazem nota. A média ignora os nulos automaticamente, mas vale
> registrar isso na apresentação para ninguém achar que faltou carga.

### Gráfico de barras — Pergunta 1

- **Tipo:** Bar Chart
- **Eixo X:** `categoria`
- **Métrica:** `COUNT(*)`, rotulada "Interações"
- **Dimension (série):** `tipo_conteudo`
- **Ordenação:** pela métrica, decrescente — a leitura precisa ser "quem lidera",
  e ordem alfabética esconde isso
- **Título:** "Engajamento por categoria e formato"

Distribuição atual: Business Intelligence 144, DevOps & Cloud 141, Banco de Dados
128, Inteligência Artificial 128, Engenharia de Dados 121, Ciência de Dados 120,
Segurança & Governança 114, Programação & Software 104.

### Gráfico de linhas — Pergunta 2

- **Tipo:** Line Chart (Time-series)
- **Eixo X:** `data_hora`, **Time Grain = Month**
- **Métrica:** `COUNT(*)`
- **Dimension (séries):** `tipo_interacao`
- **Título:** "Evolução mensal das interações por tipo"

> **Cuidado com agosto.** Os dados terminam em 25/08/2026, então o último mês está
> incompleto e aparece como queda (97 contra ~130 nos meses cheios). Isso é efeito
> do recorte, não do comportamento dos usuários. Ou limite o período a julho no
> filtro, ou diga isso explicitamente na apresentação — apontar uma queda que não
> existe é o erro mais fácil de cometer aqui.

### Filtros interativos

| # | Filtro | Tipo | Coluna |
|---|---|---|---|
| 1 | Categoria | Value | `categoria` |
| 2 | Tipo de conteúdo | Value | `tipo_conteudo` |
| 3 (opcional) | Período | Time range | `data_hora` |

Ficam na barra lateral esquerda: *Edit dashboard* → ícone de filtro → **+ Add/Edit
Filters**. Como todos os gráficos usam a mesma visão, os filtros valem para o
painel inteiro sem configuração extra.

---

## 3. Consistência visual

- **Uma paleta para o dashboard todo**, definida em *Edit properties → Color
  scheme*, não gráfico a gráfico. Assim uma categoria tem sempre a mesma cor.
- **A cor identifica a entidade, não a posição.** Com o esquema no nível do
  dashboard, filtrar não repinta as barras sobreviventes.
- **Nada de eixo duplo.** Duas métricas de escalas diferentes viram dois gráficos.
- **Legenda visível** nos dois gráficos, que têm mais de uma série.

---

## 4. Como reproduzir

O ambiente é **Superset nativo no Windows + PostgreSQL em Docker**. O Superset não
precisa de Docker; o PostgreSQL usa, porque a imagem `pgvector` já traz a extensão
`vector` compilada — no Windows, compilá-la exigiria o componente C++ do Visual
Studio.

### Passo 1 — subir o banco

```bash
docker run -d --name desafio-postgres   -e POSTGRES_PASSWORD=postgres   -e POSTGRES_DB=desafio_dados   -p 5432:5432   pgvector/pgvector:pg16
```

> O contêiner sobe sem política de reinício, então **não volta sozinho depois de
> reiniciar a máquina**. Nesse caso, rode `docker start desafio-postgres`.

PostgreSQL 16 + pgvector 0.8.6, na porta **5432**. O banco `desafio_dados` é
criado automaticamente.

> Se a máquina tiver o PostgreSQL nativo do Windows instalado, ele disputa a
> mesma porta. Desative o serviço antes, num PowerShell como administrador:
> `Stop-Service postgresql-x64-16 -Force` e
> `Set-Service postgresql-x64-16 -StartupType Disabled`.

### Passo 2 — carregar os dados

Com o `.env` preenchido (senha igual à usada ao criar o contêiner):

```bash
python -m src.main
```

Carrega 8 categorias, 150 usuários, 1.000 conteúdos e 1.000 interações no
PostgreSQL, e 1.000 comentários no MongoDB.

### Passo 3 — criar as visões do dashboard

```bash
psql -U postgres -h localhost -p 5432 -d desafio_dados -f sql/criar_visoes_dashboard.sql
```

### Passo 4 — subir o Superset

Instalado em `C:\Users\libia\superset-lab`, num venv separado do projeto (as
dependências conflitam). Para subir, execute `iniciar-superset.ps1` e deixe a
janela aberta. Acesse http://localhost:8088 com `admin` / `admin`.

Quatro ajustes foram necessários para rodar no Windows, nenhum documentado
oficialmente — estão fixados em `requirements-superset.txt`:

| Sintoma | Causa | Correção |
|---|---|---|
| `pip install` aborta | limite de 260 caracteres de caminho do Windows | instalar em caminho curto, fora do OneDrive |
| `ModuleNotFoundError: rich` | importado pelo CLI, não declarado | `pip install rich` |
| `ModuleNotFoundError: cachetools` | importado no boot, não declarado | `pip install cachetools` |
| `TypeError: ignore_delete_many_errors` | `flask-caching` ≥ 2.4 incompatível | fixar `flask-caching==2.3.1` |

### Passo 5 — conectar o Superset ao banco

*Settings → Database Connections → + Database → PostgreSQL*:

```
postgresql://postgres:postgres@localhost:5432/desafio_dados
```

> O roteiro da aula usa `172.17.0.1` porque lá o Superset roda em contêiner e
> precisa alcançar o host. Aqui é o contrário — o Superset é nativo e o banco é
> que está no contêiner, então `localhost` funciona direto.

Depois: *Datasets → + Dataset* → schema `public` → **`vw_dashboard_interacoes`**.

### Passo 6 — importar o dashboard pronto

*Dashboards → Import* → selecione o `.zip` desta pasta. O Superset pede a senha do
banco na importação (ela não vai no arquivo, por segurança).

### Exportar após alterar

*Dashboards* → `...` na linha do dashboard → **Export**. Substitua o `.zip` desta
pasta pelo novo e faça commit.
