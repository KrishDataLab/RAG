# AHITA

AUTOSAR HLD Intelligence & Traceability Assistant (AHITA) indexes HLD PDF text, answers engineering questions with references to retrieved passages, extracts architecture entities and relationships, and compares document revisions.

## Release Architecture

- **Retrieval:** Pure-Python BM25 over an in-memory index. Document chunks and metadata persist in SQLite and hydrate the index on search. No vector database or embedding model is used.
- **Generation:** Gemini or OpenAI when configured; otherwise a conservative local fallback that quotes relevant retrieved text and abstains when it cannot match the question to evidence. It is not equivalent to an LLM.
- **PDF handling:** Text extraction is page-aware. Low-text pages are detected but this release does not perform OCR.
- **Citations:** Responses include retrieved document/page/section references. The validator checks source references and lexical overlap with cited passages, but does not guarantee semantic entailment.
- **Architecture workflows:** Entity/relationship extraction, revision alignment, deterministic inconsistency rules, human review, and audit records.

## Setup (Windows PowerShell)

Run these commands from this `Code/` directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` or `OPENAI_API_KEY` in `Code/.env` to use a hosted model. Both are optional; the local fallback is selected otherwise. Configuration and prompts are loaded from `Code/configs/` and `Code/prompts/`, independent of the shell's working directory. The matching copies under the submission's `Model_Prompts_Config/` are for review and are not runtime dependencies.

Start the API and UI in separate terminals, both from `Code/`:

```powershell
python -m uvicorn app.api.main:app --port 8000
python -m streamlit run streamlit_app/Home.py --server.port 8501
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
Streamlit UI: [http://localhost:8501](http://localhost:8501)

## Included Workflows

- Upload a PDF, assign project/version metadata, and index its parsed chunks.
- Ask questions, inspect retrieved passages, and receive source references or an abstention when no chunks match.
- Extract entities and relationships and view the resulting architecture inventory/diagram.
- Compare two revisions, inspect rule-based findings, and record human review decisions.
- Run the included evaluation benchmark and export its results.

Two sample HLD revisions are in the submission's `Input_Data/` directory.

## Commands

```powershell
python -m pytest tests/ -v
python scripts/run_eval.py
python scripts/package_submission.py
```

See `../Documentation/FINAL_RUNTIME_PACKAGE_AUDIT_v1.0.md` for verified runtime details, capability status, and release-gate results.
