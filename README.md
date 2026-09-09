# LifeLens

LifeLens is an orchestrated AI assistant that answers questions across a user's personal information, uploaded documents, and small-business analytics.

The application combines three specialized data paths:

- **Timeline** — structured Gmail-derived personal events stored in PostgreSQL
- **Documents** — uploaded PDFs queried with Retrieval-Augmented Generation (RAG) using ChromaDB
- **Business Analytics** — structured business data queried through guarded Text-to-SQL

A router/orchestrator selects the appropriate source or combination of sources and returns one grounded answer.

## Demo Account

For portfolio and interview demonstrations, LifeLens uses the dedicated demo Gmail account:

`demolifelens@gmail.com`

The demo account contains sample personal and business data so the application can be demonstrated without requiring an interviewer or reviewer to connect a personal Gmail account.

In a production deployment, authenticated identity would be resolved by the backend and all personal documents, timeline events, and business queries would be scoped to that user/tenant.

## Features

- Gmail OAuth with read-only access
- Dedicated demo account for portfolio demonstrations
- LLM-based extraction of structured personal events from Gmail
- Personal timeline stored in Supabase/PostgreSQL
- PDF question answering using RAG and ChromaDB
- Small-business analytics using natural-language-to-SQL
- Multi-source routing across timeline, documents, and business data
- Hybrid questions that can combine multiple source results
- SQL safety guardrails and tenant scoping
- Input and prompt-injection guardrails
- Structured observability with request trace IDs and latency/error logging
- RAG evaluation using RAGAS
- Router evaluation using routing accuracy

## Architecture

```text
                         User
                           |
                        React UI
                           |
                        FastAPI
                           |
                  Input Guardrails
                           |
                  Router / Orchestrator
                 /         |          \
                /          |           \
        Timeline        Document       Business
          Path           RAG Path       SQL Path
            |               |              |
     Gmail-derived       ChromaDB      Text-to-SQL
        events              |              |
            |           Retriever      SQL Guardrails
            |               |              |
      PostgreSQL           LLM         PostgreSQL
                \           |           /
                 \          |          /
                    Final Answer
                         |
                 Structured Logs
                  + Trace ID
```

The router can select one source for a simple question or multiple sources for a hybrid question.

Examples:

```text
"When is my next trip?"
    -> Timeline

"What does my insurance policy say about the deductible?"
    -> Document RAG

"What were my sales last month?"
    -> Business Text-to-SQL

"I'm going to New York next week. Which of my top customers are there?"
    -> Timeline + Business
    -> Final synthesis
```

## Gmail Ingestion Flow

```text
Google OAuth
    |
Gmail API
    |
Email content
    |
LLM structured extraction
    |
Supabase/PostgreSQL
    |
Personal Timeline
```

## PDF RAG Flow

```text
PDF
 |
PyPDFLoader
 |
Chunking
 |
OpenAI Embeddings
 |
ChromaDB
 |
User-scoped Retriever
 |
Top-K Context
 |
Grounded LLM Answer
```

The RAG prompt instructs the model to answer only from retrieved context and return a fallback when sufficient information is not available.

A pre-built `rag/chroma_db` containing sample/demo document embeddings may be included so the RAG workflow can be demonstrated immediately. It should contain demo/sample data only.

## Business Text-to-SQL Flow

```text
Natural-language business question
              |
              v
Backend resolves authenticated email
              |
              v
       business_id / role
              |
              v
        LLM generates SQL
              |
              v
        SQL Guardrails
              |
              v
   Read-only PostgreSQL query
              |
              v
         Query results
              |
              v
      Grounded LLM answer
```

The LLM does **not** choose the user's `business_id`. The backend resolves the tenant context from the authenticated account and supplies it as a trusted parameter.

Business tables currently include:

- `customers`
- `products`
- `orders`
- `order_items`

Personal Gmail-derived events remain separate from the business Text-to-SQL schema.

## Guardrails

LifeLens uses layered guardrails rather than relying only on prompt instructions.

### Input Guardrails

Before routing, user input is checked for:

- Empty or excessively long requests
- Suspicious prompt-injection patterns
- Unsupported control characters
- Questions unrelated to personal or business data stored in LifeLens

### RAG Guardrails

The document pipeline:

- Filters retrieval by the active `user_id`
- Uses only retrieved document context for generation
- Falls back when the retrieved context is insufficient

### Text-to-SQL Guardrails

Generated SQL is validated before execution using deterministic checks and `sqlglot` parsing.

The SQL layer enforces:

- `SELECT` / `WITH` queries only
- Exactly one SQL statement
- Approved business tables only
- Blocked access to `users`, `businesses`, `events`, and system catalogs
- No SQL comments or write/DDL operations
- Required trusted `%(business_id)s` tenant parameter
- Tenant scoping for business tables
- `order_items` access only through a tenant-scoped `orders` join
- Read-only database execution

Prompt instructions guide SQL generation, but deterministic validation is the actual security boundary.

## Observability

LifeLens emits structured logs for the orchestration pipeline.

Each request receives a unique `trace_id` that can be used to correlate events across the request lifecycle.

Observed information includes:

- Selected route/source(s)
- Router latency
- Per-source latency
- Number of retrieved RAG contexts
- SQL result row count
- Multi-source synthesis latency
- Source failures and exception types
- Final source selection

Raw email addresses are not written to observability logs; a short stable hash is used instead.

Example:

```text
{"event":"router.success","trace_id":"...","latency_ms":221.7,"sources":["business"]}
{"event":"source.business.success","trace_id":"...","latency_ms":684.2,"row_count":5}
{"event":"request.completed","trace_id":"...","sources":["business"]}
```

The architecture is intentionally provider-independent so structured logs can later be shipped to systems such as OpenTelemetry, CloudWatch, Datadog, or LangSmith.

## Evaluation

LifeLens evaluates different components with metrics appropriate to each task.

### RAG Evaluation — RAGAS

The PDF RAG pipeline exposes both the generated answer and retrieved contexts so it can be evaluated with RAGAS.

Current metrics:

- **Context Precision** — how relevant the retrieved chunks are
- **Context Recall** — whether retrieval found the information needed to answer
- **Faithfulness** — whether the answer is supported by retrieved context
- **Answer Relevancy** — whether the answer addresses the question

Evaluation cases contain manually verified reference answers from the source PDFs.

Run:

```bash
python -m eval.ragas_eval \
  --email demolifelens@gmail.com \
  --cases eval/ragas_cases.json
```

Detailed results are saved to:

```text
eval/results/ragas_results.csv
```

### Router Evaluation

Routing is evaluated separately as a classification task.

```bash
python -m eval.router_eval
```

The evaluation compares expected source(s) with the source(s) selected by the router and reports routing accuracy.

### Text-to-SQL Evaluation

The business path is designed to be evaluated using:

- SQL execution success / execution accuracy
- Result correctness
- Generated SQL safety
- Final answer correctness

RAGAS is used specifically for the RAG pipeline rather than being forced onto routing or SQL tasks.

## Tech Stack

### AI / LLM

- OpenAI API
- LangChain
- Structured LLM output
- Tool / agent orchestration
- Retrieval-Augmented Generation (RAG)
- OpenAI Embeddings
- ChromaDB
- RAGAS

### Backend

- Python
- FastAPI
- Gmail API
- OAuth 2.0
- Supabase / PostgreSQL
- Psycopg
- SQLGlot

### Frontend

- React
- JavaScript
- CSS

### Testing / Evaluation

- Pytest
- RAGAS
- Router evaluation dataset
- Structured application logging

## Specialized Paths

### Timeline

Searches structured Gmail-derived events for the active LifeLens user.

### Documents

Searches uploaded PDFs using user-scoped RAG and ChromaDB.

### Business

Converts natural-language business questions into guarded, tenant-scoped PostgreSQL queries and converts query results into concise answers.

### Orchestrator

Determines which source or sources are required and combines grounded source answers for multi-source questions.

## Privacy and Security

Secrets are loaded from environment variables and must not be committed to GitHub.

Expected local environment variables include:

```text
OPENAI_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
DATABASE_URL=...
```

Google OAuth credentials should be stored locally in `credentials.json`.

The public repository should never contain:

- Personal Gmail data
- OAuth tokens
- Database passwords
- Private uploaded documents
- Production customer/business data

The committed ChromaDB, if present, should contain demo/sample data only.

## Run Locally

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn Lifelens_api:app --reload
```

### Frontend

```bash
cd lifelens-ui
npm install
npm start
```

## Run Evaluation

### Router

```bash
python -m eval.router_eval
```

### RAGAS

First replace the template cases in `eval/ragas_cases.json` with manually verified questions and reference answers from the demo PDFs.

Then run:

```bash
python -m eval.ragas_eval \
  --email demolifelens@gmail.com
```

## MVP Design

- The default portfolio/demo account is `demolifelens@gmail.com`.
- Gmail-derived personal events are stored as structured timeline data.
- Uploaded PDFs remain in a separate RAG knowledge path.
- Business analytics uses structured PostgreSQL tables and guarded Text-to-SQL.
- The router selects the correct specialized path automatically.
- Hybrid questions can invoke multiple sources and synthesize their results.
- Tenant identity is resolved by the backend rather than selected by the LLM.
- Guardrails are applied before routing and again at specialized security boundaries.
- Evaluation and observability are treated as first-class parts of the AI system.

## Future Enhancements

- Google Calendar ingestion
- Vision/OCR for image-heavy PDFs
- Persistent multi-user credential storage
- PostgreSQL Row Level Security (RLS)
- Larger automated router evaluation set
- Text-to-SQL execution/result evaluation suite
- RAG query rewriting and reranking
- Long-term memory/state
- Incremental Gmail synchronization and deduplication
- OpenTelemetry/LangSmith integration
- CI/CD evaluation gates
