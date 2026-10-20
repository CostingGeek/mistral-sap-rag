# Project conventions — sap-rag-app

Instructions for agents working in this repository. Keep this file current when
project facts change.

## Run & verify

- Backend: FastAPI. Verify with `uv run python -m compileall -q backend` and
  `uv run python -c "import backend.main"`. Bare `python` is blocked in this
  environment — always use `uv run python ...`.
- Frontend: React + Vite + TS in `frontend/`. Verify with
  `cd frontend && npm run build` (runs tsc, then vite). The build was broken on
  main before 2026-10-18 (pre-existing ObjectPage tsc errors); keep it green.
- Python deps are managed by uv (`pyproject.toml` + `uv.lock`). Run `uv lock`
  after changing dependencies. `backend/requirements.txt` is a legacy mirror —
  keep it in sync.
- The backend talks to live GCP (configure your project and dataset in `.env`)
  and the Mistral API. Importing `backend.main` instantiates
  BigQueryClient and hits BigQuery. Direct service calls in tests cost Mistral
  tokens — keep them small and purposeful.

## Environment quirks (Windows / this machine)

- Line endings are normalized to LF repo-wide via `.gitattributes`
  (`* text=auto eol=lf`) and `core.autocrlf` is disabled locally. Write new
  files and edit scripts with LF joins. Do not re-enable `autocrlf` or commit
  CRLF — it breaks the `edit` tool's string matching on this machine.
- Bash heredocs containing multiline content get CRLF-mangled in transport —
  never use them for code. Use throwaway Node scripts for programmatic edits,
  and verify edits with `grep`/`sed -n` before assuming they landed.

## Domain facts

- Two corpora: SAP standard (`DOKTL`, 68,625 objects, tables `doktl_clean` /
  `doktl_embeddings`) and company standard (`DOKTL_NOVA`, 24 objects,
  `doktl_nova_clean` / `doktl_nova_embeddings`). NOVA object IDs are
  `SIMG/NOVA/*`; corpora are disjoint in content (e.g. zero payroll chunks in
  NOVA vs 6,200 in standard).
- The chat flow is stateless: history lives in the frontend; `session_id` in
  responses is a throwaway uuid. Do not reintroduce session persistence
  without discussion.
- Citations: the LLM must cite as `[Source N]` — square brackets required;
  extraction depends on the literal string. Source numbers refer to the full
  context order; `ChunkInfo.source_no` carries that number to the UI so the
  source list matches in-text markers.
- Graph-expanded chunks carry `distance=0.0` as a sentinel plus
  `graph_expanded=True` — never display their similarity (it would show 1.000).
- The old fit-gap PDF pipeline (sessions/requirements/matches/decisions tables,
  pdf_pipeline, decision/requirement/verdict services, gcs_client, OCR/ASR
  methods) was removed on 2026-10-18 and the BigQuery tables dropped. Do not
  resurrect it; the chat RAG flow is the product.
- The ingestion notebook (`doc/ingest_sap_documentation_doktl.ipynb`) runs
  once per corpus. A `DOKTL_NOVA` run requires `DOKTL` ingested first
  (cross-corpus ref validation reads `doktl_clean`).

## Instrumentation

- `ChatService.chat()` records per-step `duration_ms` and token usage in the
  trace (token usage is thread-local in `MistralClient` because sub-query
  retrieval runs in parallel). The backend logs a `chat timing:` INFO line;
  the UI shows the breakdown under each assistant message. Instrument any new
  pipeline step the same way.
- Reference timing (battery query, scope both, 2026-10-18): ~12s total —
  intent ~1s (`mistral-small-latest`), retrieval ~4.5s (up to 3 parallel
  sub-queries, BQ ML.DISTANCE over the embedding union), graph ~2.2s (2
  batched queries), synthesis ~4s+ (`mistral-medium-latest`, scales with
  answer length).

## Known open items

- True token streaming: `/api/chat/stream` currently sends the whole answer as
  one event; the Stop button only aborts the frontend fetch, not backend work.
- Retrieval still costs ~4s per sub-query; candidates: BigQuery vector index,
  or a pre-merged scope table to avoid the UNION.
- Citation extraction could accept bare `Source N` (no brackets) as a fallback;
  one observed run produced zero citations because the model dropped brackets.
- Chat-quality harness: the notebook's golden sets could grade answers and
  citations to measure quality, not just speed.
