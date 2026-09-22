# Functional Requirements Document (FRD) — meeting-transcript-analyzer

**Project:** meeting-ai-agent
**Slug:** meeting-transcript-analyzer
**Source BRD Version:** 1.0
**Date:** 2025-09-17
**Author:** hasancan.corut
**Status:** DRAFT

---

## 1. Introduction

This Functional Requirements Document (FRD) decomposes the Business Requirements Document (BRD v1.0) into testable functional and non-functional requirements for the **meeting transcript analyzer**. Each requirement is written in an EARS pattern for testability and traced to its source BRD element.

**Scope:** v1 — on-demand transcript analysis for internal team members.
**Language support:** Mixed English and Turkish transcripts (UR-010); output language follows the dominant language of the input.
**Input format:** Plain text (.txt) files only.
**Language handling:** Automated language detection added as an implicit in-scope capability (C-002 resolution).

---

## 2. Functional Requirements

Each FR is derived from one or more URs, written in an EARS pattern, and labeled with the pattern type.

### 2.1 Transcript Upload

| ID | Requirement | EARS Pattern | Source |
|---|---|---|---|
| FR-001 | WHEN a user selects a .txt transcript file for upload, the system shall accept and store the file for processing. | Event-driven | UR-001, BR-001 |
| FR-002 | IF the uploaded file is not a plain text (.txt) file, THEN the system shall reject the upload and display an error message indicating that only .txt files are accepted. | Unwanted | UR-001 |
| FR-003 | WHEN a transcript file exceeds 50 pages of text, the system shall reject the upload and display an error message explaining the limit. | Unwanted | UR-001, C-001 resolution |

### 2.2 Language Handling

| ID | Requirement | EARS Pattern | Source |
|---|---|---|---|
| FR-004 | WHEN a transcript is processed, the system shall detect the primary language (English or Turkish) of the input text. | Event-driven | UR-010, C-002 resolution |
| FR-005 | WHERE the transcript is predominantly in one language, the system shall produce the output (topic clusters, summaries, action items) in that language. | Optional | UR-011 |
| FR-006 | WHERE the transcript contains mixed-language content (English and Turkish), the system shall produce the output in the dominant language. | Optional | UR-010, UR-011 |

### 2.3 Topic Identification & Summarization

| ID | Requirement | EARS Pattern | Source |
|---|---|---|---|
| FR-007 | WHEN processing completes, the system shall identify distinct topic clusters from the transcript content. | Event-driven | UR-002, BR-001 |
| FR-008 | WHERE topic clusters exist, the system shall produce a 1-2 sentence summary for each topic cluster. | Optional | UR-003, BR-001 |

### 2.4 Action Item Extraction

| ID | Requirement | EARS Pattern | Source |
|---|---|---|---|
| FR-009 | WHEN processing completes, the system shall identify action items mentioned in the transcript, including assignees and deadlines when they are explicitly stated. | Event-driven | UR-004, BR-002 |
| FR-010 | IF an action item has no explicitly stated assignee or deadline, the system shall include the action item with those fields marked as "unspecified." | Unwanted | UR-004 |

### 2.5 Uncertainty Flagging

| ID | Requirement | EARS Pattern | Source |
|---|---|---|---|
| FR-011 | IF a finding (topic, summary, or action item) cannot be identified with sufficient confidence by the analysis engine, THEN the system shall flag it with an "uncertain" indicator in the output. | Unwanted | UR-005 |

### 2.6 Output Generation

| ID | Requirement | EARS Pattern | Source |
|---|---|---|---|
| FR-012 | WHEN processing completes, the system shall output the analysis result in Markdown format with: (a) topic clusters with summaries, (b) a dedicated action items section, (c) uncertainty indicators where applicable. | Event-driven | UR-006, BR-001, BR-002 |

### 2.7 Access Control

| ID | Requirement | EARS Pattern | Source |
|---|---|---|---|
| FR-013 | WHILE a user is interacting with the system, the system shall require authentication before granting access to any analysis features. | State-driven | UR-008 |
| FR-014 | WHILE the system is running, the system shall restrict access to analysis results and transcript files to authenticated internal team members only. | State-driven | UR-008, BR-001 |

### 2.8 Error Handling

| ID | Requirement | EARS Pattern | Source |
|---|---|---|---|
| FR-015 | IF the analysis engine fails to process a transcript (e.g., API error, empty file), THEN the system shall display a user-friendly error message and offer a retry option. | Unwanted | UR-001 |
| FR-016 | IF the uploaded transcript file is empty, THEN the system shall reject processing with a clear message. | Unwanted | UR-001 |

---

## 3. Non-Functional Requirements

### 3.1 Performance & Scalability

| ID | Requirement | Category | Source | Measurable |
|---|---|---|---|---|
| NFR-P-001 | WHILE analyzing a transcript of up to 30 pages, the system shall complete processing within 2 minutes. | Performance | UR-009, NFR-003 | ≤ 2 min for ≤ 30 pages |
| NFR-P-002 | WHILE processing a transcript of up to 50 pages, the system shall complete within 5 minutes. | Performance | NFR-002 | ≤ 5 min for ≤ 50 pages |
| NFR-P-003 | The system shall be designed for horizontal scalability to support future team expansion beyond the initial small team. ⚠ Assumption — OP-004 | Scalability | NFR-001 | — |
| NFR-P-004 | The system shall handle concurrent uploads from at least 5 users simultaneously. | Performance | — | 5 concurrent users |
| NFR-P-005 | WHEN a transcript exceeds 50 pages of text, the system shall reject the upload and display an error message explaining the limit. | Performance | C-001 resolution | — |

### 3.2 Security & Privacy

| ID | Requirement | Category | Source | Measurable |
|---|---|---|---|---|
| NFR-S-001 | The system shall follow standard internal data handling practices for internal-only data. | Security | NFR-004, OP-001 | — |
| NFR-S-002 | In v1, the system shall minimize storage of transcript files and analysis results; a data retention policy shall be defined during the architecture/security evaluation phase. ⚠ Assumption — OP-001 | Privacy | OP-001, C-004 resolution | TBD (v1 = minimal) |
| NFR-S-003 | Data in transit between client and server shall be encrypted using TLS 1.2 or higher. | Security | OP-001 | TLS 1.2+ |
| NFR-S-004 | Authentication mechanisms shall be configurable; specific implementation TBD pending architecture evaluation. ⚠ Assumption — OP-006 | Security | OP-006 | TBD |

### 3.3 Usability & Accessibility

| ID | Requirement | Category | Source | Measurable |
|---|---|---|---|---|
| NFR-U-001 | The system shall provide a clear user interface where users can upload a transcript, view processing progress, and access the output document. | Usability | UR-001, UR-006 | — |
| NFR-U-002 | Processing status (uploading, analyzing, complete, failed) shall be visible to the user at all times. | Usability | UR-001 | — |
| NFR-U-003 | The output document shall be structured with clear headings, sections, and visual hierarchy suitable for scanning. | Usability | BR-001 | — |

### 3.4 Reliability & Maintainability

| ID | Requirement | Category | Source | Measurable |
|---|---|---|---|---|
| NFR-R-001 | The system shall gracefully handle API failures from the LLM provider and offer a retry mechanism. | Reliability | FR-015 | — |
| NFR-R-002 | The system shall log analysis errors with sufficient detail for debugging, without exposing sensitive transcript content in logs. | Reliability | NFR-S-001 | — |
| NFR-R-003 | The system architecture shall support modular replacement of the LLM component without requiring changes to other system layers. ⚠ Assumption — OP-003 | Maintainability | OP-003 | — |
| NFR-R-004 | The system shall be designed so that new output formats and integrations (e.g., PDF, later Miro MCP) can be added with minimal changes to core analysis logic. | Maintainability | OP-005 | — |

---

## 4. ⚠ Conflicts & Gaps

| ID | Type | Description | Status |
|---|---|---|---|
| C-001 | Resolved | FR-003 had ambiguous behavior for >50 pages. **Resolved:** System rejects with error message (user choice). | ✅ Resolved |
| C-002 | Resolved | "Language detection out of scope" vs FR-004 requires it. **Resolved:** Language detection added as implicit in-scope capability. | ✅ Resolved |
| C-003 | Resolved | PDF export conflict: SHOULD-have vs out of scope. **Resolved:** PDF is out of scope for v1. | ✅ Resolved |
| C-004 | Resolved | Retention policy TBD — proposed 30 days. **Resolved:** Minimize storage for v1; retention policy deferred to architecture/security evaluation. | ✅ Resolved |

**No unresolved conflicts or gaps.**

---

## 5. Traceability Matrix

| FR/NFR ID | Description | Source BR | Source UR | EARS Pattern | Status |
|---|---|---|---|---|---|
| FR-001 | File upload & storage | BR-001 | UR-001 | Event-driven | ✅ |
| FR-002 | Reject non-.txt files | BR-001 | UR-001 | Unwanted | ✅ |
| FR-003 | Reject >50 pages | BR-001 | UR-001 | Unwanted | ✅ |
| FR-004 | Detect primary language | — | UR-010 | Event-driven | ✅ |
| FR-005 | Output in dominant language | — | UR-011 | Optional | ✅ |
| FR-006 | Handle mixed-language | — | UR-010, UR-011 | Optional | ✅ |
| FR-007 | Identify topic clusters | BR-001 | UR-002 | Event-driven | ✅ |
| FR-008 | Summarize topics | BR-001 | UR-003 | Optional | ✅ |
| FR-009 | Extract action items | BR-002 | UR-004 | Event-driven | ✅ |
| FR-010 | Handle unspecified assignees | — | UR-004 | Unwanted | ✅ |
| FR-011 | Flag uncertain findings | — | UR-005 | Unwanted | ✅ |
| FR-012 | Markdown output | BR-001, BR-002 | UR-006 | Event-driven | ✅ |
| FR-013 | Authentication requirement | — | UR-008 | State-driven | ✅ |
| FR-014 | Access restriction | — | UR-008 | State-driven | ✅ |
| FR-015 | Handle analysis failures | — | UR-001 | Unwanted | ✅ |
| FR-016 | Handle empty files | — | UR-001 | Unwanted | ✅ |
| NFR-P-001 | ≤ 2 min for ≤ 30 pages | NFR-003 | UR-009 | State-driven | ✅ |
| NFR-P-002 | ≤ 5 min for ≤ 50 pages | NFR-002 | — | State-driven | ✅ |
| NFR-P-003 | Horizontal scalability | NFR-001 | — | — | ⚠ OP-004 |
| NFR-P-004 | 5 concurrent users | — | — | — | — |
| NFR-P-005 | Reject >50 pages (NFR) | C-001 | — | Unwanted | ✅ |
| NFR-S-001 | Internal data handling | NFR-004 | — | — | ✅ |
| NFR-S-002 | Minimal v1 storage | OP-001 | — | — | ⚠ OP-001 |
| NFR-S-003 | TLS encryption | OP-001 | — | — | ✅ |
| NFR-S-004 | Configurable authN | OP-006 | — | — | ⚠ OP-006 |
| NFR-U-001 | Clear UI | — | UR-001, UR-006 | — | ✅ |
| NFR-U-002 | Processing status visibility | — | UR-001 | — | ✅ |
| NFR-U-003 | Structured output | BR-001 | — | — | ✅ |
| NFR-R-001 | Graceful API failure | — | FR-015 | — | ✅ |
| NFR-R-002 | Secure logging | — | NFR-S-001 | — | ✅ |
| NFR-R-003 | Modular LLM replacement | OP-003 | — | — | ⚠ OP-003 |
| NFR-R-004 | Extensible output formats | OP-005 | — | — | ✅ |

---

*Greenfield project — AS-IS / TO-BE / GAP sections are not applicable.*
*All 4 conflicts resolved during refinement phase.*
