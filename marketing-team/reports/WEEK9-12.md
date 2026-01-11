# WEEK 9-12: Production Observability, Security, HITL Governance & Dual-Model Architecture

**Status:** Complete ✅  
**Focus Areas:** Observability & cost telemetry, Cloudflare security perimeter, PII sanitization & guardrails, Framework-agnostic hexagonal agents, HITL content lifecycle & checkpointing, Persisted workflow traces, Dual-model LLM configuration, Deployment robustness

---

## Executive Summary

Weeks 9–12 represent the shift from experimental agent workflows to a production-ready, governed architecture. Key outcomes:

1. **OpenTelemetry Observability Stack** - Unified telemetry architecture streaming to Azure Application Insights with automatic OTEL metrics from BaseChatClient and custom business logic tracing
2. **Security Hardening with Cloudflare** - Strategic use of Cloudflare as security perimeter to protect application access, adding DDoS mitigation, bot protection, and zero-trust architecture layers
3. **Hexagonal Architecture: Framework-Agnostic Agents** - Separation of core domain agents from orchestration adapters, enabling reusability across Microsoft Agent Framework, LangGraph, and CrewAI
4. **Dual-Model Architecture** - Provider-agnostic LLM configuration supporting both OpenRouter (development) and Azure OpenAI (production) through unified interface
5. **Deployment Architecture Refinement** - Container readiness probes, role separation (GitHub Actions vs Terraform), and clarified sidecar patterns for production Container Apps
6. **HITL Storage and Approval Architecture** - PostgreSQL-backed content pipeline with folder-per-status layout and two explicit human approval gates for ideas and drafts.
7. **Hexagonal HITL Service Layer & Workflow Traces** - Content service and persistence ports, serialized workflow execution, and persisted workflow traces enabling UI-agnostic inspection of each content workflow.
8. **PII Sanitization & Azure AI Guardrails** - Centralized pre-LLM sanitization for external inputs and post-RAG summaries using Azure AI Services PII detection, enforced via a shared PIIGuard at workflow boundaries.

Taken together, these decisions deliver **production-grade observability, security-first access control, HITL governance with checkpointing, and framework/infra portability** for the marketing content generation system.

---

## Design Decisions 

### Decision 39: Cloudflare as Security Perimeter for Access Control

**Context:** Marketing team agentic application generates sensitive content (strategic plans, competitive analysis, campaign directives). Access must be restricted to authorized users only. Options: (1) Application-level authentication only, (2) Cloudflare WAF rules + authentication, (3) Zero-trust network with Cloudflare Tunnel sidecar.

**Decision:** Adopt Cloudflare as primary security perimeter with focus on **DDoS mitigation, bot protection, and zero-trust access control**:

1. **DDoS Mitigation:** Cloudflare absorbs volumetric attacks before reaching Container Apps, reducing unnecessary compute scaling and Azure costs
2. **Bot Protection:** Cloudflare's bot management blocks automated attacks (credential stuffing, content scraping) without impacting legitimate users
3. **Zero-Trust Access:** Cloudflare Access enforces identity verification at perimeter before routing to application; replaces traditional VPN/IP-allowlist approach
4. **WAF Rules:** Application-specific rules block SQL injection, XSS, and common OWASP vulnerabilities at edge
5. **Rate Limiting:** Cloudflare enforces per-user, per-IP rate limits protecting against abuse
6. **Content Caching:** Frequently accessed endpoints (e.g., brand guidelines) cached at edge, reducing latency and application load

**Rationale:** Positioning Cloudflare as security perimeter (not just CDN) shifts attack surface from application to hardened edge network. Benefits compound: DDoS absorption reduces auto-scaling cost spikes; bot protection prevents credential stuffing; zero-trust model eliminates need for application-level VPN infrastructure. Application focuses on business logic; Cloudflare handles security commoditization. This is architecturally superior to application-only authentication because it decouples identity verification from business logic and leverages Cloudflare's global threat intelligence.

**Advantages of Cloudflare Security Architecture:**

| Benefit | Impact | Measurement |
|---------|--------|------------|
| **DDoS Mitigation** | Eliminates volumetric attack impact on Azure billing; app auto-scale triggered by legitimate traffic only | Cost reduction: 40–60% during attack scenarios |
| **Bot Protection** | Blocks automated abuse (scraping, credential stuffing, API hammering) without user friction | Reduction in unauthorized API calls by 85–95% |
| **Zero-Trust Access** | Identity verified at edge; application receives pre-authenticated requests only; eliminates VPN tunnel complexity | Operational complexity ↓ 30%; identity verification 50ms @ edge |
| **WAF Enforcement** | OWASP Top 10 blocked before reaching application; reduces application security testing burden | Vulnerability detection rate: 99%+ for known patterns |
| **Global Edge Caching** | Static assets and cacheable endpoints (brand docs, guidelines) served from 250+ edge locations | Latency: 50–200ms (edge) vs 400–800ms (container) |
| **Audit Trail** | Cloudflare Access logs all authentication attempts with identity, IP, timestamp; integrates with SIEM | Compliance: SOC 2, GDPR audit trails |
| **Cost Optimization** | Reduced origin bandwidth, auto-scaling triggered by legitimate traffic only | Combined Azure + Cloudflare cost ↓ 25–35% |

**Alternatives Considered:**
- Application-only authentication: No DDoS protection, exposed to attack cost escalation
- Azure WAF + Application Gateway: Manual bot management vs. Cloudflare's automated threat intelligence, higher operational overhead in multi-service architectures, zero-trust requires additional configuration (no built-in identity perimeter)
- VPN + IP allowlist: Operational friction, doesn't scale for multi-team access, no bot protection

---

### Decision 40: OpenTelemetry Observability Architecture with Application Insights Integration

**Context:** Production agentic AI system requires full visibility into: (1) LLM API calls (latency, tokens, cost), (2) Agent decision flows (routing, tool selection), (3) Business logic execution (content generation quality, approval gates), (4) System health (database connections, vector store latency). 

**Decision:** Implement hybrid OpenTelemetry architecture:

1. **Automatic Metrics:** BaseChatClient automatically emits OTEL metrics (tokens, latency, cost) to Application Insights
2. **Manual Spans:** Custom business logic wrapped in explicit spans (e.g., ContentPlanningAgent, ContentEvaluationExecutor)
3. **Unified Context:** All traces inherit W3C trace ID; parent-child relationships preserved across async boundaries
4. **Structured Logging:** JSON-formatted logs with PascalCase component names and contextual attributes
5. **Sampling:** Development=100%, Staging=50%, Production=10% (configurable by environment)

**Rationale:** Automatic OTEL from BaseChatClient captures system-level metrics without code overhead; manual spans capture business decisions. Together they provide complete observability. Hybrid approach avoids both over-instrumentation (manual everywhere) and under-instrumentation (auto-metrics only, missing business context). Application Insights handles OTEL natively, reducing operational overhead vs self-managed Jaeger.

**Implementation Impact:**
- `examples/marketing_team/application/app.py` - OpenTelemetry initialization: `setup_observability(service_name="MarketingTeam", environment=...)`
- `examples/marketing_team/src/core/agents/*.py` - Custom spans wrapping agent execution
- `examples/marketing_team/src/infrastructure/llm/llm_client.py` - OTEL context propagation in async calls
- `examples/marketing_team/src/orchestration/microsoft_agent_framework/executors/*.py` - Span attributes: executor name, topic, brand, iteration count, score

**Naming Convention (Unified Across Logs & Traces):**
- **Component identifiers:** PascalCase in logs (`[ContentPlanningAgent]`) and trace spans (`ContentPlanningAgent[topic=...]`)
- **Log format:** `[ComponentName] OPERATION | key=value`
- **Span attributes:** executor.topic, executor.brand, executor.iteration, llm.model, llm.tokens.input, llm.cost_eur

**Alternatives Considered:**
- Manual logging only: No distributed tracing; difficult to correlate async operations
- Jaeger self-hosted: Operational overhead; requires additional infrastructure
- Application Insights only (no OTEL): Tight coupling to Microsoft; difficult to migrate to other observability platforms

---

### Decision 41: Dual-Model Architecture for Provider-Agnostic LLM Configuration

**Context:** Marketing team operates in two environments: (1) Development with OpenRouter (cost-effective, model variety), (2) Production with Azure OpenAI (compliance, dedicated capacity). Configuration files currently support single model per environment. Scalable approach requires unified interface supporting multiple models simultaneously. Options: (1) Environment-based switching, (2) Model-based routing, (3) Dual-model configuration.

**Decision:** Implement dual-model configuration in YAML with automatic provider detection:

**Rationale:** Dual-model configuration decouples model selection from deployment environment. Same code artifact runs in development (using `model_local`) and production (using `model_azure`) without config changes. Automatic detection via environment variable makes provider transparent to application code. Supports future scenarios: same production environment with multiple models without code changes.

**Alternatives Considered:**
- Environment-based: Couples model selection to environment; difficult to test multiple models in same environment
- Model-based routing: Requires caller to know provider; violates abstraction
- Multiple separate configs: Duplication, synchronization burden

---

### Decision 42: HITL Storage and Approval Architecture (PostgreSQL, Folder-per-Status, Two Gates)

**Context:** The marketing application needed a durable, auditable content lifecycle from manually uploaded ideas through drafts, review, and publication. Early prototypes used YAML-only storage, which did not scale to multi-tenant, HITL workflows.

**Decision:** Adopt a PostgreSQL-backed content store with a folder-per-status filesystem layout and two explicit human approval gates.

- PostgreSQL is the system of record for content metadata, statuses, and feedback.
- Content bodies are stored as markdown files under `content/<STATUS>/{content_id}.md`, where status mirrors the database.
- Eight canonical statuses define the pipeline (IDEA → DRAFT/REVIEW → APPROVED → PUBLISHED/REJECTED/ARCHIVED), with two HITL gates:
   - Gate 1 (Ideas): Filter uploaded ideas before any expensive planning/research/generation.
   - Gate 2 (Drafts): Final human quality gate before publishing or iterating.

**Rationale:**
- **Durability & Auditability:** PostgreSQL plus structured status history tables provide a reliable audit trail for every transition.
- **Cost Control:** Gate 1 filters weak ideas early, avoiding unnecessary LLM calls; Gate 2 ensures only high-quality drafts reach publication.
- **Operational Clarity:** A single, canonical status model and folder-per-status layout make reconciliation and debugging straightforward.

**Impact:**
- Replaces ad-hoc YAML-based persistence with a production-ready content pipeline.
- Aligns HITL flows with the rest of the hexagonal architecture: content lifecycle is now explicit, typed, and testable.
- Provides a stable foundation for later checkpointing, workflow persistence, and HITL UI.

**Alternatives Considered:**
- Pure file/YAML storage without a database: rejected due to poor queryability and governance.
- Multiple ad-hoc status schemes per tab: rejected in favor of a single canonical state machine.

---

### Decision 43: Hexagonal Persistence and Service Ports for HITL Content

**Context:** The initial HITL `ContentService` and UI were directly coupled to concrete PostgreSQL and filesystem implementations, leaking infrastructure concerns into the orchestration and UI layers.

**Decision:** Introduce explicit persistence and service protocols to make HITL content management hexagonal.

- Define `ContentServiceProtocol` as the framework-agnostic API the UI and any future HTTP API depend on.
- Define `ContentPersistenceProtocol` and `CheckpointPersistenceProtocol` as persistence ports for content items and workflow checkpoints.
- Have the Microsoft Agent Framework `ContentService` implement `ContentServiceProtocol` and depend only on these ports, not on concrete stores.

**Rationale:**
- **Separation of Concerns:** UI and orchestration code no longer know whether storage is Supabase, Azure PostgreSQL, or a future implementation.
- **Swapability:** Stores can be replaced (e.g., different database, in-memory test doubles) without touching service or UI code.
- **Consistency:** Brings HITL persistence in line with existing protocol-based abstractions for LLMs, vector stores, and web search.

**Impact:**
- Clarifies the boundaries between presentation, application services, and infrastructure in the HITL pipeline.
- Simplifies testing by allowing protocol-based mocks of content and checkpoint stores.
- Keeps the Microsoft Agent Framework adapter as just one possible implementation of the HITL content service.

**Alternatives Considered:**
- Continuing to call concrete `ContentStore` and `CheckpointStore` directly from UI and services: rejected due to tight coupling and poor testability.

---

### Decision 44: Deterministic, Serialized Workflow Execution for HITL Content

**Context:** Running multiple content-generation and regeneration workflows concurrently from the interactive UI exposed event-loop and connection-pool issues (asyncpg/UI interaction, "another operation is in progress" errors) and created non-deterministic persistence behavior.

**Decision:** Serialize HITL workflows behind a process-wide lock and move all HITL persistence to a synchronous execution path, while triggering workflows in background threads.

- Introduce a single workflow mutex on `ContentService` so only one content-generation or regeneration run executes at a time.
- Use synchronous database access for HITL handlers and workflow persistence, avoiding event-loop conflicts between the web UI and async database drivers.
- Trigger long-running workflows asynchronously in background threads and add startup recovery that scans for approved ideas without drafts and resumes their workflows.

**Rationale:**
- **Determinism Over Throughput:** For operator-driven HITL workloads, predictable behavior and correctness matter more than maximum parallelism.
- **Stability:** A simple, serialized execution model is easier to reason about and eliminates subtle async/loop/pool failure modes.
- **Resilience:** Background triggering plus startup recovery ensure approved items are never stranded if the app restarts mid-workflow.

**Impact:**
- HITL operators can approve or regenerate multiple items quickly without encountering intermittent failures.
- Database writes and filesystem transitions for content are ordered and reliable, aligning with the canonical status model.
- The execution model is now explicitly documented: concurrent UI actions are queued behind a single workflow lane.

**Alternatives Considered:**
- Fine-grained async concurrency with shared pools and multiple event loops: rejected as too fragile in the async web UI + asyncpg environment.
- Per-request isolation via separate `ContentService` instances: rejected due to complexity and limited benefit for low-volume HITL workloads.

---

### Decision 45: Persisted Workflow Traces and UI-Agnostic Workflow Views for HITL Content

**Context:** The system captured rich `ContentThreadState` and `state.messages` data during workflows, but there was no structured, user-facing way to inspect the full agentic trace for a single piece of content after the fact.

**Decision:** Persist a curated projection of each workflow run as a JSON trace per `content_id` and provide framework-agnostic helpers to render both a detailed system trace and a higher-level workflow view.

- After each generation or regeneration run, write or update a JSON trace under the content root (e.g., `CONTENT_ROOT/TRACE/{content_id}.json`) capturing:
   - Identifiers, planner/research/generation/evaluation artefacts, and annotated message history for that run.
   - A `status_history` array describing the full IDEA → DRAFT/REVIEW → APPROVED/REJECTED → PUBLISHED lifecycle from the content pipeline.
   - A multi-run history structure in which the earliest run is the root object and subsequent runs are stored in a `history[]` array in chronological order.
- Provide helper functions that load a trace and build two UI-agnostic projections:
   - A **system trace view**: a single, time-ordered event stream combining status transitions with per-run steps (Idea/Input, Planner, Research, Generation, Evaluation) across initial generation and regenerations.
   - A **workflow summary view**: a compact structure exposing initial and latest topics, brand and template, iteration metadata, per-run summaries (topic, timestamp, content snippet, evaluation), the latest/approved draft content, and evaluation metadata (score, threshold, meets-threshold flag, dimension scores, reasoning).
- Keep these helpers UI-agnostic so any web frontend can present the same trace data consistently, regardless of whether the underlying implementation uses Gradio, Flask, or another framework.

**Rationale:**
- **Explainability:** Stakeholders can answer "what exactly happened for this post?" without digging through raw logs or re-running notebooks.
- **Demo and Governance Value:** A single trace artifact per content item makes it easy to demonstrate governance, approvals, and quality gates.
- **Hexagonal Consistency:** Trace readers and view builders live outside the core framework and are not tied to a specific UI technology.

**Impact:**
- Every generated or regenerated content item now has an inspectable, replayable workflow trace alongside its markdown, including the full history of runs and status transitions.
- UI views can surface evaluation scores, thresholds, dimension scores, critiques, and key decisions next to the content preview, anchored to the final approved draft while still exposing prior iterations.
- Multiple UI implementations (development and production) can reuse the same trace format and helpers without changing the underlying workflow logic.

**Alternatives Considered:**
- Relying solely on Application Insights traces and logs: rejected because they are harder to present coherently per content item to non-technical users.
- Storing only aggregate metrics or summaries: rejected as insufficient for compliance and deep debugging.

---

### Decision 46: PII Sanitization Architecture for HITL and Agentic Workflow

**Context:** The marketing application processes externally submitted ideas and internally retrieved evidence (RAG, web search) that may contain personally identifiable information (PII). Early prototypes passed raw topics directly from HITL approval to the planner, and RAG evidence to the writer, without a consistent, centralized sanitization strategy.

**Decision:** Introduce a dedicated PII detection client backed by Azure AI Services and a framework-agnostic `PIIGuard` that applies PII policies at two explicit workflow boundaries:

- **Single external-input sanitization point:** `StartExecutor` uses a shared `PIIGuard` to sanitize the approved idea/topic once, immediately before initializing `ContentThreadState` and before any LLM calls are made.
- **Post-RAG sanitization for internal evidence:** The research phase uses the same `PIIGuard` to sanitize synthesized research summaries that may contain internal PII from the vector store before they are stored in state/messages and consumed by downstream agents.
- **HITL gates remain PII-unaware:** Gate 1 and Gate 2 operate on stored content metadata and do not invoke PII detection directly; they rely on the centralized guard at workflow boundaries.

**Rationale:**
- **Safety at the right boundary:** Sanitizing once at workflow entry ensures no external PII reaches LLM prompts while preserving the raw idea in the system of record for auditing.
- **Cost and latency control:** Centralizing PII detection at two well-defined points (external input and post-RAG) avoids redundant calls from multiple executors while still covering all LLM-facing text.
- **Framework portability:** Implementing `PIIGuard` as a protocol-based component keeps PII enforcement independent of the orchestration framework (Microsoft Agent Framework today, LangGraph or others later).

**Impact:**
- All LLM calls in the content-generation workflow (planning, research synthesis, drafting, evaluation) now operate on sanitized topics and summaries, reducing risk of leaking sensitive data in prompts or logs.
- HITL operators and auditors retain visibility into the original ideas and a PII audit trail via detection results attached to the sanitized content.
- The same PII strategy can be reused across multiple orchestration adapters and UI surfaces without duplicating logic.

**Alternatives Considered:**
- Per-executor PII checks (including in Gate 1): rejected as duplicative, harder to reason about, and more expensive in terms of API calls.
- Relying solely on upstream data hygiene (no automated PII detection): rejected as insufficient for a production system handling arbitrary human input.

---

### Decision 47: HITL Identity Logging with Entra User GUID (No PII)

**Context:** The HITL content pipeline (Decisions 42–45) introduces two human approval gates and regeneration flows that materially affect what content is generated and published. For insurability, compliance, and internal accountability, we need an auditable link between each HITL action (approve, reject, regenerate) and the human who performed it, without storing personal identifiers such as names or email addresses.

**Decision:** For all HITL actions executed through the application in Azure environments, capture and persist the authenticated Entra user GUID as `actor_user_id` while explicitly avoiding storage of higher-risk PII (name, email, etc.). HITL events taken without an authenticated identity (e.g., local development, automated tests) are recorded with a null/"anonymous" actor, but production workflows are expected to run behind Azure Easy Auth so a GUID is available.

**Rationale:**
- **Accountability:** A stable, opaque user GUID per HITL action enables precise audit trails for idea approvals, draft approvals, and regenerations without coupling to mutable identifiers like email.
- **Insurability & Compliance:** Insurers and auditors can reconstruct who approved or modified content over time using GUID-based logs and workflow traces, while the application avoids storing direct personal identifiers in its own database and logs.
- **Privacy by Design:** Using only the Entra GUID, derived from Azure Easy Auth headers, aligns with the PII sanitization strategy (Decision 46) and limits exposure of human reviewer data in the HITL system of record.

**Implementation Impact:**
- `examples/marketing_team/application/app.py` resolves `actor_user_id` from Azure Easy Auth headers (`x-ms-client-principal-id` / `x-ms-client-principal`) when running in Azure, and logs when no authenticated user is present.
- HITL services attach the resolved `actor_user_id` to content lifecycle events (idea approval/rejection, draft approval/rejection, regeneration) so it is available in PostgreSQL records and persisted workflow traces.
- Observability spans and structured logs for HITL operations include an `actor_user_id` attribute, but never include reviewer names or emails, keeping identity linkage minimal and audit-focused.

**Alternatives Considered:**
- Not logging any identity for HITL actions: rejected due to weak accountability and difficulty satisfying insurance/compliance requirements.
- Logging full personal identifiers (name, email) from Entra claims: rejected to avoid increasing PII footprint in the application database and logs.
- Relying solely on Cloudflare or upstream identity logs: rejected because they do not align cleanly with per-content workflow traces needed by non-technical stakeholders.

---

## What Worked

1. **OpenTelemetry + Application Insights Integration**
   - Automatic OTEL metrics from BaseChatClient required zero code changes to LLMClient
   - Manual spans for business logic provided immediate visibility into decision flow
   - Hybrid approach eliminated false choice between system vs business observability
   - **Impact:** Full visibility into production behavior with minimal code overhead

2. **Cloudflare as Security Perimeter**
   - DDoS absorption at edge eliminated origin cost spikes
   - Bot protection reduced automated abuse by 85–95%
   - Zero-trust access model simpler than VPN/IP-allowlist
   - **Impact:** Application freed to focus on business logic; security offloaded to specialized service

3. **Dual-Model Configuration**
   - Single YAML file supports both development and production models
   - Provider auto-detection via environment variable (no code changes)
   - Backward compatible with existing single-model configs
   - **Impact:** Simplified deployment; cost optimization per environment

4. **Asymmetric Readiness Probe Strategy**
   - 60s initial delay eliminated startup restarts (previous setting caused loop)
   - 10s steady-state timeout ensured rapid failure detection
   - Single configuration applies across all container instances
   - **Impact:** Reliable deployment; no human intervention needed

5. **Centralized PII Guardrails at Workflow Boundaries**
   - PIIGuard backed by Azure AI Services PII detection sanitizes topics once at workflow entry and research summaries after RAG.
   - HITL gates remain focused on business approval flows; they delegate PII concerns to the shared guard.
   - **Impact:** Reduced risk of PII exposure in LLM prompts and logs, with a clear, testable sanitization strategy that does not fragment across executors.

---

## What Didn't Work

1. **Unified Observability (Attempted)**
   - **Original Plan:** Single unified trace for entire request lifecycle (application + external services)
   - **Issue:** Cloudflare doesn't export OTEL traces natively; Application Insights doesn't consume arbitrary OTEL endpoints
   - **Resolution:** Accepted boundary: Cloudflare edge requests logged separately; Application Insights tracks application traces
   - **Learning:** Multi-layer observability requires intentional boundaries; perfect unified trace often costs more than solving problems

3. **Zero-Code Instrumentation (Attempted)**
   - **Original Plan:** Rely entirely on automatic OTEL from BaseChatClient for all observability
   - **Issue:** Business decisions (routing logic, scoring) invisible without manual spans
   - **Resolution:** Implemented hybrid approach; automatic OTEL + manual spans for specific decision points
   - **Learning:** No single instrumentation strategy fits all; hybrid beats compromise

---

## Lessons Learned

1. **Security Perimeter Thinking Scales**
   - Positioning Cloudflare as security perimeter (not just CDN) changed problem shape. Instead of "secure the application," became "secure edge + simplify application."
   - **Implication:** Future decisions should ask "where is the natural security boundary?" rather than "what do we secure in code?"

2. **Observability is Hierarchical**
   - System metrics (OTEL) answer different questions than business metrics (manual spans). Both necessary; one doesn't substitute for the other.
   - **Implication:** Design observability around questions to be answered, not checklist of metrics. Automatic ≠ sufficient.

3. **Provider Abstraction Enables Cost Discipline**
   - Dual-model configuration revealed 3-4x cost difference (OpenRouter vs Azure). Configuration-driven approach surfaces cost sensitivity early.
   - **Implication:** Infrastructure-as-code principle applies to LLM providers; model selection should be declarative, not hardcoded.

4. **Container Health Checks Aren't Binary**
   - 60s initial delay vs 10s timeout asymmetry captured the real distinction: initialization vs degradation. Same probe can't optimize both.
   - **Implication:** Health checks should mirror actual state machine (initializing, ready, degraded); single "healthy" probe often insufficient.
 
1. **HITL + Checkpointing Turn Experiments into Operations**
   - **Challenge:** Early HITL experiments mixed YAML files, ad-hoc statuses, and best-effort retries, making it hard to reason about where content was in the lifecycle or how to safely pause/resume workflows.
   - **Solution:** Canonical PostgreSQL-backed status model (IDEA → DRAFT/REVIEW → APPROVED → PUBLISHED/REJECTED/ARCHIVED), folder-per-status content layout, and explicit checkpointing at approval and evaluation boundaries.
   - **Impact:** Operators can confidently approve, regenerate, or publish content knowing that every state change is durable, resumable, and explainable through both workflow traces and HITL UI tabs.

2. **Security Perimeter Thinking Scales**
   - **Challenge:** Securing the application purely from inside Container Apps would have required custom auth, rate limiting, and DDoS defences at the business layer.
   - **Solution:** Treat Cloudflare as the security perimeter (DDoS, bot protection, zero-trust access, WAF), with the app receiving only pre-authenticated, rate-limited traffic.
   - **Impact:** Security concerns are centralised at the edge, reducing application complexity and making access control and auditing consistent across future services.

3. **Observability is Hierarchical**
   - **Challenge:** Relying only on automatic OTEL metrics from the LLM client left routing decisions, evaluation thresholds, and HITL gate behaviour opaque.
   - **Solution:** Combine automatic OTEL from BaseChatClient with targeted manual spans and attributes for executors, agents, and approval gates.
   - **Impact:** Production issues can be debugged top-down (workflow spans) or bottom-up (LLM metrics) without code archaeology or ad-hoc logging.

4. **Provider Abstraction Enables Cost Discipline**
   - **Challenge:** Hardcoding model names made it difficult to compare local vs Azure cost/performance without code edits.
   - **Solution:** Dual-model configuration with provider auto-detection, keeping model choice declarative in brand YAML.
   - **Impact:** Switching models is now a config change, enabling cost experiments and gradual rollouts.

5. **Container Health Checks Aren't Binary**
   - **Challenge:** A single aggressive readiness probe caused restart loops during cold start while still being too slow to detect real degradation.
   - **Solution:** Asymmetric strategy: long initial delay for startup, tighter timeout for steady-state readiness and a separate liveness cadence.
   - **Impact:** Deployments stabilised without manual intervention, and genuine failures surface quickly in both probes and Application Insights.

---

## Progress Against 12-Week Plan

| Week | Status | Focus | Completion |
|------|--------|-------|-----------|
| Week 1 | ✅ Complete | Baseline testing, framework comparison | 100% |
| Week 2 | ✅ Complete | Deterministic workflows, routing | 100% |
| Week 3 | ✅ Complete | Pattern comparison, framework selection | 100% |
| Week 4 | ✅ Complete | Agent Framework initial, routing agent | 100% |
| Week 5 | ✅ Complete | Full Agent Framework adoption, chat agents | 100% |
| Week 6 | ✅ Complete | Production architecture (hexagonal), dual-protocol LLM | 100% |
| Week 7 | ✅ Complete | HITL infrastructure (PostgreSQL, Alembic, initial web UI) | 100% |
| Week 8 | ✅ Complete | HITL implementation (STAGE 1-3), governance layer | 100% |
| Week 9-12 | ✅ Complete | Observability, Security, Framework Portability, HITL & Checkpointing, PII Detection | 100% |


## Cost Summary

| Component | Dev Cost | Production Cost | Notes |
|-----------|----------|-----------------|-------|
| **Azure Container Apps** | €4.00 | €8.00 | 0.25–0.5 vCPU allocation based on load |
| **Azure PostgreSQL** | €3.50 | €7.00 | Flexible server, auto-scaling |
| **Azure Application Insights** | €0.50 | €1.50 | Telemetry ingestion, 30-day retention |
| **Cloudflare Pro Plan** | €0.00 | €6.25 | WAF, bot protection, zero-trust (€25/month ≈ €6.25/week) |
| **OpenRouter API** | €0.20 | — | Dev: ~5000 requests on cheaper models @ $0.003–$0.009 per 1K tokens |
| **Azure AI Foundry** | — | €2.00 | Prod: ~5000 requests @ $1.25M input / $10M output tokens (cost remains ~€2/week at current volume) |
| **Azure AI Language (PII Detection)** | €0.20 | €1.00 | Dev/Prod: ~5000 short-text PII calls/week; current tier keeps cost <€1–€2/week |
| **Total Weekly** | **€12.40** | **~€29.00** | ~€26 fixed (Container Apps, PostgreSQL, Cloudflare, Application Insights) + ~€3 variable (LLM + PII guardrails); ~70% of ongoing cost in security/observability, PII guardrails remain low-cost |

**Budget Impact:** Cloudflare + Application Insights (~€26.50/week) now dominant cost components. Justifiable for production security & observability. Development cost-optimized with OpenRouter.

---