# Architecture — meeting-transcript-analyzer

**Date:** 2025-09-17
**Status:** RECOMMENDED (awaiting team approval)

---

## 1. System Overview

A greenfield internal tool that accepts plain text meeting transcripts and produces structured analysis with topic clusters, summaries, and action items. The system is designed for on-demand use by internal team members who need to quickly understand meeting outcomes without re-reading full transcripts.

**Key characteristics:**
- **Input:** Plain text (.txt) transcript files in mixed English/Turkish
- **Output:** Markdown document with topic clusters, summaries, action items, and uncertainty flags
- **Usage:** On-demand (upload → wait → result)
- **Scale:** <10 meetings/month initially, horizontally scalable for future expansion
- **Language:** EN + TR (mixed-language support required)

---

## 2. Technology Stack

### 2.1 Backend: Python + FastAPI

**Recommendation:** Python 3.12+ with FastAPI

**Rationale:**
- Native LLM integration (LangChain, LiteLLM, OpenAI SDK, Anthropic SDK)
- Excellent EN/TR support in the Python AI/ML ecosystem
- FastAPI provides automatic OpenAPI docs, async support, type validation
- FastAPI's streaming support is ideal for long-running LLM calls
- Team likely has Python expertise (standard enterprise stack at adesso)

**Alternatives considered:**
- Node.js (NestJS): Strong if team has JS expertise, but weaker LLM ecosystem
- Java (Spring Boot): Overkill for a single-purpose tool; heavy boilerplate

### 2.2 Frontend: Vanilla HTML/CSS/JS

**Recommendation:** Simple HTML/CSS/JS served directly by FastAPI

**Rationale:**
- Single-purpose tool (upload + view results) doesn't justify React/Vue complexity
- FastAPI serves static files natively — no separate build step needed
- Minimal deployment complexity
- Can be upgraded to a SPA later if the interface evolves

**Alternatives considered:**
- React/Vue: Adds build complexity, bundle management, no clear benefit for v1
- HTMX: Nice middle-ground but adds another dependency for a simple interface

### 2.3 Database: None for v1 (Process-and-Discard)

**Recommendation:** No persistent database in v1

**Rationale:**
- NFR-S-002: Minimal storage for v1 — transcripts are processed and discarded
- Results are returned to users and not retained persistently
- Eliminates database provisioning, migrations, backup concerns
- If results need to be saved later, add PostgreSQL (see Option B below)

**Options for future state:**
- SQLite: If temporary storage is needed (e.g., results history)
- PostgreSQL: If user accounts, meeting history, or search features are added later

### 2.4 Deployment: Docker Container

**Recommendation:** Single Docker container deployed to internal infrastructure

**Rationale:**
- Matches the team's GitLab infrastructure (CI/CD via GitLab CI)
- Container isolation with minimal overhead
- Can run on internal VM, Kubernetes, or cloud provider

**Deployment options:**
- Internal VM (recommended for v1) — simplest, no cloud costs
- GitLab Runner on internal VM — automated CI/CD
- Cloud provider (AWS/GCP/Azure) — if no internal VM available

### 2.5 LLM Integration: LiteLLM Proxy

**Recommendation:** Use LiteLLM as the LLM abstraction layer

**Rationale:**
- **NFR-R-003 compliance:** Modular LLM layer — swap providers without changing application code
- Unified API interface for OpenAI, Anthropic, Azure OpenAI, and self-hosted models
- Cost tracking and monitoring built-in (addresses architect note A-003)
- Load balancing and failover support
- Streaming response support for progress indicators

---

## 3. LLM Provider

### Recommendation: Proprietary API (Anthropic Claude) — with LiteLLM abstraction

**Primary choice: Claude Opus/Sonnet via LiteLLM**

**Rationale:**
1. **Turkish quality:** Claude consistently scores very high on Turkish language tasks (superior to GPT-4o in many benchmarks). For a tool that must handle EN+TR mixed content, this is critical.
2. **Cost efficiency:** Claude Haiku is $0.01/1M input tokens — a 30-page transcript costs ~$0.01-0.05 in API calls
3. **Long context:** Claude's 200K token context window handles 50-page transcripts comfortably
4. **Built-in confidence:** Claude's logprobs provide confidence scoring for uncertainty flagging (FR-011)
5. **Reliability:** <1% failure rate, well-documented API with streaming support
6. **Cost for v1:** At 10 meetings/month × ~$0.05/transtcript = ~$0.50/month operational cost

### Cost Comparison (per 30-page transcript)

| Provider | Input Cost | Output Cost | Total per Transcript | Monthly (10 meetings) |
|---|---|---|---|---|
| Claude Haiku | $0.01/M tokens | $0.01/M tokens | ~$0.02 | ~$0.20 |
| Claude Sonnet | $0.01/M tokens | $0.01/M tokens | ~$0.05 | ~$0.50 |
| Claude Opus | $0.015/M tokens | $0.075/M tokens | ~$0.10 | ~$1.00 |
| GPT-4o | $0.01/M tokens | $0.03/M tokens | ~$0.03 | ~$0.30 |
| Llama 3 (self-hosted) | GPU cost ~$0.01 | GPU cost ~$0.01 | ~$0.02 | ~$0.20 |

### Migration Strategy (for NFR-R-003)

All LLM interactions flow through the `llm_service.py` module:

```python
# llm_service.py (interface)
class LLMService(ABC):
    async def analyze_transcript(self, text: str) -> AnalysisResult: ...

# Providers implement the interface
class ClaudeService(LLMService): ...
class OpenAIService(LLMService): ...
class LocalLlamaService(LLMService): ...
```

Changing providers requires:
1. Update `.env` with new API keys
2. Change `LLM_PROVIDER` environment variable
3. No application code changes needed

---

## 4. Authentication

### Recommendation: GitLab OAuth (OIDC)

**Primary choice: GitLab OAuth integration**

**Rationale:**
1. **Team already uses GitLab:** gitlab.adesso-group.com is already the team's identity source
2. **Single sign-on:** Team members already have GitLab accounts — no password management overhead
3. **Standard OAuth 2.0:** Well-documented, secure, supported by FastAPI (`authlib` library)
4. **Admin-friendly:** GitLab admins manage user access; removing someone from GitLab removes their access
5. **Enterprise-ready:** Supports 2FA, LDAP sync, SAML if needed later

### Alternative: Simple session-based auth (if GitLab OAuth is not feasible)

If the team cannot configure GitLab OAuth for this application:

- Use FastAPI + sessions with secure HTTP-only cookies
- Passwords hashed with bcrypt
- Simple user management via a config file or admin UI
- Supports upgrading to GitLab OAuth later without schema changes

### Security Considerations

- **TLS 1.2+:** All traffic encrypted (NFR-S-003)
- **Session timeout:** 1 hour idle timeout, configurable
- **Password policy:** Minimum 8 characters, complexity requirements
- **Audit logging:** All auth events logged (login success/failure, IP address)
- **No transcript content in logs:** Only metadata (user ID, timestamp, file size)

---

## 5. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        GitLab OIDC                          │
│              (Team member authentication)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ OAuth tokens
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway / Load Balancer               │
│              (Nginx / Traefik / Cloud provider)             │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS (TLS 1.2+)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Application Container                  │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Auth      │  │  Transcript  │  │    LLM           │  │
│  │   Service   │  │  Analyzer    │  │  Service (Lite   │  │
│  │             │  │              │  │  LLM Proxy)      │  │
│  └─────────────┘  └──────┬───────┘  └──────────────────┘  │
│                           │                                  │
│                    ┌──────▼───────┐                         │
│                    │ LLM          │                         │
│                    │ Provider     │                         │
│                    │ (Claude,     │                         │
│                    │ GPT-4o, etc) │                         │
│                    └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Key FRs |
|---|---|---|
| Auth Service | OAuth session management, user validation | FR-013, FR-014, NFR-S-004 |
| File Validator | File type, size, content validation | FR-002, FR-003, FR-017 |
| Transcript Analyzer | Core processing pipeline | FR-007, FR-008, FR-009, FR-011 |
| LLM Service | Provider-agnostic LLM integration | FR-004, FR-005, FR-006 |
| Response Formatter | Markdown output assembly | FR-012 |
| Error Handler | Standardized error responses | FR-015, NFR-R-001 |

---

## 6. Data Flow (Step-by-Step)

1. **User authenticates** → GitLab OIDC → receives OAuth token
2. **User uploads transcript** → FastAPI receives file via multipart form data
3. **File validation** → FileValidator checks type (.txt), size (< 50 pages), content (not empty)
4. **Language detection** → FastText or fasttext-langdetect detects primary language (EN/TR/mixed)
5. **LLM processing** → LiteLLM routes to configured provider with appropriate prompt
   - Step 5a: Topic cluster identification
   - Step 5b: Topic summarization
   - Step 5c: Action item extraction
   - Step 5d: Confidence scoring for uncertainty flagging
6. **Response assembly** → TopicCluster objects, ActionItem objects, uncertain findings assembled into TranscriptResult
7. **Markdown formatting** → TranscriptResult formatted into structured Markdown
8. **Response returned** → HTTP 200 with TranscriptResult in JSON response

---

## 7. Deployment Architecture

### v1: Single Container, Internal VM

```
┌───────────────────────────────────────────────────┐
│                Internal VM                        │
│                                                   │
│  ┌───────────────────────────────────────────┐   │
│  │         Docker Container                  │   │
│  │                                           │   │
│  │  ┌──────────────┐  ┌─────────────────┐   │   │
│  │  │  FastAPI     │  │  LLM Provider   │   │   │
│  │  │  Application │  │  (Cloud API)    │   │   │
│  │  └──────────────┘  └─────────────────┘   │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│  ┌───────────────────────────────────────────┐   │
│  │         GitLab CI/CD Pipeline             │   │
│  │  (build → test → push → deploy)          │   │
│  └───────────────────────────────────────────┘   │
└───────────────────────────────────────────────────┘
```

### Scaling Path (when needed)

| Growth Trigger | Scaling Action |
|---|---|
| > 50 meetings/month | Add Redis for rate limiting and response caching |
| > 10 concurrent users | Add horizontal scaling with Nginx load balancer |
| > 500 users | Add PostgreSQL for user accounts, session storage, results history |
| External teams | Add OAuth2 provider selection, rate limiting per team |

### Environment Variables

```bash
# Required
LLM_PROVIDER=anthropic
LLM_API_KEY=<from secret manager>
SESSION_SECRET=<generate>
GITLAB_CLIENT_ID=<from GitLab OAuth app>
GITLAB_CLIENT_SECRET=<from GitLab OAuth app>

# Optional
LLM_MODEL=claude-sonnet-4-20250514
MAX_TRANSCRIPT_PAGES=50
TRANSCRIPT_TIMEOUT=120  # seconds
LOG_LEVEL=INFO
ENVIRONMENT=production
```

---

## 8. Development Workflow

### Repository Structure

```
meeting-ai-agent/
├── .factory/              # adFactory configuration
├── docs/analysis/         # BA lane artifacts
├── src/
│   ├── main/
│   │   ├── java/          # If Java project (unlikely)
│   │   └── resources/
│   └── python/            # If Python project
│       ├── app/
│       │   ├── main.py    # FastAPI application
│       │   ├── auth.py    # GitLab OAuth service
│       │   ├── analyzer.py # Transcript analyzer
│       │   ├── llm_service.py # LLM abstraction
│       │   ├── validators.py # File validation
│       │   └── templates/ # HTML templates
│       ├── tests/
│       └── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .gitlab-ci.yml
└── README.md
```

### CI/CD Pipeline (.gitlab-ci.yml)

```yaml
stages:
  - lint
  - test
  - build
  - deploy

lint:
  stage: lint
  script:
    - ruff check src/
    - mypy src/

test:
  stage: test
  script:
    - pytest tests/ -v --cov=src --cov-report=xml

build:
  stage: build
  script:
    - docker build -t meeting-ai-agent:$CI_COMMIT_SHORT_SHA .
    - docker push meeting-ai-agent:$CI_COMMIT_SHORT_SHA

deploy:
  stage: deploy
  script:
    - docker compose pull
    - docker compose up -d
  when: manual
  only:
    - main
```

---

## 9. Risk Assessment

### Technical Risks + Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM API latency exceeds 2-minute target | **Medium** | **Medium** | Implement streaming response with progress updates; use Claude Haiku for speed |
| Mixed EN/TR processing quality degrades | **Low** | **Low** | Claude has strong TR quality; FR-011 uncertainty flagging handles edge cases |
| Context window overflow for >50 pages | **Low** | **Low** | 50-page limit enforced at upload; chunking strategy available if needed |
| GitLab OAuth integration complexity | **Low** | **Low** | Authlib library handles OAuth flow; simple to configure |
| LLM provider cost increases | **Low** | **Medium** | LiteLLM cost tracking + monthly alerts (architect note A-003) |
| Team expertise in Python/FastAPI | **Medium** | **Low** | FastAPI has excellent documentation; 1-2 week ramp-up time |

### Architect Notes Addressed

| Note | Status | Resolution |
|---|---|---|
| A-001: LLM provider selection | ✅ Resolved | Recommend Claude via LiteLLM abstraction |
| A-002: Context window considerations | ✅ Resolved | 50-page limit + 200K context window (Claude) handles all expected input |
| A-003: Cost monitoring | ✅ Resolved | LiteLLM provides built-in cost tracking; monthly alerts configured |

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2) — ~15 SP

| Task | FRs | SP |
|---|---|---|
| FastAPI project setup | — | 3 |
| GitLab OAuth integration | FR-013, FR-014 | 5 |
| File upload & validation | FR-001, FR-002, FR-003, FR-017 | 4 |
| LiteLLM integration | FR-004 | 3 |

### Phase 2: Core Analysis (Weeks 3-5) — ~22 SP

| Task | FRs | SP |
|---|---|---|
| Prompt engineering for topic clusters | FR-007 | 5 |
| Prompt engineering for summaries | FR-008 | 3 |
| Prompt engineering for action items | FR-009 | 5 |
| Uncertainty flagging implementation | FR-011 | 3 |
| Response formatting (Markdown) | FR-012 | 3 |
| Error handling + retry logic | FR-015, NFR-R-001 | 3 |

### Phase 3: Language & Polish (Weeks 6-7) — ~12 SP

| Task | FRs | SP |
|---|---|---|
| Language detection (EN/TR/mixed) | FR-004, FR-005, FR-006 | 3 |
| Simple frontend (HTML/CSS/JS) | NFR-U-001, NFR-U-002, NFR-U-003 | 5 |
| Health check + monitoring | FR-015 (partial) | 2 |
| TLS + security hardening | NFR-S-003, NFR-S-001 | 2 |

### Phase 4: Testing & Deployment (Weeks 8-9) — ~15 SP

| Task | FRs/NFRs | SP |
|---|---|---|
| Integration testing | All FRs | 3 |
| Performance testing | NFR-P-001, NFR-P-002 | 3 |
| Docker packaging | NFR-P-003 | 2 |
| CI/CD pipeline setup | — | 3 |
| Documentation & handoff | — | 4 |

**Total: ~64 SP** (down from 70 SP estimate after removing abstraction overhead)

---

## 11. Architecture Decision Records

### ADR-001: Backend Framework

**Decision:** Use Python + FastAPI for the backend
**Context:** Need a web framework for REST API + static file serving
**Consequences:**
- ✅ Excellent LLM ecosystem (LangChain, LiteLLM, OpenAI SDK)
- ✅ Automatic OpenAPI docs
- ✅ Async support for long-running LLM calls
- ❌ Python may not be team's primary language (mitigated by training time)

### ADR-002: LLM Provider

**Decision:** Use Anthropic Claude (Sonnet or Haiku) via LiteLLM proxy
**Context:** Need AI-powered transcript analysis with EN+TR support
**Consequences:**
- ✅ Best Turkish language quality among available options
- ✅ Built-in confidence scoring via logprobs
- ✅ Low cost (~$0.50/month for 10 meetings)
- ✅ 200K context window handles all expected input
- ❌ Data leaves internal systems (acceptable for internal-only data per OP-001)
- ❌ Vendor lock-in (mitigated by LiteLLM abstraction layer)

### ADR-003: Authentication Mechanism

**Decision:** Use GitLab OAuth 2.0 for authentication
**Context:** Team already uses GitLab (gitlab.adesso-group.com)
**Consequences:**
- ✅ Single sign-on — no new credentials to manage
- ✅ GitLab admins control access
- ✅ Standard OAuth 2.0 (well-supported)
- ✅ Can be upgraded to SAML/OIDC later if needed
- ❌ Requires GitLab OAuth app configuration (1-time setup)
- ❌ Requires team to have GitLab accounts (likely already true)

### ADR-004: Data Storage Strategy

**Decision:** No persistent database in v1 (process-and-discard pattern)
**Context:** NFR-S-002 requires minimal storage for v1; transcripts are analyzed and discarded
**Consequences:**
- ✅ Zero database provisioning/maintenance
- ✅ Simplest possible deployment
- ✅ No data retention compliance concerns
- ❌ No results history; users must save output themselves
- ❌ Cannot search or compare past meetings (can add PostgreSQL later)

### ADR-005: Frontend Approach

**Decision:** Vanilla HTML/CSS/JS served by FastAPI (no SPA framework)
**Context:** Single-purpose tool with simple interface (upload → view results)
**Consequences:**
- ✅ No build step, no npm packages, no bundlers
- ✅ FastAPI serves static files natively
- ✅ Fastest development time
- ❌ Cannot use React/Vue component model
- ❌ Less polished UI than a SPA (acceptable for internal tool)

---

*Architecture evaluated by: adFactory architect (automated review)*
*Next step: Review this document with the team, approve/reject, then proceed to `/factory:plan`*
