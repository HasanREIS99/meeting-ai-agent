# Executive Summary — meeting-transcript-analyzer

**Date:** 2025-09-17
**Author:** hasancan.corut
**Status:** DRAFT

---

## Problem

Team members spend significant time re-reading full meeting transcripts after meetings to understand what was discussed, what decisions were made, and what follow-up actions are required. This is inefficient and error-prone — action items can be missed.

## Solution

A meeting transcript analyzer that accepts a plain text transcript file as input and automatically produces a structured analysis output containing:

- **Topic clusters** — the main subjects discussed in the meeting
- **Topic summaries** — 1-2 sentence summaries for each topic cluster
- **Action items** — identified tasks with assignees and deadlines, displayed prominently

Output is provided in Markdown format (PDF as a SHOULD-have).

## Key Requirements (MUST-have)

1. Upload a .txt transcript file
2. Identify topic clusters automatically
3. Summarize each topic cluster (1-2 sentences)
4. Extract action items with assignees and deadlines
5. Flag uncertain findings for manual review
6. Output in Markdown format
7. Restrict access to internal team members only
8. Designed for horizontal scalability

## Exclusions for v1

- Meeting recording / speech-to-text
- Batch processing
- Miro board integration
- PDF output (SHOULD-have, may be deferred)

## Expected Benefits

- **Time savings:** No need to re-read full transcripts
- **Action visibility:** Action items are prominently surfaced
- **Organization:** Structured output makes it easy to scan and share

## Next Steps

1. Architecture evaluation — determine application form factor, technology stack, and LLM provider
2. Functional & non-functional requirements (FRD/NFRD)
3. Service architecture and UI design
4. Test planning
