# Effort Estimate — meeting-transcript-analyzer

**Project:** meeting-ai-agent
**Slug:** meeting-transcript-analyzer
**Source FRD Version:** 1.0
**Date:** 2025-09-17
**Author:** hasancan.corut
**Status:** DRAFT

---

## 1. Method & Assumptions

### Estimation Method
**Fibonacci Story Points** (1, 2, 3, 5, 8, 13)

### Size-to-Effort Conversion
**Assumption:** 1 Story Point ≈ 0.5 ideal days (4 hours of focused work)
*This assumption is based on a small, experienced team. Adjust if your team's velocity differs.*

### Team Context
- **Greenfield project** — no legacy code, no migrations
- **Small team** — likely 1-2 developers (internal team tool)
- **Language stack:** TBD pending architecture phase (estimated assuming Python or Node.js)
- **LLM provider:** TBD pending architecture phase (estimated assuming a standard REST API integration)

---

## 2. Feature Groups & Estimates

### Group 1: Upload & Validation
| FR ID | Description | Story Points | Rationale |
|---|---|---|---|
| FR-001 | File upload & storage | 3 | Standard file upload with validation |
| FR-002 | Reject non-.txt files | 1 | Simple file type check |
| FR-003 | Reject >50 pages | 2 | Page count calculation + rejection |
| FR-016 | Handle empty files | 1 | Simple empty check |
| FR-017 | Reject empty transcript | 1 | Same as FR-016, split for clarity |
| FR-015 (partial) | Handle analysis failures | 2 | Error handling + retry option |
| **Group subtotal** | **6 FRs** | **10 SP** | — |

**Complexity signals:** 2 endpoints (EP-001, EP-003), 1 data model (TranscriptUploadRequest), simple validation logic.

### Group 2: Core Analysis Engine
| FR ID | Description | Story Points | Rationale |
|---|---|---|---|
| FR-007 | Identify topic clusters | 5 | Core AI functionality; LLM prompt engineering required |
| FR-008 | Summarize topics | 3 | LLM call per cluster; 1-2 sentence constraint |
| FR-009 | Extract action items | 5 | NLP + entity extraction (assignees, deadlines); moderate complexity |
| FR-011 | Flag uncertain findings | 3 | Confidence scoring implementation |
| FR-015 (partial) | Handle LLM failures | 2 | Retry logic, timeout handling |
| **Group subtotal** | **5 FRs** | **18 SP** | — |

**Complexity signals:** Core AI pipeline; multiple LLM calls (topics → summaries → action items); uncertainty flagging adds complexity; 8 data models.

### Group 3: Language Processing
| FR ID | Description | Story Points | Rationale |
|---|---|---|---|
| FR-004 | Detect primary language | 2 | Standard language detection library call |
| FR-005 | Output in dominant language | 2 | LLM prompt conditioning based on detected language |
| FR-006 | Handle mixed-language | 3 | Edge case: detect dominant language in mixed content; output accordingly |
| **Group subtotal** | **3 FRs** | **7 SP** | — |

**Complexity signals:** Language detection is straightforward but mixed-language handling adds edge cases.

### Group 4: Output Generation
| FR ID | Description | Story Points | Rationale |
|---|---|---|---|
| FR-012 | Markdown output | 3 | Structured output assembly; templates needed |
| **Group subtotal** | **1 FR** | **3 SP** | — |

**Complexity signals:** Output formatting is straightforward given the data models are already defined.

### Group 5: Access Control
| FR ID | Description | Story Points | Rationale |
|---|---|---|---|
| FR-013 | Authentication requirement | 3 | TBD mechanism; auth framework integration |
| FR-014 | Access restriction | 2 | Role-based access control |
| **Group subtotal** | **2 FRs** | **5 SP** | — |

**Complexity signals:** Auth mechanism is TBD (OP-006); estimated for standard session-based or token-based auth.

### Group 6: Non-Functional Overhead
| NFR ID | Category | Story Points | Rationale |
|---|---|---|---|
| NFR-P-001 to NFR-P-005 | Performance & Scalability | 3 | Performance optimization; capacity testing |
| NFR-S-001 to NFR-S-004 | Security & Privacy | 3 | TLS, logging, auth integration, data handling |
| NFR-U-001 to NFR-U-003 | Usability & Accessibility | 2 | UI design requirements (for FE implementation) |
| NFR-R-001 to NFR-R-004 | Reliability & Maintainability | 3 | Retry logic, modular LLM layer, error handling |
| **Group subtotal** | **4 categories** | **11 SP** | — |

**Rationale:** NFRs span all FR groups and are implemented as cross-cutting concerns. Estimated at ~25% of functional effort, which is standard for internal tools.

---

## 3. Total & Confidence

| Component | Story Points | Ideal Days |
|---|---|---|
| Group 1: Upload & Validation | 10 SP | 5 days |
| Group 2: Core Analysis Engine | 18 SP | 9 days |
| Group 3: Language Processing | 7 SP | 3.5 days |
| Group 4: Output Generation | 3 SP | 1.5 days |
| Group 5: Access Control | 5 SP | 2.5 days |
| Group 6: NFR Overhead | 11 SP | 5.5 days |
| **Functional Subtotal** | **54 SP** | **27.5 days** |
| **±30% Confidence Buffer** | **16 SP** | **8 days** |
| **TOTAL (with buffer)** | **70 SP** | **35.5 days** |

### Team Timeline Scenarios

| Scenario | Team Size | Weeks (working days) | Calendar |
|---|---|---|---|
| Single developer | 1 person | 7-10 weeks | 1.5-2.5 months |
| Two developers | 2 people | 4-6 weeks | 1-1.5 months |
| Three developers | 3 people | 3-4 weeks | 1 month |

*Timeline assumes no major scope changes and that the architecture phase resolves the TBD decisions (LLM provider, auth mechanism) early.*

---

## 4. Assumptions & Caveats

### Explicit Assumptions

| # | Assumption | Source | Impact |
|---|---|---|---|
| A-1 | 1 SP ≈ 0.5 ideal days | User-confirmed conversion rate | If velocity differs, total effort scales inversely |
| A-2 | Greenfield — no legacy code | Project context | Lower complexity than incremental projects |
| A-3 | Small team (1-2 developers) | Team context | Effort is not distributed across parallel workstreams |
| A-4 | Python or Node.js backend | Architecture TBD | Stack changes could affect story point assignments |
| A-5 | Standard LLM API (REST) | Architect review note A-001 | If LLM provider requires SDK or self-hosting, Group 2 effort increases by 3-5 SP |
| A-6 | Session-based or JWT auth | Architect review recommendation | If organizational auth requirements are more complex (SAML, OIDC), Group 5 effort may increase by 3-5 SP |
| A-7 | No CI/CD pipeline exists yet | Greenfield assumption | DevOps setup time is not included in this estimate |
| A-8 | No UI design system exists | Internal tool, no existing system | UI development effort is fully included |

### Known Unknowns (will affect estimate)

| # | Unknown | Impact | Resolution Timing |
|---|---|---|---|
| U-1 | Final tech stack | ±10-20% of effort | After architecture phase |
| U-2 | LLM provider | ±5-10% of effort | After LLM evaluation |
| U-3 | Auth mechanism | ±5-10% of effort | After security requirements are defined |
| U-4 | Data retention policy | ±2-5% of effort | After architecture/security evaluation |

### Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM API costs exceed budget | Medium | Medium (operational, not development) | Budget monitoring + alerting (architect note A-003) |
| LLM response times exceed 2-minute target | Medium | Medium | Performance testing early in development; chunking strategy (architect note A-002) |
| Architecture phase decisions change scope | Low | Medium | Engage architecture phase early; freeze requirements after |
| Mixed-language processing quality | Low | Low | FR-006 uncertainty handling addresses this |

---

## 5. Recommendation

The estimate of **70 SP (35.5 ideal days)** with a **30% confidence buffer** is appropriate for a greenfield internal tool with well-defined requirements and a small team.

**Recommended approach:**
1. **Phase 1 (Weeks 1-2):** Architecture + prototype LLM integration — validate technical feasibility and select LLM provider
2. **Phase 2 (Weeks 3-6):** Core analysis engine + upload/validation — deliver end-to-end flow with English-only transcripts
3. **Phase 3 (Weeks 7-8):** Language processing + access control — add Turkish support and authentication
4. **Phase 4 (Weeks 9-10):** Polish, testing, and deployment — NFRs, optimization, and production readiness

*This phased approach delivers value early (English-only analysis in Week 6) while de-risking the most uncertain aspects (LLM selection, performance) first.*
