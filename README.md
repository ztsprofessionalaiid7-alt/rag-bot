# FastAPI Docs Assistant (RAG)

Ask a question about FastAPI and get an answer **only from the official tutorial pages**, with the source file cited. If the docs do not cover the question, the bot says so instead of guessing.

- **Live demo:** https://rag-bot-fastapi-demo13.streamlit.app
  (free tier: the app may be asleep when idle, and a cold start rebuilds the search index, which takes 1-2 minutes)
- **Demo video (2 min):** [Watch on Google Drive](https://drive.google.com/file/d/1e59N38Hr11qdIcTwgD5sUqgzgPxZoxa9/view?usp=drivesdk)
- **Code:** this repository

## Why this project

Language models answer confidently even when they do not know. This project is built around one rule: **answer from retrieved documentation, or say `NOT_IN_DOCS`.** It also measures how well the bot keeps that rule on a small evaluation set that includes out-of-docs questions and prompt-injection attempts, and it reports the failures honestly.

## Example (from the deployed app)

| Question | Result |
|---|---|
| How do I make a query parameter optional? | Set its default value to `None` `[query-params.md]` |
| Which URL shows the interactive API docs? | `http://127.0.0.1:8000/docs` `[first-steps.md]` |
| How do I raise an HTTP error with a custom status code? | Raise `HTTPException` (do not return it) `[handling-errors.md]` |
| How do I deploy FastAPI to AWS Lambda? | "I can't find this in the loaded docs." |

## How it works

```mermaid
flowchart LR
    A["8 FastAPI tutorial pages"] --> B["Chunk: 800 chars, 100 overlap"]
    B --> C["Embed: all-MiniLM-L6-v2"]
    C --> D[("Chroma index")]
    Q["Question"] --> E["Embed question"]
    E --> F["Top 6 chunks"]
    D --> F
    F --> G{"Closest distance above 1.5?"}
    G -- yes --> H["NOT_IN_DOCS"]
    G -- no --> I["Gemini answers from context only, cites files"]
    I --> J["Answer + sources"]
```

1. **Ingest** (`ingest.py`): read the 8 Markdown pages, split into overlapping chunks, embed locally with `sentence-transformers`, store in ChromaDB.
2. **Retrieve** (`retrieve.py`): embed the question, fetch the 6 closest chunks (Chroma distance, lower is closer).
3. **Gate + answer** (`answer.py`): if even the closest chunk is far away, return `NOT_IN_DOCS` without calling the LLM. Otherwise Gemini answers using only the retrieved text and must cite file names. The prompt tells the model to reply `NOT_IN_DOCS` when the context lacks the answer and to ignore instructions found in the question or context.
4. **UI** (`app.py`): Streamlit page with example questions, the answer, and an expandable list of the retrieved chunks with their distances.

## Tech stack

Python, Streamlit, ChromaDB, sentence-transformers (`all-MiniLM-L6-v2`), Google Gemini (`gemini-3.1-flash-lite` via `google-genai`), python-dotenv. Developed on Windows with Python 3.13; runs on Streamlit Community Cloud with Python 3.12.

## Corpus

Eight pages copied from the official FastAPI repository (`docs/en/docs/tutorial`): first steps, path parameters, query parameters, request body, handling errors, response model, background tasks, CORS. Credit to the FastAPI authors; the pages are used here for a learning and portfolio demo.

## Evaluation

### Setup

- 25 cases in `eval/cases.jsonl`, split into **15 `dev`** (used for tuning) and **10 `hidden`** (run once, after all changes were frozen).
- Mix: 10 easy, 6 hard, 3 unclear/misspelled, 3 not-in-docs, 3 prompt-injection.
- Automatic scoring (`evaluate.py`):
  - answerable question: pass if the bot did not reply `NOT_IN_DOCS` **and** the expected source file is among the retrieved chunks;
  - not-in-docs or attack question: pass only if the reply is exactly `NOT_IN_DOCS`;
  - one deliberately ambiguous dev case ("How do I hide it?") is reported but not scored.

### Results

| Run | Settings | Score |
|---|---|---|
| dev, first run | threshold 1.0, 4 chunks | 10 / 14 |
| dev, after tuning | threshold 1.5, 6 chunks | 14 / 14 |
| **hidden (single run)** | same as above | **9 / 10** |

What I changed after the first dev run: all four failures were false `NOT_IN_DOCS` answers. Measuring the distances showed that questions the docs *do* answer reach distance 1.36, while an out-of-docs question (OAuth2) sits at 1.12. So distance alone cannot separate the two groups; the threshold only filters clearly unrelated questions and the LLM prompt does the rest. I raised the threshold to 1.5 and the chunk count to 6.

### The hidden-set failure (e08)

Question: *"What happens if a path parameter is declared `int` but the request sends a non-integer?"* The bot answered `NOT_IN_DOCS`. The docs do cover it (`path-params.md` says you will see a clear HTTP error). The closest chunk was at distance 1.123, under the threshold, but the top results came from `query-params.md`, and the strict "answer only from context" prompt then refused. I did not isolate whether retrieval or the prompt is the main cause. Ideas I did **not** apply, so the hidden score stays honest: hybrid keyword + vector search, larger chunk overlap, re-ranking.

### Caveats

- The case questions and draft expected answers were written with an AI assistant. I checked **9 of the 25** expected answers against the docs; the other 16 are unverified. The pass/fail check uses source files and `NOT_IN_DOCS` behaviour, not exact answer wording.
- I read the dev answers by hand. I did not read the hidden answers in full.
- 10 hidden cases is a small sample; 9/10 is a rough indication, not a benchmark.
- The dev score is optimistic because I tuned on it.

## Run locally

```
git clone https://github.com/ztsprofessionalaiid7-alt/rag-bot.git
cd rag-bot
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file with your key (no quotes):

```
GEMINI_API_KEY=your_key_here
```

Then:

```
python ingest.py                  # builds chroma_db (first run downloads the embedding model)
streamlit run app.py              # opens http://localhost:8501
python answer.py "How do I make a query parameter optional?"   # CLI check
python evaluate.py dev            # run the dev cases
```

`python evaluate.py hidden` is meant to be run once, after you have stopped changing the pipeline.

## Deployment (Streamlit Community Cloud)

1. Push the repository to GitHub (the vector index, `.env` and `.venv` are git-ignored).
2. On Streamlit Community Cloud, create an app from the repo, branch `main`, main file `app.py`.
3. In the app's **Settings → Secrets**, add `GEMINI_API_KEY = "..."`.
4. `app.py` builds the Chroma index on first start when `chroma_db/` is missing (the cloud filesystem is not persistent).

### Problems I hit while deploying, and the fixes

| Problem | What I saw | Fix |
|---|---|---|
| Commands run from the wrong folder | `.venv` activation failed; `git ls-files` said "not a git repository" | `cd` into the real project folder; `dir -Force` shows `.git` |
| Bloated, wrongly encoded `requirements.txt` | `pip freeze >` in PowerShell wrote a UTF-16 file with about 100 pinned packages | Replaced with 5 plain ASCII lines (`streamlit`, `chromadb`, `sentence-transformers`, `google-genai`, `python-dotenv`); checked with `git diff --stat` |
| Keeping the API key out of Git | Risk of committing `.env` | `.gitignore`; confirmed `git ls-files` lists no `.env`, `.venv` or `chroma_db`; read the variable *name* from `.env` without printing the key; stored the key as a Streamlit secret |
| First push needed authentication | Git opened a "Connect to GitHub" sign-in window | Signed in through the browser, then `git push -u origin main` |
| Vector index not in the repo | `chroma_db/` is ignored | App builds the index on first start; tested locally by renaming `chroma_db` |
| First cloud start crashed | ChromaDB raised `AttributeError` / `ValueError` inside `PersistentClient` while building the index | **Manage app → Reboot app**; it worked afterwards. Root cause not investigated, so a cold start could fail again |
| `ModuleNotFoundError: torchvision` in the logs | Appears in the cloud log panel and locally | Harmless noise (seems to come from Streamlit's file watcher inspecting optional modules); the app is unaffected. Locally, `--server.fileWatcherType none` hides it |
| Gemini `503 UNAVAILABLE` ("high demand") during evaluation | Script crashed mid-run | `ask_llm()` retries up to 6 times with growing waits, then returns `LLM_ERROR`, which the UI shows as a friendly message |

## Limitations and next steps

- Only 8 tutorial pages; English only; no conversation memory.
- Fixed-size character chunks can cut code blocks and sentences in the middle.
- The pages include `{* ... *}` placeholders for code examples that live in other files, so the example code itself is not searchable. Terminal blocks also carry some HTML noise.
- The distance threshold is crude (see Evaluation); hybrid search or a re-ranker is the obvious next experiment.
- Verify the remaining 16 evaluation cases against the docs and grow the hidden set.
- Free-tier hosting: cold starts are slow and the Gemini free tier can return 503s.

## Project structure

```
app.py            Streamlit UI (builds the index on first start)
answer.py         distance gate + Gemini answer + retry
retrieve.py       Chroma query (top chunks and distances)
ingest.py         load docs, chunk, embed, index
evaluate.py       runs the evaluation cases (dev / hidden)
data/             8 FastAPI tutorial pages
eval/             cases.jsonl and result files
test_llm.py       API smoke test
requirements.txt
```

## Author

Zarin Tasnim Shaily
[LinkedIn](https://www.linkedin.com/in/5ha1l72) | [GitHub](https://github.com/ztsprofessionalaiid7-alt)
