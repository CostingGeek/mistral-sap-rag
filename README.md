# SAP Fit-Gap RAG Application

A local web application that lets SAP implementation consultants and project teams interrogate SAP Customizing documentation and run fit-gap analysis against real project inputs.

## Features

- **Chat** against SAP Customizing documentation (RAG with agentic retrieval)
- **PDF Fit-Gap Analysis** - Upload requirements PDF → extract requirements → match against corpus → generate report with decisions
- **Workshop Recording Fit-Gap** - Upload audio → transcribe → match against corpus and open decisions (coming soon)

## Architecture

```
sap-rag-app/
├── backend/          # FastAPI (Python)
│   ├── integrations/  # BigQuery, Mistral, GCS clients
│   ├── services/      # Chat, PDF pipeline, decisions, etc.
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

The application will automatically create the following tables if they don't exist:
- `sap_rag.sessions` - Analysis sessions
- `sap_rag.requirements` - Extracted requirements
- `sap_rag.matches` - Requirement to object matches
- `sap_rag.decisions` - Open decisions from fit-gap analysis

The ingestion pipeline should have already created:
- `sap_rag.doktl_clean` - Cleaned SAP documentation chunks (~133k)
- `sap_rag.doktl_embeddings` - Embeddings for searchable chunks (~41k)

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
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

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

### Scenario 1: Chat

1. Navigate to **Chat** page
2. Type a question about SAP Customizing
3. Get an answer grounded in the documentation with:
   - Source citations
   - Knowledge graph visualization
   - Agent trace for transparency

Example questions:
- "What do I need to configure for dangerous goods transport?"
- "How do I set up hazard statements for chemicals?"
- "We ship lithium batteries internationally — what do we need to configure?"

### Scenario 2: PDF Fit-Gap Analysis

1. Navigate to **Fit-Gap** page
2. Upload a PDF with requirements
3. The system will:
   - Extract text using Mistral OCR (with pypdf fallback for local processing)
   - Identify discrete requirements
   - Match each requirement against SAP Customizing activities
   - Generate fit/partial/gap/question verdicts
   - Identify open decisions for workshop discussion
4. View the **Report** with:
   - Coverage statistics
   - Per-requirement verdicts and rationales
   - Open decisions list
   - Executive summary with workshop agenda

### Scenario 3: Workshop Recording (Coming Soon)

1. Upload audio recording of a workshop
2. System transcribes with Voxtral ASR (with diarization)
3. Matches transcript against:
   - The corpus (for new requirements)
   - Open decisions (to track which were answered)
4. View transcript with inline requirement markers
5. See decision status board (open → answered)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sessions` | Create a new session |
| GET | `/api/sessions` | List sessions |
| DELETE | `/api/sessions` | Clear all sessions |
| GET | `/api/sessions/{id}` | Get session details |
| POST | `/api/chat` | Send chat message |
| POST | `/api/chat/stream` | Stream chat response |
| POST | `/api/upload/pdf` | Upload PDF for analysis |
| POST | `/api/sessions/{id}/process-pdf` | Start PDF processing |
| GET | `/api/report/{id}` | Get fit-gap report |
| GET | `/api/sessions/{id}/status` | Get session processing status |
| GET | `/api/object/{id}` | Get SAP object info |
| GET | `/api/object/{id}/graph` | Get object graph |
| GET | `/api/decisions/{id}` | Get session decisions |
| PATCH | `/api/decisions/{id}` | Update decision |
| GET | `/api/health` | Health check |

## Models Used

All Mistral models:
- **Embeddings**: `mistral-embed` (1024 dims)
- **Chat & Analysis**: `mistral-medium`
- **OCR**: Mistral OCR API
- **ASR**: Mistral Voxtral (for audio transcription)

## Data Flow

### PDF Fit-Gap Pipeline

```
PDF Upload
  → Mistral OCR (text extraction)
    → [Fallback: pypdf library for local text extraction]
  → Requirement Extraction (Mistral Medium)
    → [Fallback: sentence-based extraction if API fails]
  → Per-Requirement Matching
    → Embed requirement (mistral-embed)
    → Retrieve top-k chunks (BigQuery ML.DISTANCE)
    → Fetch object evidence
    → Generate verdict (Mistral Medium)
  → Decision Generation (for partial/question)
  → Persist to BigQuery
  → Generate Report
```

### Agentic Chat

```
User Question
  → Intent Classification (simple/multi-intent/follow-up)
  → Per-(sub)query retrieval
    → Embed query
    → BigQuery vector search (k=8)
  → Graph Expansion (1-hop via element_refs)
  → Answer Synthesis (Mistral Medium)
    → Grounded in retrieved chunks
    → Citations required
  → Return answer with sources and graph
```

## Project Structure

```
sap-rag-app/
├── .env.example
├── Makefile
├── README.md
│
├── backend/
│   ├── __init__.py
│   ├── config.py           # Settings and env loading
│   ├── main.py             # FastAPI application
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── bigquery_client.py  # BigQuery operations
│   │   ├── gcs_client.py      # GCS file operations
│   │   └── mistral_client.py  # Mistral API client
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py      # Pydantic models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chat_service.py      # Agentic chat
│   │   ├── decision_service.py # Decision management
│   │   ├── pdf_pipeline.py      # PDF processing
│   │   ├── requirement_service.py # Requirement extraction
│   │   └── verdict_service.py  # Fit-gap verdicts
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
        │   └── Layout.tsx      # App layout with nav
        │
        └── views/
            ├── HomePage.tsx
            ├── ChatPage.tsx
            ├── FitGapPage.tsx
            ├── SessionsPage.tsx
            ├── ReportPage.tsx
            ├── ObjectPage.tsx
            └── DecisionsPage.tsx
```

## Testing

Run backend tests:
```bash
cd backend
python -m pytest
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
| Verdict hallucination | Verdict requires ≥1 match with distance < 0.4, otherwise forced to "question" |
| OCR garbles tables | Requirement extraction prompt tolerant to OCR noise |
| OCR API unavailable | pypdf fallback for local PDF text extraction |
| Long-audio speaker drift | Overlap windows + LLM-based speaker-merge pass |
| Decision explosion | Group similar decisions, cap by salience |
| Voxtral diarization quality | Prime with SAP glossary, fallback to non-diarized |
| Mistral API returns malformed data | Type validation and fallback to sentence-based extraction |

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
