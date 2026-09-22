# Context — meeting-transcript-analyzer

## Project Type
Greenfield — no existing codebase.

## Purpose
Enable the team to quickly understand what was discussed in a meeting, the important points, and subsequent action items **without re-reading the full transcript**. The system must summarize meeting content without losing context, and especially make follow-up actions visible.

## Execution Model
On-demand: user uploads a transcript file → system analyzes → structured output returned immediately.

## Data Sensitivity
Internal-only — team meetings, not confidential but not public.

## Volume
Low initially (<10 meetings/month), but system must be designed for future team expansion.

## Input
- **Format:** Plain text (.txt) files only
- **Language:** Mixed English and Turkish expected (output language follows the dominant language in the transcript)
- **Size:** Up to 50 pages, typical processing target ≤30 pages

## Output
- **Formats:** Markdown (MUST) and/or PDF (SHOULD)
- **Structure:** Topics with summaries + a dedicated action items section
- **Language:** Follows the dominant language of the input transcript

## Users
- Primary: Internal team members who participated in or need meeting results

## Constraints
- Data sensitivity: Internal-only
- Execution: On-demand (upload → immediate output)
- Uncertainty: Flag uncertain items for manual review (MUST)
- No external integrations in v1

## Out of Scope (v1)
- Meeting recording / speech-to-text
- Batch/scheduled processing
- Miro board integration
- Sharing with external parties
- PDF output (SHOULD-have, may be deferred)

## Deferred Decisions
- LLM provider (proprietary API vs open-source) — deferred to architecture phase; must support English + Turkish

---
**Last updated:** 2025-09-17
