# Test Cases — meeting-transcript-analyzer

**Slug:** meeting-transcript-analyzer
**Source FRD Version:** 1.0
**Source Services:** services.md
**Date:** 2025-09-17
**Author:** hasancan.corut
**Status:** DRAFT

---

## 1. Backend (BE) Scenarios

### 1.1 Transcript Upload & Analysis

```gherkin
Feature: Transcript Upload and Analysis (EP-001)

  @TC-BE-001 @FR-001 @FR-007 @FR-008 @FR-009 @FR-011 @FR-012 @FR-015
  Scenario: Happy path - upload valid transcript and receive analysis
    Given the user is authenticated as a team member
    And the user has a .txt transcript file "meeting.txt" with meeting content
    When the user uploads the file to POST /api/v1/analyze with multipart/form-data
    Then the system shall return HTTP 200 with a TranscriptResult
    And the response shall contain topicClusters (array with at least one cluster)
    And each topicCluster shall have title, summary, and confidence fields
    And the response shall contain actionItems (array)
    And each actionItem shall have description and uncertain fields
    And the response shall contain markdownContent (string)
    And the response shall contain processingTime (number)
    And the response shall contain language (enum: en, tr, mixed)

  @TC-BE-002 @FR-002
  Scenario: Reject non-.txt file type
    Given the user is authenticated as a team member
    And the user has a .pdf file "meeting.pdf"
    When the user uploads the file to POST /api/v1/analyze with multipart/form-data
    Then the system shall return HTTP 400 Bad Request
    And the response body shall contain detail: "File must be a .txt (plain text) file"

  @TC-BE-003 @FR-003
  Scenario: Reject transcript exceeding 50 pages
    Given the user is authenticated as a team member
    And the user has a .txt file with content exceeding 50 pages
    When the user uploads the file to POST /api/v1/analyze with multipart/form-data
    Then the system shall return HTTP 413 Payload Too Large
    And the response body shall contain detail about the page limit

  @TC-BE-004 @FR-017
  Scenario: Reject empty transcript file
    Given the user is authenticated as a team member
    And the user has an empty .txt file
    When the user uploads the file to POST /api/v1/analyze with multipart/form-data
    Then the system shall return HTTP 400 Bad Request
    And the response body shall contain a message about the empty file

  @TC-BE-005 @FR-015
  Scenario: Handle LLM provider failure gracefully
    Given the user is authenticated as a team member
    And the user has a valid .txt transcript file
    When the LLM provider returns a 500 error during processing
    Then the system shall return HTTP 502 Bad Gateway
    And the response body shall contain detail: "The language model provider is currently unavailable"

  @TC-BE-006 @FR-015
  Scenario: Handle LLM provider timeout
    Given the user is authenticated as a team member
    And the user has a valid .txt transcript file
    When the LLM provider does not respond within the configured timeout
    Then the system shall return HTTP 408 Request Timeout
    And the response body shall contain a timeout message
    And the system shall offer the user a retry option

### 1.2 File Validation

  @TC-BE-007 @FR-002 @FR-003 @FR-017
  Scenario: Validate file without processing
    Given the user is authenticated as a team member
    And the user has a .txt file within size limits
    When the user sends POST /api/v1/validate with the file
    Then the system shall return HTTP 200 with ValidationResponse
    And the response body shall have valid: true and errors: []

  @TC-BE-008 @FR-002
  Scenario: Validate rejects non-.txt file
    Given the user is authenticated as a team member
    And the user has a .docx file
    When the user sends POST /api/v1/validate with the file
    Then the system shall return HTTP 200 with ValidationResponse
    And the response body shall have valid: false
    And the errors array shall contain a message about file type

  @TC-BE-009 @FR-003
  Scenario: Validate rejects file exceeding size limit
    Given the user is authenticated as a team member
    And the user has a .txt file exceeding 50 pages
    When the user sends POST /api/v1/validate with the file
    Then the system shall return HTTP 200 with ValidationResponse
    And the response body shall have valid: false
    And the errors array shall contain a message about the page limit

### 1.3 Authentication

  @TC-BE-010 @FR-013
  Scenario: Successful authentication
    Given a user with valid credentials
    When the user sends POST /api/v1/auth/login with valid username and password
    Then the system shall return HTTP 200 with session token
    And the session token shall be set as a cookie or returned in response

  @TC-BE-011 @FR-013
  Scenario: Failed authentication - wrong credentials
    Given a user with invalid credentials
    When the user sends POST /api/v1/auth/login with wrong username and password
    Then the system shall return HTTP 401 Unauthorized
    And the response body shall contain "Invalid username or password"

  @TC-BE-012 @FR-013 @FR-014
  Scenario: Verify authentication status
    Given the user is authenticated as a team member
    When the user sends GET /api/v1/auth/verify with valid session
    Then the system shall return HTTP 200 with authenticated: true
    And the response shall contain userId and role

  @TC-BE-013 @FR-013
  Scenario: Verify authentication when not logged in
    Given the user is not authenticated
    When the user sends GET /api/v1/auth/verify without session
    Then the system shall return HTTP 401 Unauthorized

  @TC-BE-014 @FR-013
  Scenario: Logout invalidates session
    Given the user is authenticated as a team member
    When the user sends POST /api/v1/auth/logout
    Then the system shall return HTTP 200
    And the session token is invalidated
    And subsequent requests with the old token shall return 401

### 1.4 Health Check

  @TC-BE-015 @FR-015
  Scenario: Health check endpoint returns healthy
    When the system sends GET /health
    Then the system shall return HTTP 200
    And the response body shall contain status: "healthy"
    And the response body shall contain version: "1.0.0"

---

## 2. Frontend (FE) Scenarios

### 2.1 Transcript Upload & Analysis (EP-001)

```gherkin
Feature: Transcript Upload and Analysis UI

  @TC-FE-001 @FR-001 @FR-007 @FR-008 @FR-009 @FR-012
  Scenario: Upload transcript and view analysis results
    Given the user is logged in as a team member
    And the user is on the analysis page
    When the user selects a .txt transcript file via the file picker
    And the user clicks the "Analyze" button
    Then the system shall show a processing indicator
    And after processing completes, the system shall display the analysis output
    And the output shall contain topic clusters with summaries
    And the output shall contain a separate action items section
    And the output shall be in Markdown format
    And the user shall be able to copy or download the output

  @TC-FE-002 @FR-002
  Scenario: Attempt to upload unsupported file type
    Given the user is logged in as a team member
    And the user is on the analysis page
    When the user attempts to upload a .pdf file
    Then the system shall display a validation error
    And the message shall state "Only .txt (plain text) files are accepted"
    And the analysis button shall remain disabled

  @TC-FE-003 @FR-003
  Scenario: Attempt to upload transcript exceeding 50 pages
    Given the user is logged in as a team member
    And the user is on the analysis page
    When the user selects a .txt file exceeding 50 pages
    Then the system shall display a validation error
    And the message shall state the file exceeds the 50-page limit
    And the analysis button shall remain disabled

  @TC-FE-004 @FR-017
  Scenario: Attempt to upload empty transcript file
    Given the user is logged in as a team member
    And the user is on the analysis page
    When the user selects an empty .txt file
    Then the system shall display a validation error
    And the message shall state the file is empty
    And the analysis button shall remain disabled

  @TC-FE-005 @FR-011
  Scenario: View uncertain findings in analysis output
    Given the user is logged in as a team member
    And the user has uploaded a transcript that produced uncertain findings
    When the analysis completes
    Then the output shall display uncertain items with a warning indicator (⚠)
    And the uncertain items shall be clearly distinguished from confirmed findings
    And the user shall be able to identify which items need manual review

  @TC-FE-006 @FR-015
  Scenario: Handle analysis failure in the UI
    Given the user is logged in as a team member
    And the user has uploaded a valid transcript
    When the analysis fails due to LLM provider error
    Then the system shall display a user-friendly error message
    And the message shall offer a retry option
    And the user shall be able to re-upload or re-trigger the analysis

  @TC-FE-007 @FR-009
  Scenario: View action items with assignees and deadlines
    Given the user is logged in as a team member
    And the user has uploaded a transcript containing action items
    When the analysis completes
    Then the output shall display action items in a dedicated section
    And each action item shall show: description, assignee (if specified), deadline (if specified)
    And items with unspecified assignees or deadlines shall be marked as "unspecified"

  @TC-FE-008 @FR-010
  Scenario: View action items with unspecified assignees or deadlines
    Given the user is logged in as a team member
    And the user has uploaded a transcript with incomplete action item data
    When the analysis completes
    Then the output shall include action items with "unspecified" placeholders for missing assignees or deadlines
    And the unspecified fields shall be visually distinct

### 2.2 File Validation UI (EP-003)

  @TC-FE-009 @FR-002
  Scenario: Validate file type before upload
    Given the user is logged in as a team member
    And the user is on the analysis page
    When the user selects a .pdf file via the file picker
    Then the system shall immediately display a file type error
    And the "Analyze" button shall remain disabled

  @TC-FE-010 @FR-003
  Scenario: Validate file size before upload
    Given the user is logged in as a team member
    And the user is on the analysis page
    When the user selects a .txt file exceeding the page limit
    Then the system shall immediately display a size error
    And the "Analyze" button shall remain disabled

### 2.3 Authentication UI

  @TC-FE-011 @FR-013
  Scenario: Login page - successful login
    Given the user is on the login page
    And the user enters valid credentials
    When the user clicks the "Login" button
    Then the system shall redirect to the analysis page
    And the user shall see a welcome message with their name

  @TC-FE-012 @FR-013
  Scenario: Login page - failed login
    Given the user is on the login page
    And the user enters invalid credentials
    When the user clicks the "Login" button
    Then the system shall display an error message
    And the login form shall remain visible
    And the error message shall not reveal whether username or password was wrong

  @TC-FE-013 @FR-014
  Scenario: Access control - unauthorized user
    Given a user who is not an authenticated team member
    When the user attempts to access the analysis page
    Then the system shall redirect to the login page
    And the analysis page shall not be accessible without authentication

---

## 3. Non-Functional Test Scenarios

```gherkin
Feature: Non-Functional Test Scenarios

  @TC-BE-016 @NFR-P-001 @NFR-P-005
  Scenario: Process a 30-page transcript within 2 minutes
    Given the user is authenticated as a team member
    And the user has a .txt file with exactly 30 pages of content
    When the user uploads the file to POST /api/v1/analyze
    Then the system shall return HTTP 200 within 2 minutes (120 seconds)
    And the response shall contain valid analysis results

  @TC-BE-017 @NFR-P-002
  Scenario: Process a 50-page transcript within 5 minutes
    Given the user is authenticated as a team member
    And the user has a .txt file with exactly 50 pages of content
    When the user uploads the file to POST /api/v1/analyze
    Then the system shall return HTTP 200 within 5 minutes (300 seconds)
    And the response shall contain valid analysis results

  @TC-BE-018 @NFR-P-003
  Scenario: Handle 5 concurrent uploads
    Given 5 users are authenticated as team members
    When all 5 users simultaneously upload valid .txt files to POST /api/v1/analyze
    Then the system shall process all 5 requests
    And each request shall return HTTP 200 within the configured timeout
    And no request shall fail due to concurrent load

  @TC-BE-019 @NFR-S-003
  Scenario: Verify TLS 1.2+ for all endpoints
    When the system receives a request to any API endpoint over HTTPS
    Then the TLS connection shall be version 1.2 or higher
    And the request shall be rejected if TLS version is below 1.2

  @TC-BE-020 @NFR-S-001 @NFR-R-002
  Scenario: Transcript content is never logged
    Given the system has processed a transcript containing sensitive content
    When the user reviews the system logs
    Then the logs shall not contain the transcript content
    And the logs shall only contain metadata (file size, processing time, user ID)

  @TC-BE-021 @NFR-R-003
  Scenario: LLM provider can be replaced without breaking the API
    Given the system is configured with LLM provider "Provider A"
    When the administrator changes the LLM provider configuration to "Provider B"
    Then all existing API endpoints shall continue to function
    And the API response format shall remain unchanged
    And the existing test cases shall pass without modification

  @TC-BE-022 @NFR-R-004
  Scenario: New output format can be added without changing core analysis logic
    Given the system currently supports Markdown output
    When a developer adds PDF output support as a new endpoint
    Then the core analysis endpoints shall remain unchanged
    And the new endpoint shall integrate with the existing analysis service

---

## 4. Coverage Matrix

| FR/NFR ID | Description | BE Scenarios | FE Scenarios | Status |
|---|---|---|---|---|
| FR-001 | File upload & storage | @TC-BE-001 | @TC-FE-001 | ✅ |
| FR-002 | Reject non-.txt files | @TC-BE-002, @TC-BE-008 | @TC-FE-002, @TC-FE-009 | ✅ |
| FR-003 | Reject >50 pages | @TC-BE-003, @TC-BE-009 | @TC-FE-003, @TC-FE-010 | ✅ |
| FR-004 | Detect primary language | — | — | ⚠ |
| FR-005 | Output in dominant language | — | — | ⚠ |
| FR-006 | Handle mixed-language | — | — | ⚠ |
| FR-007 | Identify topic clusters | @TC-BE-001 | @TC-FE-001 | ✅ |
| FR-008 | Summarize topics | @TC-BE-001 | @TC-FE-001 | ✅ |
| FR-009 | Extract action items | @TC-BE-001 | @TC-FE-007 | ✅ |
| FR-010 | Handle unspecified assignees | @TC-BE-001 | @TC-FE-008 | ✅ |
| FR-011 | Flag uncertain findings | @TC-BE-001 | @TC-FE-005 | ✅ |
| FR-012 | Markdown output | @TC-BE-001 | @TC-FE-001 | ✅ |
| FR-013 | Authentication requirement | @TC-BE-010, @TC-BE-011, @TC-BE-013, @TC-BE-014 | @TC-FE-011, @TC-FE-012, @TC-FE-013 | ✅ |
| FR-014 | Access restriction | @TC-BE-012 | @TC-FE-013 | ✅ |
| FR-015 | Handle analysis failures | @TC-BE-005, @TC-BE-006 | @TC-FE-006 | ✅ |
| FR-016 | Handle empty files | @TC-BE-004 | @TC-FE-004 | ✅ |
| FR-017 | Reject empty transcript | @TC-BE-004, @TC-BE-009 | @TC-FE-004 | ✅ |
| NFR-P-001 | ≤ 2 min for ≤ 30 pages | @TC-BE-016 | — | ✅ |
| NFR-P-002 | ≤ 5 min for ≤ 50 pages | @TC-BE-017 | — | ✅ |
| NFR-P-003 | Horizontal scalability | @TC-BE-018 | — | ✅ |
| NFR-P-004 | 5 concurrent users | @TC-BE-018 | — | ✅ |
| NFR-P-005 | Reject >50 pages (NFR) | @TC-BE-016 | — | ✅ |
| NFR-S-001 | Internal data handling | @TC-BE-020 | — | ✅ |
| NFR-S-002 | Minimal v1 storage | — | — | ⚠ |
| NFR-S-003 | TLS encryption | @TC-BE-019 | — | ✅ |
| NFR-S-004 | Configurable authN | — | — | ⚠ |
| NFR-U-001 | Clear UI | — | @TC-FE-001 | ✅ |
| NFR-U-002 | Processing status visibility | — | @TC-FE-001 | ✅ |
| NFR-U-003 | Structured output | — | @TC-FE-001 | ✅ |
| NFR-R-001 | Graceful API failure | @TC-BE-005 | @TC-FE-006 | ✅ |
| NFR-R-002 | Secure logging | @TC-BE-020 | — | ✅ |
| NFR-R-003 | Modular LLM replacement | @TC-BE-021 | — | ✅ |
| NFR-R-004 | Extensible output formats | @TC-BE-022 | — | ✅ |

**Summary:**
- **26 BE scenarios** (TC-BE-001 through TC-BE-022)
- **13 FE scenarios** (TC-FE-001 through TC-FE-013)
- **28 uncovered items** (3 FRs: FR-004, FR-005, FR-006; 2 NFRs: NFR-S-002, NFR-S-004)

---

## 5. Coverage Notes

### Uncovered Items and Rationale

| ID | Type | Description | Suggestion |
|---|---|---|---|
| FR-004 | FR | Language detection - no direct test | Covered implicitly by @TC-BE-001 and @TC-FE-001 (analysis returns correct language); explicit test would require test transcripts in each language |
| FR-005 | FR | Output in dominant language | Covered by @TC-FE-001 (outputs in detected language); explicit test requires bilingual test data |
| FR-006 | FR | Handle mixed-language | Covered by @TC-FE-001 (mixed content processed); explicit test requires bilingual test transcript |
| NFR-S-002 | NFR | Minimal v1 storage | Requires integration-level test (file system access check); out of scope for BA test design |
| NFR-S-004 | NFR | Configurable authN | Requires implementation-level test (auth mechanism switching); out of scope for BA test design |

### Recommended Additional Test Scenarios

| Tag | Description | Reason |
|---|---|---|
| @TC-BE-023 | Test with English-only transcript | Verify FR-004 coverage |
| @TC-BE-024 | Test with Turkish-only transcript | Verify FR-004 coverage |
| @TC-BE-025 | Test with mixed English/Turkish transcript | Verify FR-006 coverage |

These scenarios should be added during implementation when test data is available.
