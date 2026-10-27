# FINN · Clarity, with a source

A mobile-first investment research prototype for the ENAM AI Engineer Build Challenge. FINN filters a model portfolio's exchange disclosures, watches configurable end-of-day thresholds, and researches any supported NSE ticker from primary documents.

## Run locally

Python 3.12+ recommended.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set GEMINI_API_KEY in .env. Never commit this file.
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. On the prepared Windows workspace, double-click **start.cmd**. Keep its window open while using FINN. If a server is already running on port 8000, use that server rather than starting a second copy.

For macOS/Linux, use `.venv/bin/python` instead. Only copy the example environment file on first setup; do not overwrite an existing key.

Get a free-tier Gemini key from [Google AI Studio](https://aistudio.google.com/apikey). The default model is `gemini-3.1-flash-lite`. Configure a free-tier project; FINN cannot determine whether a key has billing enabled. No paid fallback model is used. Without a key or when a provider fails, research shows clearly labelled primary-source excerpts instead of invented analysis.

## Two workflows

**Your brief — push:** default 24-hour digest, configurable through 30 days; category-based priority; routine disclosures collapsed; original exchange PDFs; saved filings; configurable absolute daily price move, volume multiple, and announcement categories. The app polls for new alerts while open. Optional browser notifications require permission. There is no background mobile push when the browser is closed.

**Research desk — pull:** arbitrary NSE symbols, including `M&M`; discovery through Screener's document directory; one annual report and up to four available transcripts; focused research lenses for promises/performance, business overview, and cash quality. Claims carry original PDF page links and exact quoted evidence. Unsupported comparisons are omitted and evidence gaps are explicit. The source index can contain multiple calls in a quarter, so four documents do not necessarily mean four fiscal quarters.

**Portfolio:** 18 businesses across banking, IT, healthcare, energy, autos, consumer, telecom, infrastructure, manufacturing and financial services. Size buckets are illustrative selection labels rather than live market-cap classifications. No positions or investment returns are invented. Four outside-portfolio examples are ASIANPAINT, PERSISTENT, KPITTECH and HAVELLS; the research engine does not special-case them.

## Data and architecture

```text
Yahoo daily chart → completed-session bars → price/volume alerts
NSE announcements → portfolio filter → deterministic category/priority → digest
Screener document links → primary PDFs → page text → bounded retrieval
                                               → Gemini → citation validation → research
SQLite cache ← successful prices, document text, feed, successful AI output
FastAPI endpoints → plain HTML/CSS/JS responsive interface
```

- **Price/volume:** Yahoo's public chart endpoint (`.NS`). Today's bar is excluded before 16:00 IST. A volume baseline uses up to 20 *previous* sessions; at least 10 are required for alerts. Prices and dates are shown explicitly. Corporate actions can affect unadjusted price moves; signals are prompts to investigate, not explanations.
- **Filings:** NSE corporate announcements for the last 30 days, filtered to the portfolio. If NSE fails, the app uses recent BSE links indexed by Screener and prominently labels coverage as partial. This fallback cannot guarantee all filings; its dates may have no time-of-day, so narrow windows are approximate. Failed refreshes retain prior successful data.
- **Research:** Screener is used only to discover annual report and transcript URLs. Screener commentary, news, broker notes, AI summaries and the model's outside company knowledge are not research inputs. PDFs are bounded to 30 MB and 500 pages. Scanned/image-only PDFs need OCR and are reported as unavailable.
- **Retrieval:** overlapping text chunks ranked by question-specific keywords, with a per-document quota to retain quarterly coverage. This is intentionally small and inspectable, without embeddings or a vector database. Relevant evidence can be missed; missing pairs are disclosed rather than padded.
- **AI:** one structured generation per uncached research lens. Exact quoted substrings and source IDs are validated before display. This validates quotations, not all semantics or financial arithmetic. Users should inspect the evidence before relying on an interpretation.
- **Efficiency:** prices cached 1 hour, document discovery 6 hours, PDF text 7 days, successful research 24 hours keyed by ticker/lens/model/evidence fingerprint. Provider requests have bounded concurrency. Default server-wide AI cap: 30 requests per UTC day. It counts attempts, including failures. No failed AI responses are cached.
- **Updates:** source refresh every 15 minutes while the server runs; foreground UI polling every minute. This is an EOD product, not a real-time trading terminal.
- **State:** SQLite stores shared market/research data. Preferences, saved filings and seen alert IDs are browser-local. Single-process prototype; no multi-user authentication, cross-device settings or multiple-worker support.
- **Secrets:** `.env` is ignored; keys are sent only server-side using a header and never returned by the app. User text is escaped in the interface. The local server binds to loopback by default.

`data/snapshot.json` is an actual dated public-data snapshot, not synthetic financial data. It seeds a fresh installation while live refresh starts; its original timestamps are preserved. No full company PDFs or API secrets are committed.

## Tests and live checks

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts/check_sources.py --snapshot
.venv\Scripts\python scripts/check_research.py INFY
.venv\Scripts\python scripts/check_examples.py
```

Unit/API tests cover baseline exclusion, threshold changes, sparse/zero data, symbol validation, classification, time windows, source discovery, fabricated citations and protected environment files. Live checks use public source hosts and, for synthesis, the configured AI key. `scripts/check_examples.py` exercises the four non-portfolio companies. Research availability depends on provider access and readable documents.

See [docs/DEMO.md](docs/DEMO.md) for a short demo path and [docs/BUILD_HISTORY.md](docs/BUILD_HISTORY.md) for the build conversation and decisions.

## Deliberate scope limits

This submission focuses on a working digest and source-grounded research. It does not implement automatic quarterly Revenue/EBITDA/PBT/PAT tables, incoming-executive biographies, trading, forecasts, portfolio return attribution, voice, OCR, or guaranteed four-quarter guidance scorecards. Those were examples in the brief, not a mandatory feature checklist. The comparison view appears only when both cited sides are available.

Next steps: chronological, metric-normalized extraction for guidance tracking; explicit reporting-period reconciliation; broader exchange adapter coverage; evaluation sets for financial claim support; durable scheduled ingestion and true push delivery.

## Optional later hosting

Local-only delivery was selected. `render.yaml` is prepared for a Render free web service. When ready, create a Blueprint from this repository and enter `GEMINI_API_KEY` as a secret. Do not paste it into the YAML. Free services can sleep after inactivity and have ephemeral storage: cache contents can disappear on redeploy, and scheduled refresh will not run while asleep. The included snapshot provides a dated starting point, not an always-on feed. [Render free-tier details](https://render.com/docs/free).

The ENAM submission requires a prototype, GitHub repository, AI build history and covering note. The local URL is not accessible to reviewers on other computers; deploy before submitting if they need a remote link.
