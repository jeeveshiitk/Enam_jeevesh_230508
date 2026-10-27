# AI build history

This project was built collaboratively with Codex on October 27, 2026.

The actual build conversation is available here:
https://chatgpt.com/s/cx_6ae07d7c116c81918d2d00b737f86a49

This is a point-in-time conversation snapshot. Preserve/export the final chat as well if further development continues. This file is a decision log, not a substitute for the actual conversation.

## Decisions made with the user

- Read the main brief before implementation and asked about the companion reference, scope, platform, providers, company selection and delivery.
- User supplied the reference and selected two focused workflows, free providers, an agent-chosen diverse portfolio and stack, immediate implementation, and the supplied GitHub repository.
- Selected a Python/FastAPI backend for document processing with a buildless, responsive frontend.
- Used the reference announcement taxonomy as deterministic, transparent classification rules. Kept optional examples out of the mandatory scope.
- Created 18 portfolio selections and four research examples outside the portfolio. Replaced an unavailable auto-company symbol with MARUTI after live source testing.
- Moved the user's API key from the example environment file into ignored `.env` without displaying or committing it.
- Tested public exchange and price adapters. Retained dated successful data, exposed provider failure status and implemented an explicitly partial fallback.
- Implemented primary-PDF discovery, bounded extraction, per-document retrieval, structured AI output and exact-quote citation checks. Added safe abstention and evidence-gap reporting.
- Corrected a document-directory selector after live HTML inspection. It initially missed transcripts nested below the heading.
- Switched from an unavailable default model to a supported free-tier model after querying the key's available models. Added structured output and increased the output bound after truncated-response tests.
- Tested alert arithmetic, data boundaries, citation rejection and API behavior. Checked the working interface at desktop and phone widths.
- User selected local-only delivery. Hosting configuration is included for future use; no public deployment was requested after that choice.

No subagents were used. Public market data and company sources inform the app; coding-agent output is not treated as financial evidence.
