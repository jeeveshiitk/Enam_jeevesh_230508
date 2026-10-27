# Covering note draft

To: assessment@enam.com

Subject: ENAM - IIT screening - 2027

Hello ENAM team,

I built FINN around two workflows: a prioritised portfolio brief and a primary-source research desk.

The brief follows 18 NSE companies across sectors and sizes, collapses routine disclosures, and lets the investor choose price, volume and announcement thresholds. Each disclosure links back to the original filing. Research accepts NSE symbols beyond the demo portfolio and reads annual reports and earnings-call transcripts, with quoted evidence and PDF page links.

My main trade-off was to keep the system small and inspectable: FastAPI, a lightweight responsive interface, deterministic filing triage, SQLite caching and a free-tier language model for research synthesis. It distinguishes missing evidence from a negative finding, and omits promise/outcome comparisons that do not pass citation checks.

I deliberately left out full quarterly-results extraction, executive biographies, voice and closed-browser mobile push. Next I would improve chronological guidance tracking, metric reconciliation and claim-support evaluation, and add durable scheduled ingestion.

Repository: https://github.com/jeeveshiitk/Enam_jeevesh_230508

AI build history: https://chatgpt.com/s/cx_6ae07d7c116c81918d2d00b737f86a49

Prototype: [Add a deployed link before submission, or arrange a local demo. The current prototype is local-only.]

Regards,
Jeevesh

---
This is an unsent draft. Verify the prototype link and include the final build-history snapshot before submitting.
