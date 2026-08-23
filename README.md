# LifeLens

LifeLens is a personal AI memory assistant that turns Gmail activity into a searchable life timeline and lets users ask questions about uploaded PDF documents using Retrieval-Augmented Generation (RAG).

## Demo Account

For portfolio and interview demonstrations, LifeLens uses the dedicated demo Gmail account:

`demolifelens@gmail.com`

The demo account contains sample data so the application can be demonstrated without requiring an interviewer or reviewer to connect a personal Gmail account.

In a production deployment, each user would connect their own Gmail account through Google OAuth and LifeLens would scope stored events and queries to that authenticated user.

## Features

- Gmail OAuth with read-only access
- Dedicated demo Gmail account for portfolio demonstrations
- LLM-based extraction of structured personal events from Gmail
- User-specific timeline stored in Supabase/PostgreSQL
- Agentic question routing using LangChain tools
- PDF question answering using RAG and ChromaDB
- Guardrails for out-of-scope questions

## Architecture

```text
User
  |
React UI
  |
FastAPI
  |
LifeLens Agent
  |-----------------------------|
  |                             |
search_timeline           search_documents
  |                             |
Gmail-derived events        PDF RAG
  |                             |
Supabase/PostgreSQL          ChromaDB
                                |
                          OpenAI embeddings + LLM
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
Timeline
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
Retriever
 |
LLM Answer
```

A pre-built `rag/chroma_db` containing sample/demo document embeddings is intentionally included in this repository so the RAG workflow can be demonstrated immediately.

## Tech Stack

### AI / LLM
- OpenAI API
- LangChain
- Tool calling / agent workflows
- RAG
- OpenAI Embeddings
- ChromaDB

### Backend
- Python
- FastAPI
- Gmail API
- OAuth 2.0
- Supabase / PostgreSQL

### Frontend
- React
- JavaScript
- CSS

## Agent Tools

### `search_timeline`

Searches Gmail-derived events for the active LifeLens user.

### `search_documents`

Searches uploaded PDFs using RAG.

## Privacy

Secrets are loaded from environment variables and are not committed to GitHub.

Expected local environment variables:

```text
OPENAI_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
```

Google OAuth credentials should be stored locally in `credentials.json`.

The committed ChromaDB should contain demo/sample data only. The public repository should not contain personal Gmail data, OAuth tokens, or private uploaded documents.

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

## MVP Design

- The default UI account is `demolifelens@gmail.com`.
- Timeline data comes from Gmail-derived structured events.
- PDFs are used separately for RAG-based question answering.
- The agent chooses the correct tool automatically.
- LifeLens currently supports one active Gmail user at a time.
- The demo account avoids requiring reviewers to connect their own Gmail during a portfolio demonstration.

## Future Enhancements

- Google Calendar ingestion
- Vision/OCR for image-heavy PDFs
- Multi-user credential storage
- RAG and tool-selection evaluation
- Incremental Gmail synchronization and deduplication
