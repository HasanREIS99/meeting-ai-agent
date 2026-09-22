# Services — meeting-transcript-analyzer

**Slug:** meeting-transcript-analyzer
**Source FRD Version:** 1.0
**Date:** 2025-09-17
**Author:** hasancan.corut
**Protocol:** REST
**Status:** DRAFT

---

## 1. API Overview

The meeting transcript analyzer exposes a REST API for internal team members to upload transcripts, trigger analysis, and retrieve results. The architecture is a single monolithic service for v1 (per architect review note A-001) with a process-and-discard data pattern.

**Authentication:** Standard session-based or token-based auth (configurable per NFR-S-004, deferred to architecture phase)
**Transport:** TLS 1.2+ (NFR-S-003)
**Content Type:** multipart/form-data for uploads, application/json for results
**Error Response Format:** RFC 7807 Problem Details

---

## 2. Endpoints / Operations

### 2.1 Transcript Analysis

| EP-ID | HTTP Method | Path | Operation | Related FR | EARS Pattern |
|---|---|---|---|---|---|
| EP-001 | POST | /api/v1/analyze | Upload a transcript file and trigger analysis; return results synchronously | FR-001, FR-007, FR-008, FR-009, FR-011, FR-012, FR-015 | Event-driven |
| EP-002 | POST | /api/v1/health | Health check endpoint for load balancer / readiness probes | — | — |

### 2.2 File Validation

| EP-ID | HTTP Method | Path | Operation | Related FR | EARS Pattern |
|---|---|---|---|---|---|
| EP-003 | POST | /api/v1/validate | Validate a file before upload (optional pre-check to avoid large uploads that will be rejected) | FR-002, FR-003, FR-017 | Unwanted/Event-driven |

### 2.3 Access Control

| EP-ID | HTTP Method | Path | Operation | Related FR | EARS Pattern |
|---|---|---|---|---|---|
| EP-004 | POST | /api/v1/auth/login | Authenticate a user (implementation TBD, per OP-006) | FR-013 | State-driven |
| EP-005 | POST | /api/v1/auth/logout | Invalidate session | FR-013 | State-driven |
| EP-006 | GET | /api/v1/auth/verify | Verify current authentication status | FR-013, FR-014 | State-driven |

---

## 3. Data Models

### 3.1 TranscriptUploadRequest

```yaml
TranscriptUploadRequest:
  type: object
  required:
    - file
    - metadata
  properties:
    file:
      type: string
      format: binary
      description: The .txt transcript file to upload
    metadata:
      $ref: '#/components/schemas/TranscriptMetadata'
```

### 3.2 TranscriptMetadata

```yaml
TranscriptMetadata:
  type: object
  properties:
    title:
      type: string
      description: Optional human-readable title for this transcript
    meeting_date:
      type: string
      format: date
      description: Date of the meeting (YYYY-MM-DD)
    participants:
      type: array
      items:
        type: string
      description: List of participant names (optional, for reference)
```

### 3.3 TranscriptResult

```yaml
TranscriptResult:
  type: object
  required:
    - meetingTitle
    - language
    - topicClusters
    - actionItems
    - processingTime
    - markdownContent
  properties:
    meetingTitle:
      type: string
      description: Auto-generated or user-provided meeting title
    language:
      type: string
      enum: [en, tr, mixed]
      description: Detected primary language
    topicClusters:
      type: array
      items:
        $ref: '#/components/schemas/TopicCluster'
      description: List of identified topic clusters
    actionItems:
      type: array
      items:
        $ref: '#/components/schemas/ActionItem'
      description: List of extracted action items
    uncertainFindings:
      type: array
      items:
        $ref: '#/components/schemas/UncertainFinding'
      description: Items flagged as uncertain
    processingTime:
      type: number
      format: float
      description: Time taken to process in seconds
    markdownContent:
      type: string
      description: Full Markdown-formatted output
    generatedAt:
      type: string
      format: date-time
      description: When this analysis was generated
```

### 3.4 TopicCluster

```yaml
TopicCluster:
  type: object
  required:
    - title
    - summary
  properties:
    title:
      type: string
      description: Topic cluster title
    summary:
      type: string
      description: 1-2 sentence summary
    confidence:
      type: number
      format: float
      minimum: 0
      maximum: 1
      description: Confidence score (0-1)
    uncertain:
      type: boolean
      description: True if this finding is flagged as uncertain
    keywords:
      type: array
      items:
        type: string
      description: Keywords or tags associated with this topic
```

### 3.5 ActionItem

```yaml
ActionItem:
  type: object
  required:
    - description
  properties:
    description:
      type: string
      description: The action item description
    assignee:
      type: string
      nullable: true
      description: Person responsible for the action; "unspecified" if not stated
    deadline:
      type: string
      format: date
      nullable: true
      description: Deadline for the action; "unspecified" if not stated
    confidence:
      type: number
      format: float
      minimum: 0
      maximum: 1
      description: Confidence score (0-1)
    uncertain:
      type: boolean
      description: True if this finding is flagged as uncertain
```

### 3.6 UncertainFinding

```yaml
UncertainFinding:
  type: object
  required:
    - type
    - description
  properties:
    type:
      type: string
      enum: [topic, summary, action_item]
      description: Type of uncertain finding
    description:
      type: string
      description: Description of what is uncertain
```

### 3.7 ErrorResponse

```yaml
ErrorResponse:
  type: object
  required:
    - type
    - title
    - status
    - detail
  properties:
    type:
      type: string
      description: Error type URI
    title:
      type: string
      description: Short error title
    status:
      type: integer
      description: HTTP status code
    detail:
      type: string
      description: Human-readable error message
    instance:
      type: string
      description: Error instance identifier
```

### 3.8 ValidationResponse

```yaml
ValidationResponse:
  type: object
  required:
    - valid
    - errors
  properties:
    valid:
      type: boolean
      description: Whether the file passes validation
    errors:
      type: array
      items:
        type: string
      description: List of validation errors (empty if valid)
```

---

## 4. Integration Notes

### 4.1 External Systems

| System | Integration | Notes |
|---|---|---|
| LLM Provider | API call | TBD (OP-003); REST API to a third-party LLM service or self-hosted LLM. Protocol: HTTPS + JSON. Auth: TBD (API key, OAuth, or local). NFR-R-003 requires this layer to be modular. |
| Miro | None (future) | Not in scope for v1. NFR-R-004 requires the architecture to support future Miro MCP integration with minimal changes. |

### 4.2 Protocol

- **REST/HTTP** throughout
- **JSON** for all request/response bodies
- **TLS 1.2+** for all external-facing traffic (NFR-S-003)
- **Content negotiation:** application/json

### 4.3 Authentication

- **Mechanism:** Configurable (NFR-S-004, OP-006) — TBD pending architecture evaluation
- **v1 recommendation:** Session-based auth with HTTP cookies or bearer token (JWT)
- **Authorization:** Internal team members only (FR-014) — simple role-based access
- **Token lifecycle:** Configurable, TBD pending architecture phase (OP-006)

### 4.4 Data Handling

- **Transcript storage:** Minimal for v1 (NFR-S-002). Transcript is processed in-memory and discarded after analysis. No persistent storage of source transcripts.
- **Result storage:** TBD pending architecture phase — results may be returned in the response without persistence, or stored temporarily for access (OP-001 resolution).
- **Logging:** Transcript content must never be logged (NFR-R-002). Only metadata (file size, processing time, user ID) may be logged.

### 4.5 Error Handling

| Error Type | HTTP Status | Related FR | Description |
|---|---|---|---|
| Unsupported File Type | 400 | FR-002 | File is not .txt |
| File Too Large | 413 | FR-003 | Transcript exceeds 50 pages |
| Empty File | 400 | FR-017 | Transcript is empty |
| LLM API Failure | 502 | FR-015 | External LLM provider unavailable or returned an error |
| Authentication Required | 401 | FR-013 | User is not authenticated |
| Access Denied | 403 | FR-014 | User is authenticated but not an internal team member |
| Server Error | 500 | FR-015 | Unexpected server error |
| Timeout | 408 | NFR-P-001 | Processing exceeded reasonable time |

---

## 5. Architecture Diagram (Text)

```
┌──────────┐      HTTPS (TLS 1.2+)      ┌──────────────────┐
│  Browser  │ ─────────────────────────→ │   API Gateway /  │
│  (Client) │ ←───────────────────────── │   Load Balancer  │
└──────────┘      JSON + multipart      └────────┬─────────┘
                                                  │
                                              ┌────▼─────┐
                                              │ Transcript│
                                              │ Analyzer  │
                                              │ Service   │
                                              └────┬──────┘
                                                   │
                                              ┌────▼─────┐
                                              │  LLM      │
                                              │  Provider │
                                              │  (TBD)   │
                                              └──────────┘
```

---

## 6. Traceability Matrix

| EP-ID | Endpoint | Related FRs | Covered |
|---|---|---|---|
| EP-001 | POST /api/v1/analyze | FR-001, FR-007, FR-008, FR-009, FR-011, FR-012, FR-015 | ✅ Full analysis pipeline |
| EP-002 | POST /api/v1/health | — | ✅ Health check |
| EP-003 | POST /api/v1/validate | FR-002, FR-003, FR-017 | ✅ File validation |
| EP-004 | POST /api/v1/auth/login | FR-013 | ✅ Authentication |
| EP-005 | POST /api/v1/auth/logout | FR-013 | ✅ Session invalidation |
| EP-006 | GET /api/v1/auth/verify | FR-013, FR-014 | ✅ Access verification |

**17 FRs covered by 6 endpoints.**

---

*Greenfield project — no existing services to integrate with.*
