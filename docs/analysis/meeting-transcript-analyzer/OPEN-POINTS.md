# Open Points — meeting-transcript-analyzer

## OP-001 · blocker · deferred
- **Raised by:** intake · 2025-09-17
- **Q:** Are meeting transcripts **confidential/sensitive** data or **internal-only** or **public**?
- **Why it matters:** architecture for data at rest/in transit, security requirements, LLM provider choice
- **Disposition:** User chose **internal-only**. Security requirements will include standard internal data handling.
- **Impact:** Standard authN/authZ will be sufficient for v1; no classified data compliance needed.
- **Impact markers:** NFR-S-001, NFR-S-002

## OP-002 · blocker · deferred
- **Raised by:** intake · 2025-09-17
- **Q:** On-demand or scheduled/batch execution?
- **Why it matters:** application form factor (web vs CLI vs worker)
- **Disposition:** User chose **on-demand**. Upload → immediate output.
- **Impact:** Application must support interactive input; batch mode is out of scope for v1.
- **Impact markers:** None in FRD — handled explicitly in scope section.

## OP-003 · major · deferred
- **Raised by:** intake · 2025-09-17
- **Q:** Which LLM powers the transcript analysis? Proprietary API vs open-source?
- **Why it matters:** tech stack, deployment model, cost model, privacy implications
- **Disposition:** User confirmed **keep deferred** — architect will evaluate both options and recommend. Must support English + Turkish.
- **Impact:** LLM-specific framework/SDK choices are provisional until architecture review.
- **Impact markers:** ⚠ Assumption — OP-003 (FRD FR-004, NFR-R-003)

## OP-004 · major · deferred
- **Raised by:** intake · 2025-09-17
- **Q:** Expected volume of meetings to analyze?
- **Why it matters:** scalability requirements, infrastructure decisions
- **Disposition:** User confirmed **keep deferred** — design for horizontal scalability from start; exact size TBD.
- **Impact:** Architecture should be horizontally scalable from the start, even if v1 only needs single-instance deployment.
- **Impact markers:** ⚠ Assumption — OP-004 (FRD NFR-P-003)

## OP-005 · major · deferred
- **Raised by:** intake · 2025-09-17
- **Q:** Is Miro board generation a v1 requirement or future?
- **Why it matters:** scoping the first deliverable
- **Disposition:** User confirmed **keep deferred / out of scope for v1**. Miro MCP integration considered later.
- **Impact:** v1 output is Markdown only. No external integrations in v1 scope.
- **Impact markers:** NFR-R-004

## OP-006 · minor · deferred
- **Raised by:** review · 2025-09-17
- **Q:** Authentication mechanism for internal team access — TBD in BRD §8 with no register entry.
- **Why it matters:** security architecture decisions depend on this
- **Disposition:** Deferred to **architecture phase** — same as TBD-001 (LLM provider + authN are both architecture concerns)
- **Impact:** authN/authZ specifics are provisional until architecture review.
- **Impact markers:** ⚠ Assumption — OP-006 (FRD FR-013, NFR-S-004)
