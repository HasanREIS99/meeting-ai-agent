# Business Requirements Document (BRD) — meeting-transcript-analyzer

**Project:** meeting-ai-agent
**Slug:** meeting-transcript-analyzer
**Version:** 1.0
**Date:** 2025-09-17
**Author:** hasancan.corut
**Status:** DRAFT

---

## 1. Executive Summary

This document defines the business and user requirements for a **meeting transcript analyzer** — a greenfield internal tool designed to help team members quickly understand meeting outcomes without re-reading full transcripts. The system accepts a plain text transcript file as input, analyzes it using AI (LLM-based), and produces a structured output containing topic clusters, summaries, and action items.

**Key benefits:**
- Saves time by eliminating the need to re-read full meeting transcripts
- Surfaces action items prominently so they are not missed
- Provides a clear, organized view of what was discussed and decided
- Supports both English and Turkish transcripts

---

## 2. Scope

### In Scope (v1)
- Upload of plain text (.txt) transcript files
- AI-powered analysis to identify topic clusters
- Generation of 1-2 sentence summaries per topic cluster
- Extraction of action items with assignees and deadlines
- Markdown output format
- Internal team access only
- Support for mixed English/Turkish transcripts (output language follows the dominant language in the transcript)

### Out of Scope (v1)
- Meeting recording / speech-to-text (transcripts are provided as input)
- PDF output format (SHOULD-have, may be deferred)
- Batch/scheduled processing
- Miro board integration
- Sharing with external parties
- Automated language detection and translation

---

## 3. Stakeholders

| Role | Responsibility |
|---|---|
| Internal team members | Primary users — upload transcripts, review analysis output, act on action items |

---

## 4. Business Requirements

| ID | Requirement | MoSCoW |
|---|---|---|
| BR-001 | Reduce the time investment required for team members to understand meeting outcomes after the meeting ends. | MUST |
| BR-002 | Enable quick and organized identification of action items from meeting transcripts so that follow-up work is not missed. | MUST |

---

## 5. User Requirements

| ID | Requirement | MoSCoW |
|---|---|---|
| UR-001 | WHEN a user uploads a .txt transcript file, the system shall process the file for analysis. | MUST |
| UR-002 | WHEN processing completes, the system shall produce topic clusters from the transcript content. | MUST |
| UR-003 | WHERE topic clusters exist, the system shall produce a 1-2 sentence summary for each topic cluster. | MUST |
| UR-004 | WHEN processing completes, the system shall identify action items, including assignees and deadlines when mentioned in the transcript. | MUST |
| UR-005 | IF a finding (topic, summary, or action item) cannot be identified with sufficient confidence, THEN the system shall flag it as uncertain. | MUST |
| UR-006 | WHEN processing completes, the system shall output the analysis result in Markdown format. | MUST |
| UR-007 | WHERE PDF export is supported, the system shall generate a PDF version of the output. | SHOULD |
| UR-008 | WHILE a user is accessing the system, access to analysis results shall be restricted to internal team members only. | MUST |
| UR-009 | WHILE analyzing a transcript of up to 50 pages, the system shall complete processing within a reasonable time for interactive use. | SHOULD |
| UR-010 | WHEN a transcript is processed, the system shall support transcripts that contain mixed English and Turkish language content. | MUST |
| UR-011 | WHERE the transcript is predominantly in one language, the system shall produce output in that language. | SHOULD |

---

## 6. Non-Functional Requirements

| ID | Requirement | MoSCoW |
|---|---|---|
| NFR-001 | The system shall be designed for horizontal scalability to support future team expansion beyond the initial small team. | MUST |
| NFR-002 | The system shall handle transcripts with up to 50 pages of text without errors. | SHOULD |
| NFR-003 | The system shall process a typical meeting transcript (up to 30 pages) within 2 minutes. | SHOULD |
| NFR-004 | The system shall follow standard internal data handling practices for internal-only data. | MUST |

---

## 7. EARS Pattern Classification

| UR ID | Requirement (EARS) | EARS Pattern |
|---|---|---|
| UR-001 | WHEN a user uploads a .txt transcript file, the system shall process the file for analysis. | Event-driven |
| UR-002 | WHEN processing completes, the system shall produce topic clusters from the transcript content. | Event-driven |
| UR-003 | WHERE topic clusters exist, the system shall produce a 1-2 sentence summary for each topic cluster. | Optional |
| UR-004 | WHEN processing completes, the system shall identify action items, including assignees and deadlines when mentioned in the transcript. | Event-driven |
| UR-005 | IF a finding cannot be identified with sufficient confidence, THEN the system shall flag it as uncertain. | Unwanted |
| UR-006 | WHEN processing completes, the system shall output the analysis result in Markdown format. | Event-driven |
| UR-007 | WHERE PDF export is supported, the system shall generate a PDF version of the output. | Optional |
| UR-008 | WHILE a user is accessing the system, access to analysis results shall be restricted to internal team members only. | State-driven |
| UR-009 | WHILE analyzing a transcript of up to 50 pages, the system shall complete processing within a reasonable time for interactive use. | State-driven |
| UR-010 | WHEN a transcript is processed, the system shall support transcripts that contain mixed English and Turkish language content. | Event-driven |
| UR-011 | WHERE the transcript is predominantly in one language, the system shall produce output in that language. | Optional |

---

## 8. Open Questions / TBD

| Item | Description | Notes |
|---|---|---|
| TBD-001 | LLM provider selection | Deferred to architecture phase — architect will evaluate proprietary API vs open-source options. Must support English + Turkish. |
| TBD-002 | Authentication mechanism for internal team access | Standard internal authN/authZ planned; specific mechanism TBD pending architecture phase |

---

## 9. Assumptions

1. Meeting transcripts are provided as pre-existing text files (not produced by this system).
2. Transcripts are primarily in English and/or Turkish (mixed-language content is expected).
3. Internal team access can be satisfied with standard internal authentication mechanisms.
4. The system is intended as a team tool, not a public or multi-tenant SaaS product.
5. Action items may or may not have explicit assignees or deadlines — only extract them when mentioned in the transcript.

---

*Greenfield project — AS-IS / TO-BE / GAP sections are not applicable.*
