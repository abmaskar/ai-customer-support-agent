# AI Customer Support Agent

Full-stack-ready AI support backend with RAG-style retrieval and citation flow.

## Problem

Support teams waste time answering repeated questions. This project reduces repetitive workload using document-grounded AI answers.

## Features

- Chat API with session history
- Admin document upload (`.txt`, `.pdf`)
- Retrieval over uploaded documents (RAG-style)
- Source citation in every answer
- Feedback endpoint (`up/down`) for quality loop

## Tech Stack

- Python + FastAPI
- Pydantic
- PDF parsing (`pypdf`)
- Ready to connect to PostgreSQL + Chroma/Qdrant + OpenAI/Ollama

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt
python run.py
```

- API docs: `http://127.0.0.1:8101/docs`

## Core API

- `POST /api/admin/upload` -> upload support docs
- `POST /api/chat` -> ask question + get citations
- `GET /api/chat/history/{session_id}` -> conversation history
- `POST /api/chat/feedback` -> thumbs up/down

## Evaluation (what to measure)

- `Answer groundedness`: % answers with valid citations
- `Support deflection`: % questions resolved without human handoff
- `Feedback ratio`: upvotes / total feedback
- `Latency`: p50, p95
- `Fallback rate`: no-context responses / total chats

## Production Signals

- Eval score target: >= 0.80 groundedness
- Fallback rate target: <= 0.20
- p95 latency target: <= 3s
- Release gate: block release if two targets fail

## Hiring Value

Demonstrates RAG, API design, AI product thinking, and measurable production KPIs.

