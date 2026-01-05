# 📚 RAG Pipeline - Sherlock Discord Bot

## Visão Geral

O **Retrieval-Augmented Generation (RAG)** é o sistema que permite ao SherlockBot responder
perguntas baseando-se em documentos reais da sua base de conhecimento jurídico.

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Documento  │ ──▶  │   Chunking   │ ──▶  │  Embeddings │
│  (PDF/TXT)  │      │   (Tokens)   │      │   (OpenAI)  │
└─────────────┘      └──────────────┘      └─────────────┘
                                                  │
                                                  ▼
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Resposta  │ ◀──  │   LLM + RAG  │ ◀──  │   pgvector  │
│   (Bot)     │      │   Context    │      │   (Neon DB) │
└─────────────┘      └──────────────┘      └─────────────┘
```

## Arquitetura

### Componentes Principais

| Componente            | Arquivo                  | Descrição                        |
| --------------------- | ------------------------ | -------------------------------- |
| **Ingestion Script**  | `scripts/ingest_docs.py` | Processa e indexa documentos     |
| **RAG Service**       | `src/rag_service.py`     | Busca híbrida (Vector + Keyword) |
| **Embedding Service** | `src/rag_service.py`     | Gera embeddings via OpenAI       |
| **Completion**        | `src/completion.py`      | Injeta contexto RAG nos prompts  |

### Tecnologias

- **Banco de Dados**: Neon (PostgreSQL Serverless)
- **Vector Search**: pgvector (HNSW index)
- **Full-Text Search**: PostgreSQL tsvector (português)
- **Embeddings**: OpenAI `text-embedding-3-small` (1536 dimensões)
- **Ranking**: Reciprocal Rank Fusion (RRF)

---

## 🔧 Configuração

### Variáveis de Ambiente

```bash
# Obrigatórias
DATABASE_URL=postgresql://user:pass@host/db
OPENAI_API_KEY=sk-...

# Opcionais
EMBEDDING_MODEL=text-embedding-3-small   # Modelo de embeddings
TEXT_SEARCH_LANG=portuguese               # Idioma para full-text search
```

### Inicialização do Banco

Execute o schema de inicialização:

```bash
psql $DATABASE_URL -f scripts/init_rag_pgvector.sql
```

Este script cria:

- Extensão `pgvector`
- Tabela `documents` com coluna `embedding vector(1536)`
- Índice HNSW para busca vetorial rápida
- Índice GIN para full-text search

---

## 📄 Alimentando a Base de Conhecimento

### Formatos Suportados

| Formato | Extensão      | Requisitos                 |
| ------- | ------------- | -------------------------- |
| PDF     | `.pdf`        | `pypdf` instalado          |
| Word    | `.docx`       | `python-docx` instalado    |
| HTML    | `.html`       | `beautifulsoup4` instalado |
| Texto   | `.txt`, `.md` | Nenhum                     |

### Comando de Ingestão

```bash
# Ingerir um documento
uv run python scripts/ingest_docs.py caminho/para/documento.pdf

# Com parâmetros customizados
uv run python scripts/ingest_docs.py documento.pdf --chunk-size 800 --overlap 150
```

### Parâmetros

| Parâmetro      | Default | Descrição                             |
| -------------- | ------- | ------------------------------------- |
| `--chunk-size` | 1000    | Tamanho máximo do chunk (em tokens)   |
| `--overlap`    | 200     | Sobreposição entre chunks (em tokens) |

### Exemplo Prático

```bash
# 1. Ingerir a Constituição Federal
uv run python scripts/ingest_docs.py ~/docs/constituicao_federal.pdf

# 2. Ingerir Código Civil
uv run python scripts/ingest_docs.py ~/docs/codigo_civil.pdf --chunk-size 500

# 3. Verificar status
uv run python scripts/verify_ingestion.py
```

---

## 🔍 Como Funciona a Busca

### 1. Hybrid Search (Busca Híbrida)

O sistema combina duas estratégias de busca:

#### Vector Search (Semântica)

```sql
SELECT content FROM documents
ORDER BY embedding <=> $query_embedding::vector
LIMIT 10;
```

- Encontra documentos semanticamente similares
- Usa distância de cosseno (`<=>`)
- Índice HNSW para performance

#### Keyword Search (Full-Text)

```sql
SELECT content FROM documents
WHERE content_search @@ websearch_to_tsquery('portuguese', $query)
ORDER BY ts_rank(content_search, ...) DESC
LIMIT 10;
```

- Encontra matches exatos de palavras
- Suporta linguagem natural
- Otimizado para português

### 2. Reciprocal Rank Fusion (RRF)

Os resultados das duas buscas são combinados usando RRF:

```python
score = 1 / (k + rank)  # k = 60 (padrão da indústria)
```

Isso garante que documentos que aparecem bem em **ambas** as buscas sejam priorizados.

### 3. Injeção de Contexto

O contexto recuperado é formatado em XML e injetado no prompt:

```xml
<relevant_context>
  <doc index='1'>Conteúdo do documento mais relevante...</doc>
  <doc index='2'>Segundo documento mais relevante...</doc>
</relevant_context>

Instructions:
1. Use the provided context to answer the user's question.
2. If the context contains the answer, cite the document index.
3. If insufficient, use general knowledge but mention missing details.
```

---

## 📊 Monitoramento

### Verificar Estatísticas

```bash
uv run python scripts/verify_ingestion.py
```

### Teste End-to-End

```bash
uv run python scripts/test_rag_e2e.py
```

Saída esperada:

```
🧪 RAG End-to-End Test
📊 Status: active
📄 Documents ingested: ✅
🔍 Query returned 3 results
✨ RRF correctly ranked document!
✅ RAG End-to-End Test Completed!
```

---

## 🚀 Boas Práticas

### Chunking

1. **Chunk Size**: 500-1000 tokens é ideal para contexto legal
2. **Overlap**: 10-20% do chunk_size previne perda de contexto
3. **Documentos longos**: Use `RecursiveTokenSplitter` (automático)

### Performance

1. **HNSW Index**: Já configurado com `m=16, ef_construction=64`
2. **Connection Pool**: Limitado a 5 conexões para Neon Free Tier
3. **Batch Ingestion**: Documentos são processados em lote

### Qualidade

1. **Híbrido > Vector-only**: A busca híbrida melhora recall
2. **RRF k=60**: Valor padrão balanceia precisão e diversidade
3. **Top-5 Results**: Mais contexto nem sempre é melhor

---

## 🔧 Troubleshooting

### "OPENAI_API_KEY not found"

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### "DATABASE_URL not set"

```bash
export DATABASE_URL=postgresql://user:pass@host/dbname
```

### "No documents found"

1. Verifique se os documentos foram ingeridos
2. Execute `scripts/verify_ingestion.py`
3. Confirme que o schema foi inicializado

### Embeddings lentos

- O modelo `text-embedding-3-small` é o mais rápido
- Batch processing já está implementado
- Considere aumentar rate limits da OpenAI

---

## 📁 Estrutura de Arquivos

```
sherlock-discord-bot/
├── scripts/
│   ├── init_rag_pgvector.sql    # Schema do banco
│   ├── ingest_docs.py           # Script de ingestão
│   ├── verify_ingestion.py      # Verificação de status
│   └── test_rag_e2e.py          # Teste end-to-end
├── src/
│   ├── rag_service.py           # Serviço RAG principal
│   ├── completion.py            # Injeção de contexto
│   └── database.py              # Conexão com Neon
└── docs/
    └── rag-pipeline.md          # Esta documentação
```
