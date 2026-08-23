# LifeLens UI

React frontend for the LifeLens personal AI memory assistant.

## Demo Account

The portfolio demo defaults to:

`demolifelens@gmail.com`

This dedicated demo Gmail account contains sample data. It lets LifeLens be demonstrated without asking an interviewer or reviewer to connect a personal Gmail account.

In production, users would connect their own Gmail accounts through Google OAuth.

## Run the UI

From the `lifelens-ui` directory:

```bash
npm install
npm start
```

The frontend runs at `http://localhost:3000` and expects the FastAPI backend at `http://127.0.0.1:8000`.

## Main Screens

- **Ask** — sends questions to the LifeLens agent.
- **Timeline** — displays Gmail-derived events for the active account.
- **Upload PDF** — sends PDFs to the backend for ChromaDB indexing and RAG-based document search.

## Demo vs. Production

The demo UI starts with `demolifelens@gmail.com`. The **Change User** flow demonstrates how another Gmail account can be authorized through OAuth.
