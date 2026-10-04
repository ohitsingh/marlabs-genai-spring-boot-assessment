# Marlabs GenAI Spring Boot + FastAPI Assessment

Employee policy and reimbursement triage application developed for the Marlabs GenAI Spring Boot Candidate Assessment.

The application consists of:

- Spring Boot public API
- Python FastAPI processing service
- Policy repository and policy engine
- Document extraction
- Deterministic offline model/provider
- Synthetic policy and reimbursement request data
- Automated tests

---

## 1. Architecture

```text
                         Client
                           |
                           | HTTP
                           v
                +----------------------+
                |     Spring Boot      |
                |      Port 8080       |
                +----------------------+
                    |             |
                    |             |
             Caller Context    Validation
                    |             |
                    +------+------+
                           |
                           | Internal HTTP
                           v
                +----------------------+
                |       FastAPI        |
                |      Port 8000       |
                +----------------------+
                    |      |       |
                    v      v       v
                Extractor Policy  Model
                         Engine   Provider
                           |
                           v
                    Policy / Request
                         Data
```

### Spring Boot Responsibilities

Spring Boot owns:

- Public API endpoints
- `X-Caller-Id` validation
- Caller context resolution
- Tenant and role lookup
- Request validation
- Batch manifest validation
- Communication with FastAPI
- Public response contract
- HTTP error handling

### FastAPI Responsibilities

FastAPI handles:

- Policy question processing
- Document extraction
- Benefit extraction
- Amount extraction
- Currency extraction
- Reference extraction
- Policy retrieval
- Evidence handling
- Batch item processing
- Deterministic offline model/provider behavior

Caller identity, tenant, and role are not trusted from submitted documents or request-body claims.

---

# 2. Project Structure

```text
marlabs-assessment/
│
├── README.md
├── .gitignore
│
├── marlabs-assessment/
│   ├── pom.xml
│   ├── mvnw
│   ├── mvnw.cmd
│   └── src/
│       ├── main/
│       │   ├── java/
│       │   │   └── com/marlabs/assessment/
│       │   │       ├── config/
│       │   │       ├── controller/
│       │   │       ├── exception/
│       │   │       ├── model/
│       │   │       └── service/
│       │   └── resources/
│       │       └── application.yaml
│       │
│       └── test/
│
└── marlabs-python-service/
    ├── app.py
    ├── batch_models.py
    ├── batch_processor.py
    ├── extractor.py
    ├── model_provider.py
    ├── policies.json
    ├── policy_engine.py
    ├── policy_repository.py
    ├── request_extractor.py
    ├── requirements.txt
    ├── test_policy.py
    │
    └── test-data/
        ├── request-01.txt
        ├── request-02.pdf
        ├── request-03.txt
        ├── request-04.txt
        ├── request-05.txt
        ├── request-06.txt
        ├── request-07.txt
        └── request-08.txt
```

---

# 3. Prerequisites

Required:

- Java 17 or compatible Java version supported by the project
- Python 3.11+ recommended
- Git
- Maven or Maven Wrapper

Verify:

```bash
java -version
python --version
git --version
```

---

# 4. Configuration

Spring Boot configuration:

```text
marlabs-assessment/src/main/resources/application.yaml
```

Current configuration:

```yaml
spring:
  application:
    name: marlabs-assessment

  servlet:
    multipart:
      max-file-size: 5MB
      max-request-size: 20MB

server:
  port: 8080

python:
  service:
    base-url: http://localhost:8000
    answer-path: /internal/answer
    batch-path: /internal/process
```

Services:

```text
Spring Boot:
http://localhost:8080

FastAPI:
http://localhost:8000

FastAPI Swagger:
http://localhost:8000/docs
```

The application supports deterministic offline execution and does not require a paid model service or API key.

---

# 5. Start FastAPI

Open Terminal 1:

```bash
cd marlabs-python-service
```

Create the virtual environment if required:

```bash
python -m venv venv
```

Activate on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

FastAPI should be available at:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

---

# 6. Start Spring Boot

Open Terminal 2:

```bash
cd marlabs-assessment
```

Windows Maven Wrapper:

```bash
.\mvnw.cmd spring-boot:run
```

Or:

```bash
mvn spring-boot:run
```

Spring Boot should be available at:

```text
http://localhost:8080
```

---

# 7. Public APIs

The public API is exposed through Spring Boot.

```text
POST /answer
POST /batches
```

Both endpoints require:

```text
X-Caller-Id
```

Supported callers:

```text
atlas-employee-01
atlas-contractor-01
boreal-employee-01
```

Tenant and role are resolved from the caller context.

They are not accepted as trusted values from the request body or uploaded document.

---

# 8. POST /answer

Endpoint:

```http
POST http://localhost:8080/answer
```

Headers:

```http
Content-Type: application/json
X-Caller-Id: atlas-employee-01
```

Request:

```json
{
  "question": "What is my annual certification reimbursement limit?",
  "as_of": "2026-09-21"
}
```

## 8.1 ANSWERED

For supported policy evidence:

```json
{
  "status": "ANSWERED",
  "answer": "The annual certification reimbursement limit for employees is INR 25000.",
  "citations": [
    {
      "chunk_id": "atlas-cert-current",
      "quote": "The annual certification reimbursement limit for employees is INR 25000."
    }
  ]
}
```

Each citation contains:

- `chunk_id` - policy ID
- `quote` - supporting policy quotation

## 8.2 INSUFFICIENT_EVIDENCE

When no eligible policy evidence supports the requested benefit:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": null,
  "citations": []
}
```

The application does not use general world knowledge or submitted reimbursement text as policy evidence.

## 8.3 CONFLICT

When multiple simultaneously applicable approved policies disagree and no precedence rule is available:

```json
{
  "status": "CONFLICT",
  "answer": null,
  "citations": [
    {
      "chunk_id": "atlas-home-office-a",
      "quote": "The annual home-office allowance for employees is INR 12000."
    },
    {
      "chunk_id": "atlas-home-office-b",
      "quote": "The annual home-office allowance for employees is INR 15000."
    }
  ]
}
```

The application does not invent a precedence rule.

---

# 9. Policy Effective Dates

Policy applicability follows:

```text
effective_from <= as_of < effective_to
```

Example:

```text
atlas-cert-historical
2026-01-01 to 2026-06-01
INR 40000
```

```text
atlas-cert-current
2026-06-01 to 2027-01-01
INR 25000
```

The requested `as_of` date determines the applicable policy.

Only approved policies matching the caller's tenant and role are eligible.

---

# 10. POST /batches

Endpoint:

```http
POST http://localhost:8080/batches
```

Content type:

```text
multipart/form-data
```

Required:

- `X-Caller-Id`
- Metadata JSON part
- Repeated file parts

Example metadata:

```json
{
  "batchId": "batch-test-001",
  "asOf": "2026-09-21",
  "documents": [
    {
      "documentId": "request-01",
      "filename": "request-01.txt"
    }
  ]
}
```

Each uploaded filename must match a manifest entry.

`documentId` and `filename` must be unique within the manifest.

---

# 11. Batch Response

The batch response contains:

- Batch ID
- Summary
- One result for every manifest item
- Extracted data
- Field evidence
- Policy result
- Review information
- Duplicate information
- Error information

Example:

```json
{
  "batch_id": "batch-test-001",
  "summary": {
    "total": 1,
    "completed": 1,
    "failed": 0
  },
  "results": [
    {
      "document_id": "request-01",
      "processing_status": "COMPLETED",
      "extracted": {
        "benefit": "certification",
        "amount": 18000,
        "currency": "INR",
        "reference": "CERT-101"
      },
      "field_evidence": [],
      "policy": {},
      "review_required": true,
      "issues": [],
      "duplicate_of": null,
      "error": null
    }
  ]
}
```

---

# 12. Human Review

Every submitted reimbursement request requires human review.

The application does not:

- Approve claims
- Initiate payments
- Send employee messages
- Infer remaining annual balance
- Determine a payable amount without supporting evidence

An annual policy limit does not establish:

- Remaining balance
- Expense eligibility
- Payable amount

---

# 13. Duplicate File Handling

`request-06.txt` is byte-for-byte identical to `request-01.txt`.

Exact file duplicates are detected using file content rather than filename.

Example:

```json
{
  "document_id": "request-06",
  "processing_status": "COMPLETED",
  "duplicate_of": "request-01"
}
```

The duplicate remains a separate manifest result.

---

# 14. Empty File Handling

`request-08.txt` is intentionally zero bytes.

An empty or unreadable file produces an item-level failure.

Example:

```json
{
  "document_id": "request-08",
  "processing_status": "FAILED",
  "review_required": true,
  "error": {
    "code": "EMPTY_FILE",
    "message": "The uploaded file is empty."
  }
}
```

One failed item does not prevent independent batch items from being processed.

---

# 15. Ambiguous Extraction

`request-03.txt` contains two different amounts:

```text
Invoice amount: INR 22000
Reimbursement form amount: INR 28000
```

The application does not arbitrarily choose one amount.

Ambiguous information remains visible and requires human review.

An ambiguous business value is different from a technical processing failure.

---

# 16. Prompt Injection Protection

Submitted documents and policy passages are treated as untrusted data.

For example, one supplied request contains text attempting to:

- Ignore the caller header
- Switch the caller to Boreal
- Approve the request

Document content cannot change:

- Caller identity
- Tenant
- Role
- Access rules
- Application behavior

Caller identity is established through the Spring Boot caller context.

---

# 17. Policy Data

Policy data is stored separately from application logic:

```text
marlabs-python-service/policies.json
```

Policy records contain:

- Policy ID
- Tenant
- Permitted role
- Approval state
- Effective dates
- Policy passage

Only eligible approved policies matching the caller context and requested date are used as evidence.

---

# 18. Supplied Test Data

The repository contains the synthetic assessment request files:

```text
test-data/
├── request-01.txt
├── request-02.pdf
├── request-03.txt
├── request-04.txt
├── request-05.txt
├── request-06.txt
├── request-07.txt
└── request-08.txt
```

| Request | Scenario |
|---|---|
| request-01 | Certification reimbursement |
| request-02 | Text-based PDF |
| request-03 | Ambiguous amount |
| request-04 | Unsupported wellness benefit |
| request-05 | Prompt injection attempt |
| request-06 | Exact duplicate of request-01 |
| request-07 | Missing amount / missing manager approval |
| request-08 | Zero-byte file |

---

# 19. Testing

### Python Tests

```bash
cd marlabs-python-service
pytest
```

If required:

```bash
pip install pytest
```

### Spring Boot Tests

```bash
cd marlabs-assessment
.\mvnw.cmd test
```

Or:

```bash
mvn test
```

---

# 20. Important Test Scenarios

## Certification Policy

```text
Caller:
atlas-employee-01

Question:
What is my annual certification reimbursement limit?

as_of:
2026-09-21

Expected:
ANSWERED
INR 25000
```

## Historical Certification Policy

```text
Caller:
atlas-employee-01

as_of:
2026-05-30

Expected:
ANSWERED
INR 40000
```

## Contractor Policy

```text
Caller:
atlas-contractor-01

as_of:
2026-09-21

Expected:
ANSWERED
INR 10000
```

## Conflicting Home-Office Policies

```text
Caller:
atlas-employee-01

Question:
What is my annual home-office allowance?

Expected:
CONFLICT
```

## Unsupported Benefit

```text
Question:
What is my annual wellness reimbursement limit?

Expected:
INSUFFICIENT_EVIDENCE
```

---

# 21. Batch Test Scenarios

### One File

```text
request-01.txt
```

Expected:

```text
COMPLETED
```

### Multiple Files

```text
request-01.txt
request-03.txt
request-04.txt
request-05.txt
```

Expected:

```text
All independent items processed
```

### Exact Duplicate

```text
request-01.txt
request-06.txt
```

Expected:

```text
request-06.duplicate_of = request-01
```

### Empty File

```text
request-08.txt
```

Expected:

```text
processing_status = FAILED
```

### Complete Eight-File Batch

```text
request-01.txt
request-02.pdf
request-03.txt
request-04.txt
request-05.txt
request-06.txt
request-07.txt
request-08.txt
```

Expected:

```text
request-01 -> COMPLETED
request-02 -> COMPLETED
request-03 -> COMPLETED
request-04 -> COMPLETED
request-05 -> COMPLETED
request-06 -> COMPLETED + duplicate_of=request-01
request-07 -> COMPLETED
request-08 -> FAILED
```

---

# 22. Validation and Error Handling

The application rejects:

- Missing `X-Caller-Id`
- Unknown caller
- Invalid `as_of` date
- Invalid metadata
- Duplicate manifest document IDs
- Duplicate manifest filenames
- Missing file parts
- Extra file parts

These are whole-request or whole-batch validation failures.

Item-level failures include:

- Empty file
- Unreadable file
- Item-level dependency failure
- Provider timeout
- Malformed model output

One item failure does not prevent independent items from being processed.

---

# 23. Offline Mode

The application includes a deterministic offline model/provider double.

This allows local execution without:

- OpenAI API keys
- Azure OpenAI credentials
- Paid model services
- External model dependencies

The model/provider abstraction keeps model behavior separated from extraction and policy logic.

A real model provider can be introduced later without changing the public API contract.

---

# 24. Security Considerations

The implementation follows these principles:

1. Caller identity is resolved server-side.
2. Tenant and role are not trusted from submitted documents.
3. Uploaded documents are treated as untrusted data.
4. Policy eligibility is determined from policy metadata.
5. Draft policies are not eligible evidence.
6. Prompt injection is treated as data, not instructions.
7. Secrets and API keys are not committed to source control.
8. Full document contents should not be logged by default.

---

# 25. Design Decision

## Decision

The implementation separates Spring Boot responsibilities from Python responsibilities.

Spring Boot owns the public contract and caller context.

Python owns document extraction, policy retrieval, and model/provider processing.

## Reason

This creates a clear trust boundary.

Caller identity and authorization context are established by Spring Boot before document processing is performed.

The separation also allows the Python processing layer to evolve independently from the public API.

## Alternative Considered

A single Spring Boot application containing the API, extraction, policy processing, and model logic could have been implemented.

This was not selected because it would mix public API responsibilities with document and model-processing responsibilities.

## Main Limitation

The implementation is designed for the supplied local assessment dataset and synchronous processing.

Production-scale queues, persistent storage, OCR, distributed processing, and production authentication are outside the assessment scope.

---

# 26. Production Design Note

For approximately 10,000 requests per day containing personal information and a slow, partially documented approval system, I would separate synchronous API handling from long-running processing.

Spring Boot would expose the authenticated public API and persist request metadata. Long-running extraction, policy evaluation, and approval-system integration would be handled asynchronously through a durable queue and independently scalable workers.

I would deploy the services as independently scalable containers behind an API gateway or load balancer. Python workers could scale based on queue depth and processing latency.

The most important security risks would be PII exposure, unauthorized tenant access, prompt injection, insecure model/tool access, secrets leakage, and excessive logging.

I would use managed secrets, encryption in transit and at rest, least-privilege service identities, strict tenant/role authorization, PII-aware logging, and controlled model/tool access.

Operational risks include provider timeouts, malformed outputs, duplicate processing, partial failures, and slow approval-system dependencies. I would use bounded timeouts, idempotency keys, dead-letter handling, structured tracing, metrics, and explicit failure states.

Before committing to a delivery date, I would clarify the approval system API contract, authentication mechanism, expected latency, rate limits, retry/idempotency behavior, PII retention requirements, compliance requirements, availability expectations, and exact business rules for approval and payment eligibility.

---

# 27. Known Limitations

This assessment implementation intentionally does not provide:

- Production authentication
- Persistent database storage
- OCR
- Cloud deployment
- Message queues
- Production approval-system integration
- Automatic claim approval
- Payment initiation
- Employee notifications

These are outside the assessment boundary.

---

# 28. Running the Complete Application

### Terminal 1 - FastAPI

```bash
cd marlabs-python-service
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 - Spring Boot

```bash
cd marlabs-assessment
.\mvnw.cmd spring-boot:run
```

### Services

```text
Spring Boot:
http://localhost:8080

FastAPI:
http://localhost:8000

FastAPI Swagger:
http://localhost:8000/docs
```

---

# 29. Quick API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/answer` | Answer policy questions |
| POST | `/batches` | Process reimbursement document batches |

Both public endpoints are exposed through Spring Boot.

---

# 30. Submission Checklist

Before submission, verify:

- [ ] Spring Boot source is included
- [ ] FastAPI source is included
- [ ] `policies.json` is included
- [ ] Synthetic request files are included
- [ ] Text-based PDF is included
- [ ] Automated tests are included
- [ ] README is included
- [ ] `.gitignore` is included
- [ ] `venv/` is not committed
- [ ] `target/` is not committed
- [ ] `.idea/` is not committed
- [ ] No API keys are committed
- [ ] No passwords or secrets are committed
- [ ] Repository is public
- [ ] Working tree is clean
- [ ] Final commit SHA is captured

---

# 31. Final Git Verification

Check the working tree:

```bash
git status
```

Expected:

```text
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

View recent commits:

```bash
git log --oneline -3
```

Get the full final commit SHA:

```bash
git rev-parse HEAD
```

The final submission should contain:

```text
GitHub Repository URL
+
Full Final Commit SHA
```
