# SAP RAG Chat Application

A local web application that lets users chat with SAP Customizing documentation using RAG (Retrieval-Augmented Generation) with Mistral AI.

## Features

- **Chat** against SAP Customizing documentation with RAG and agentic retrieval
- **Corpus scope selection**: ask against the SAP standard (DOKTL), the company standard (DOKTL_NOVA), or both
- Source citations with clickable references
- Rich markdown rendering of assistant answers: nested numbered/bulleted lists, tables, code blocks, and inline styles
- Conversation history with reset capability

## Architecture

```
sap-rag-app/
├── backend/          # FastAPI (Python)
│   ├── integrations/  # BigQuery, Mistral clients
│   ├── services/      # Agentic chat service
│   ├── models/        # Pydantic schemas
│   └── main.py        # FastAPI application
│
└── frontend/         # React + Vite + TypeScript
    ├── src/views/     # Page components
    ├── src/components/ # Reusable components
    └── ...            # Config files
```

## Prerequisites

- Python 3.12+
- Node.js 18+
- Google Cloud SDK (for authentication)
- Mistral API key

## Setup

### 1. Clone and Setup

```bash
cd sap-rag-app

# Install backend dependencies
make install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 2. Environment Variables

Edit `.env` file with your configuration:

```bash
# GCP Configuration
GCP_PROJECT=your-gcp-project
BQ_DATASET=sap_rag
BUCKET=your-bucket-name

# GCP Service Account Key (base64 encoded)
# Create with: cat service-account.json | base64 -w 0
GCP_SA_KEY_BASE64=your-base64-encoded-key

# Mistral API
MISTRAL_API_KEY=your-mistral-api-key

# Application (optional)
APP_HOST=127.0.0.1
APP_PORT=8000
DEBUG=true
```

### 3. BigQuery Tables

The ingestion pipeline (see `doc/ingest_sap_documentation_doktl.ipynb`) creates the corpus tables the backend reads:
- `sap_rag.doktl_clean` - Cleaned SAP standard documentation chunks (~137k)
- `sap_rag.doktl_embeddings` - Embeddings for searchable chunks (~46k)
- `sap_rag.doktl_nova_clean` - Company-standard (Project NOVA) chunks - created by setting `CORPUS = "DOKTL_NOVA"` in the ingestion notebook
- `sap_rag.doktl_nova_embeddings` - Embeddings for the NOVA corpus

### 4. Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Development Mode

Start both backend and frontend:

```bash
# Terminal 1: Backend
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000) in your browser.

### Using Make

```bash
# Install dependencies
make install

# Start backend
make dev

# In another terminal, start frontend
cd frontend && npm run dev
```

## Usage

### Chat with SAP Documentation

1. Open the application
2. Type a question about SAP Customizing
3. Get an answer grounded in the documentation with:
   - Source citations
   - Agent trace for transparency

Example questions:
- "What do I need to configure for dangerous goods transport?"
- "How do I set up hazard statements for chemicals?"
- "We ship lithium batteries internationally - what do we need to configure?"

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send chat message (optional `scope` in body: `standard` / `nova` / `both`) |
| GET | `/api/object/{id}` | Get SAP object info (optional `?scope=standard|nova|both`). `{id}` may contain slashes (e.g. `SIMG/SEHS/DG_020`); the frontend sends it URL-encoded |
| GET | `/api/object/{id}/graph` | Get related-objects graph for an object (optional `?scope=standard|nova|both`) |
| GET | `/api/health` | Health check |

## Models Used

All Mistral models:
- **Embeddings**: `mistral-embed` (1024 dims)
- **Chat & Analysis**: `mistral-medium-latest`

## Data Flow

### Chat Flow

```
User Question
  -> Intent Classification (simple/multi-intent/follow-up)
  -> Per-(sub)query retrieval
    -> Embed query (mistral-embed)
    -> BigQuery vector search with ML.DISTANCE (k=8)
    -> Graph Expansion (1-hop via element_refs)
  -> Answer Synthesis (Mistral Medium)
    -> Grounded in retrieved chunks
    -> Citations required
  -> Return answer with sources
```

## Project Structure

```
sap-rag-app/
├── .env.example
├── Makefile
├── README.md
├── BUILD_SUMMARY.md
│
├── backend/
│   ├── __init__.py
│   ├── config.py           # Settings and env loading
│   ├── main.py             # FastAPI application
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── bigquery_client.py  # BigQuery operations
│   │   └── mistral_client.py  # Mistral API client
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py      # Pydantic models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── chat_service.py      # Agentic chat
│   │
│   └── requirements.txt
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── postcss.config.js
    │
    └── src/
        ├── main.tsx
        ├── index.css
        ├── App.tsx
        ├── App.css
        ├── vite-env.d.ts
        │
        ├── types/
        │   └── index.ts       # TypeScript types
        │
        ├── hooks/
        │   └── useApi.ts       # API client hook
        │
        ├── components/
        │   └── Layout.tsx      # App layout
        │
        └── views/
            ├── HomePage.tsx
            └── ObjectPage.tsx
```

## Testing

Run backend tests:
```bash
# Note: Tests are not currently implemented
```

## Deployment

For production deployment:

1. Set `DEBUG=false` in environment
2. Configure proper authentication
3. Set up reverse proxy (Nginx, etc.)
4. Consider using:
   - Gunicorn + Uvicorn for FastAPI
   - PM2 or similar for process management
   - Proper logging configuration

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Hallucination prevention | Answers are grounded in retrieved chunks and must cite them; golden-set calibration shows true-match and negative distance bands overlap, so distance is never treated as confidence |
| Mistral API returns malformed data | Type validation with regex JSON extraction fallback |

## License

This project is for demonstration purposes and uses Mistral AI APIs.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Acknowledgments

- SAP for the Customizing documentation corpus
- Mistral AI for the embeddings and LLM APIs
- Google Cloud for BigQuery and GCS
