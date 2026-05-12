# Design Decisions

_Compiled from `marketing-team/reports/WEEK*.md`. Numbering is normalized sequentially across the weekly reports, and active/superseded status was checked against `marketing-team/README.md` and the rendered architecture diagrams linked there._

_Note: the request referenced a Draw.io source file, but this checkout only contains the rendered PNG architecture views under `marketing-team/architecture/`; those README-linked diagrams were used for alignment._

_Scope note: this file compiles decisions across the full 12-week journey. Some active decisions describe the later private production target state, while the public runnable reference implementation remains the Week 6 local system under `marketing-team/`._

### Decision 1 — Methodological Approach: Evaluation-Driven Development

**Date:** 2026-01-16T07:41:11Z
**Number:** 1
**Status:** active

**Decision**

Use Evaluation-Driven Development as the governing method and defer architecture choices until metrics and experiments are defined.

**Context**

The project needed to avoid assumption-driven design and the failure patterns common in GenAI pilots; the main alternative was an architecture-first approach.

**Why**

Defining success criteria before implementation makes later model, RAG, and orchestration choices measurable instead of opinion-based.

**Consequence**

The project gains a traceable decision trail and recurring experiments, but it must invest time upfront in evaluation design.

**Evidence**

- [WEEK1.md#L24-L39](WEEK1.md#L24-L39)

### Decision 2 — Three-Environment Strategy

**Date:** 2026-01-16T07:41:11Z
**Number:** 2
**Status:** active

**Decision**

Split the system into local, staging, and production environments with separate purposes and cost boundaries.

**Context**

Rapid iteration, production-parity testing, and reliable live operation have conflicting needs; the alternative was a single shared environment.

**Why**

Environment separation preserves developer speed while keeping operational metrics and compliance testing representative.

**Consequence**

Deployment becomes clearer and safer, but environment management and release coordination become ongoing work.

**Evidence**

- [WEEK1.md#L40-L59](WEEK1.md#L40-L59)

### Decision 3 — Model Selection Strategy: Test Before Committing

**Date:** 2026-01-16T07:41:11Z
**Number:** 3
**Status:** superseded

**Decision**

Delay model lock-in until Week 3 and compare predefined configurations against fixed criteria.

**Context**

The initial GPT-4o-mini assumption lacked evidence; alternatives were to pick a default model early or optimize for vendor familiarity.

**Why**

A preregistered test matrix avoids midstream model churn and makes cost, latency, and quality trade-offs explicit.

**Consequence**

The project spends extra evaluation effort up front, but the eventual model choice becomes evidence-backed and auditable.

**Evidence**

- [WEEK1.md#L60-L92](WEEK1.md#L60-L92)
- [WEEK3.md#L28-L69](WEEK3.md#L28-L69)

### Decision 4 — Vector Store: PostgreSQL + pgvector (Semantic Search Baseline, Hybrid Search Optional)

**Date:** 2026-01-16T07:41:11Z
**Number:** 4
**Status:** active

**Decision**

Use PostgreSQL with pgvector as the semantic-search baseline and keep hybrid search as an evidence-gated option.

_Implementation note: the current public reference implementation still uses local ChromaDB; PostgreSQL + pgvector is the later production-direction decision reflected in private Weeks 7-12 material._

**Context**

The system needed durable retrieval, low cost, and room for production operations; alternatives included Azure AI Search, ChromaDB, FAISS, and larger embedding models.

**Why**

PostgreSQL combines persistence, low incremental cost, and operational reuse better than separate managed vector platforms for this workload.

**Consequence**

The architecture gets a production-ready store with future hybrid search headroom, but advanced retrieval optimizations stay deferred until tests justify them.

**Evidence**

- [WEEK1.md#L93-L182](WEEK1.md#L93-L182)

### Decision 5 — RAG Distance Threshold for Quality Control

**Date:** 2026-01-16T07:41:11Z
**Number:** 5
**Status:** active

**Decision**

Apply a 0.60 maximum distance threshold so weak vector matches are dropped instead of forced into prompts.

_Implementation note: the current public brand configs use `max_distance: 0.50`; the earlier 0.60 threshold recorded here reflects the initial decision before later tuning._

**Context**

Top-k retrieval was injecting irrelevant chunks and wasting tokens; the alternative was unfiltered retrieval.

**Why**

Distance filtering improves precision and prevents noisy context from diluting generation quality.

**Consequence**

Some queries intentionally fall back to no RAG context, trading recall for lower cost and cleaner prompts.

**Evidence**

- [WEEK2.md#L27-L53](WEEK2.md#L27-L53)

### Decision 6 — RAG Chunking Strategy (150 Tokens, 30 Overlap)

**Date:** 2026-01-16T07:41:11Z
**Number:** 6
**Status:** active

**Decision**

Chunk source posts into 150-token segments with 30-token overlap instead of embedding full posts.

**Context**

Full-post retrieval returned mostly irrelevant text for paragraph-level needs; the alternative was document-sized embeddings.

**Why**

Smaller overlapping chunks align retrieval granularity with the concepts the generator actually needs.

**Consequence**

Retrieval gets cheaper and more precise, but indexing creates more chunks and requires overlap management.

**Evidence**

- [WEEK2.md#L54-L89](WEEK2.md#L54-L89)

### Decision 7 — LLM-Powered Search Query Optimization

**Date:** 2026-01-16T07:41:11Z
**Number:** 7
**Status:** active

**Decision**

Insert a lightweight LLM step that rewrites long topic prompts into Tavily-safe search queries.

**Context**

Detailed topics exceeded Tavily limits and produced poor search strings; alternatives were manual shortening or disabling search.

**Why**

Query optimization converts verbose intent into concise evidence-seeking terms without losing downstream topic detail.

**Consequence**

Search quality improves with minimal extra latency and cost, but the pipeline adds another model call.

**Evidence**

- [WEEK2.md#L90-L120](WEEK2.md#L90-L120)

### Decision 8 — Search Quality Filtering (Domain Whitelisting)

**Date:** 2026-01-16T07:41:11Z
**Number:** 8
**Status:** active

**Decision**

Filter Tavily results through domain whitelists, exclusions, and score thresholds before they reach generation.

**Context**

Raw search results included low-authority social content; the alternative was accepting all high-ranked results.

**Why**

Trusted-domain filtering increases evidence quality and reduces context pollution.

**Consequence**

Research becomes more reliable, but some potentially useful non-whitelisted sources may be dropped.

**Evidence**

- [WEEK2.md#L121-L149](WEEK2.md#L121-L149)

### Decision 9 — Brand Guidelines Architecture Refactor

**Date:** 2026-01-16T07:41:11Z
**Number:** 9
**Status:** active

**Decision**

Move hard brand constraints into the system message and remove polluting messaging pillars from the user prompt.

**Context**

YAML instructions alone kept forcing irrelevant brand themes into outputs; alternatives were more banned terms, template tweaks, and lower temperature.

**Why**

System-message precedence gives constraint rules the highest authority and removes conflicting signals from user prompts.

**Consequence**

Brand enforcement becomes cleaner and more predictable, but prompt architecture grows more explicit and rigid.

**Evidence**

- [WEEK2.md#L150-L201](WEEK2.md#L150-L201)

### Decision 10 — Corpus Expansion Strategy (Synthetic Post Generation)

**Date:** 2026-01-16T07:41:11Z
**Number:** 10
**Status:** active

**Decision**

Expand the corpus with researched synthetic posts to balance topic coverage instead of only adding more of the same source type.

**Context**

A 10-post corpus failed on diverse queries, and the team needed to separate composition problems from simple size limits; the alternative was indiscriminate corpus growth.

**Why**

A balanced corpus improves semantic match coverage more effectively than a narrowly themed but larger collection.

**Consequence**

Retrieval reliability improves and the corpus becomes reusable for publishing, but synthetic content now needs provenance and quality controls.

**Evidence**

- [WEEK2.md#L202-L243](WEEK2.md#L202-L243)

### Decision 11 — Manual Engagement Tracking (Defer Automation)

**Date:** 2026-01-16T07:41:11Z
**Number:** 11
**Status:** active

**Decision**

Keep engagement tracking manual for Q1 rather than building scraping or browser-automation infrastructure.

**Context**

LinkedIn API limits blocked reliable automated retrieval; alternatives included scraping, browser automation, RSS, and third-party APIs.

**Why**

Manual collection is cheap enough at current volume and preserves focus on proving the system rather than automating a brittle edge case.

**Consequence**

The system avoids fragile integration work now, but analytics collection remains labor-intensive until scale justifies automation.

**Evidence**

- [WEEK2.md#L244-L281](WEEK2.md#L244-L281)

### Decision 12 — Observability Strategy (LangSmith Dev, Application Insights Production)

**Date:** 2026-01-16T07:41:11Z
**Number:** 12
**Status:** superseded

**Decision**

Use LangSmith for development tracing and Azure Application Insights for production observability.

**Context**

The team needed fast prompt-trace feedback during experiments and Azure-native monitoring in production; alternatives were LangSmith everywhere, AI Foundry tracing, or App Insights alone.

**Why**

Each tool fit a different stage: LangSmith for experimentation speed and App Insights for platform-aligned production telemetry.

**Consequence**

Development and production observability stayed fit-for-purpose, but the split architecture was later replaced by a unified OTEL design.

**Evidence**

- [WEEK2.md#L282-L316](WEEK2.md#L282-L316)
- [WEEK9-12.md#L61-L92](WEEK9-12.md#L61-L92)

### Decision 13 — Model Selection Strategy - Evidence-Driven Testing

**Date:** 2026-01-16T07:41:11Z
**Number:** 13
**Status:** superseded

**Decision**

Choose Claude Sonnet 4 with a reference post after a structured comparison of candidate model setups.

**Context**

Week 2 showed GPT-4o-mini could not reliably hold brand constraints; alternatives included GPT-4o variants and Claude without reference grounding.

**Why**

Total editing cost, not raw inference price, made the higher-quality configuration the cheaper operational choice.

**Consequence**

Output quality and publishability improved, but later provider-agnostic model configuration superseded a single fixed model choice.

**Evidence**

- [WEEK3.md#L28-L69](WEEK3.md#L28-L69)
- [WEEK9-12.md#L93-L107](WEEK9-12.md#L93-L107)

### Decision 14 — Orchestration Pattern Architecture - Three Approaches

**Date:** 2026-01-16T07:41:11Z
**Number:** 14
**Status:** active

**Decision**

Compare single-pass, reflection, and evaluator-optimizer orchestration patterns under the same evaluation regime.

**Context**

The system needed to know whether iterative critique justified its extra cost and latency; the alternative was committing to one pattern without comparison.

**Why**

Side-by-side pattern testing isolates the quality contribution of orchestration itself instead of confounding it with prompt or model changes.

**Consequence**

The project gains an evidence base for workflow shape, but incurs extra experimental complexity and evaluation effort.

**Evidence**

- [WEEK3.md#L70-L109](WEEK3.md#L70-L109)

### Decision 15 — Dynamic Rubric Generation from Brand Config

**Date:** 2026-01-16T07:41:11Z
**Number:** 15
**Status:** active

**Decision**

Generate evaluation rubrics directly from the same brand configuration used for generation.

**Context**

Pattern comparisons required a shared source of truth; the alternative was maintaining separate manual rubrics.

**Why**

Reusing brand config keeps generation and evaluation aligned as requirements evolve.

**Consequence**

The evaluation layer stays synchronized automatically, but rubric behavior becomes coupled to config quality.

**Evidence**

- [WEEK3.md#L110-L127](WEEK3.md#L110-L127)

### Decision 16 — Evaluation System Calibration - Temperature Uniformity

**Date:** 2026-01-16T07:41:11Z
**Number:** 16
**Status:** active

**Decision**

Standardize evaluation temperature at 0.3 across all compared patterns.

**Context**

Earlier comparisons used different temperatures and produced artificial score gaps; the alternative was leaving pattern-specific evaluator settings in place.

**Why**

Uniform evaluator randomness is necessary for fair pattern comparison.

**Consequence**

Reported quality differences become more trustworthy, but some evaluator tuning freedom is intentionally sacrificed.

**Evidence**

- [WEEK3.md#L128-L152](WEEK3.md#L128-L152)

### Decision 17 — Evaluation System Calibration - Violation Detection Rules

**Date:** 2026-01-16T07:41:11Z
**Number:** 17
**Status:** active

**Decision**

Clarify the evaluator’s violation taxonomy and reweight the rubric to emphasize factual accuracy.

**Context**

The judge missed obvious violations and hallucinated others; alternatives were keeping the ambiguous prompt or relying on manual review alone.

**Why**

Explicit detection rules reduce false positives and false negatives in AI-as-a-judge scoring.

**Consequence**

Evaluation becomes stricter and more reliable, but the rubric is more opinionated and must be maintained carefully.

**Evidence**

- [WEEK3.md#L153-L183](WEEK3.md#L153-L183)

### Decision 18 — Architecture Correction - Deterministic to Agentic

**Date:** 2026-01-16T07:41:11Z
**Number:** 18
**Status:** active

**Decision**

Replace caller-controlled boolean routing with a supervisor that decides research strategy from the topic.

**Context**

The initial design only mimicked agentic behavior because the caller still chose the workflow; the alternative was to keep deterministic orchestration parameters.

**Why**

Real agent autonomy requires the orchestration graph to react to planner decisions rather than preset flags.

**Consequence**

The workflow becomes genuinely agentic and auditable, but orchestration logic grows more complex.

**Evidence**

- [WEEK4.md#L30-L60](WEEK4.md#L30-L60)

### Decision 19 — Config-Driven Architecture - ROI-Justified Refactoring

**Date:** 2026-01-16T07:41:11Z
**Number:** 19
**Status:** active

**Decision**

Move model and prompt-related settings out of code and into brand configuration files.

**Context**

Hardcoded settings blocked A/B tests and required redeployments for routine tuning; the alternative was to leave configuration scattered in classes.

**Why**

Externalized configuration makes tuning cheap, reversible, and brand-specific without code churn.

**Consequence**

The system becomes easier to experiment with, but startup validation and configuration discipline become mandatory.

**Evidence**

- [WEEK4.md#L61-L98](WEEK4.md#L61-L98)

### Decision 20 — Framework-Agnostic Core Architecture

**Date:** 2026-01-16T07:41:11Z
**Number:** 20
**Status:** superseded

**Decision**

Keep domain logic in reusable classes and make LangGraph nodes thin wrappers.

**Context**

Week 5 would compare orchestration frameworks and needed stable business logic underneath; the alternative was embedding rules directly in node functions.

**Why**

Separating domain logic from orchestration allows objective framework comparison and simpler testing.

**Consequence**

Reuse improved immediately, but later hexagonal architecture formalized this boundary more completely.

**Evidence**

- [WEEK4.md#L99-L140](WEEK4.md#L99-L140)
- [WEEK8.md#L36-L65](WEEK8.md#L36-L65)

### Decision 21 — Framework-Agnostic Core Services

**Date:** 2026-01-16T07:41:11Z
**Number:** 21
**Status:** superseded

**Decision**

Preserve plain-Python core services and treat orchestrators as thin shells around them.

**Context**

Framework comparison and production migration both risked duplicating business logic; alternatives included duplication, heavy abstraction, or a weakest-common-denominator facade.

**Why**

Plain services maximize portability with minimal architectural overhead.

**Consequence**

Core behavior stays reusable across frameworks, but adapter touchpoints must evolve whenever core APIs change.

**Evidence**

- [WEEK5.md#L29-L51](WEEK5.md#L29-L51)
- [WEEK8.md#L36-L65](WEEK8.md#L36-L65)

### Decision 22 — Orchestration Boundary - Agentic vs Deterministic Split

**Date:** 2026-01-16T07:41:11Z
**Number:** 22
**Status:** active

**Decision**

Keep research planning agentic, but keep generation and evaluation deterministic and orchestrator-controlled.

**Context**

The workflow needed flexibility in evidence gathering without losing governance over costs, thresholds, and iteration loops; alternatives were fully agentic or fully deterministic flows.

**Why**

This split preserves tool-selection adaptability while keeping quality control explicit and auditable.

**Consequence**

Governance improves and cost stays predictable, but the architecture must maintain a sharp boundary between planning and execution.

**Evidence**

- [WEEK5.md#L52-L74](WEEK5.md#L52-L74)

### Decision 23 — State Fields as API for Control/Audit

**Date:** 2026-01-16T07:41:11Z
**Number:** 23
**Status:** superseded

**Decision**

Treat workflow state fields as an explicit cross-framework control and audit contract.

**Context**

Different orchestrators needed consistent governance and telemetry semantics; alternatives were implicit state, framework-specific state, or logs-only tracking.

**Why**

Shared state contracts make debugging, dashboards, and controls portable across orchestrators.

**Consequence**

Observability became structured and comparable, but later typed state modeling replaced this looser contract.

**Evidence**

- [WEEK5.md#L75-L96](WEEK5.md#L75-L96)
- [WEEK6.md#L70-L93](WEEK6.md#L70-L93)

### Decision 24 — CrewAI Evaluation and Early Rejection

**Date:** 2026-01-16T07:41:11Z
**Number:** 24
**Status:** active

**Decision**

Reject CrewAI after a minimal spike showed it would fight the custom LLM client and observability model.

**Context**

Week 5 needed a real framework comparison; alternatives were a full CrewAI build or a flows-only compromise.

**Why**

The required adapter complexity duplicated proven infrastructure without offering meaningful upside over existing orchestration.

**Consequence**

The project saves integration time and preserves its core client design, but forecloses CrewAI-specific workflow features.

**Evidence**

- [WEEK5.md#L97-L140](WEEK5.md#L97-L140)

### Decision 25 — Production Deployment Requirements for Regulated Industries (Azure) — Microsoft Agent Framework Validated and Adopted

**Date:** 2026-01-16T07:41:11Z
**Number:** 25
**Status:** superseded

**Decision**

Adopt Microsoft Agent Framework as the production orchestrator for the Azure-regulated target environment.

**Context**

Azure deployment needed observability, identity, networking, compliance posture, and procurement fit; the main alternative was staying on open-source orchestrators.

**Why**

Microsoft Agent Framework aligned with Azure-native controls and reduced enterprise hardening effort.

**Consequence**

Production fit improved quickly, but later decisions expanded this into full protocol-level adoption and deeper platform integration.

**Evidence**

- [WEEK5.md#L141-L166](WEEK5.md#L141-L166)
- [WEEK8.md#L186-L217](WEEK8.md#L186-L217)
- [README.md#L60-L66](../README.md#L60-L66)

### Decision 26 — Planner/Research/Writer Orchestration Boundary

**Date:** 2026-01-16T07:41:11Z
**Number:** 26
**Status:** active

**Decision**

Use a two-pass planner that decides strategy before research and confirms progression after research.

**Context**

Planning, research, and writing were getting too intertwined inside a single orchestration step; the alternative was an inline planner that executed tools directly.

**Why**

Separating passes gives clean cost attribution, isolated retries, and typed routing decisions.

**Consequence**

Workflow stages become clearer and easier to observe, but the planner now runs twice on research paths.

**Evidence**

- [WEEK6.md#L46-L69](WEEK6.md#L46-L69)

### Decision 27 — Custom Typed State Model for Microsoft Agent Framework Workflows

**Date:** 2026-01-16T07:41:11Z
**Number:** 27
**Status:** active

**Decision**

Wrap Microsoft Agent Framework shared state in a custom Pydantic `ContentThreadState`.

**Context**

Generic key-value shared state was too weak for a multi-step content workflow; the alternative was direct string-key access.

**Why**

Strong typing and validation catch state errors early and improve developer ergonomics.

**Consequence**

Workflow code becomes safer and clearer, but state evolution now requires schema maintenance.

**Evidence**

- [WEEK6.md#L70-L93](WEEK6.md#L70-L93)

### Decision 28 — Executor/Agent Separation

**Date:** 2026-01-16T07:41:11Z
**Number:** 28
**Status:** active

**Decision**

Remove the redundant node layer and let executors own orchestration while agents remain reusable domain helpers.

**Context**

The initial Microsoft Agent Framework node abstraction only translated types and added indirection; the alternative was keeping the wrapper layer.

**Why**

Executor-first design matches the framework model and simplifies call paths.

**Consequence**

Wiring and maintenance become simpler, but the architecture becomes more opinionated around executor boundaries.

**Evidence**

- [WEEK6.md#L94-L115](WEEK6.md#L94-L115)

### Decision 29 — Conversation History on Thread State

**Date:** 2026-01-16T07:41:11Z
**Number:** 29
**Status:** active

**Decision**

Store the full conversation history centrally on thread state instead of inside individual executors.

**Context**

Multiple workflow components needed prior context without fragmenting history; the alternative was executor-local history management.

**Why**

A single shared history supports auditability and avoids duplicated context plumbing.

**Consequence**

End-to-end traces become easier to inspect, but history management must be disciplined to avoid state bloat.

**Evidence**

- [WEEK6.md#L116-L137](WEEK6.md#L116-L137)

### Decision 30 — Brand-Agnostic Executors with Per-Call Brand Slices

**Date:** 2026-01-16T07:41:11Z
**Number:** 30
**Status:** active

**Decision**

Keep executors reusable across brands and inject brand-specific configuration per call.

**Context**

One-executor-per-brand would waste memory and complicate lifecycle management; the alternative was brand-bound instances.

**Why**

Per-call injection preserves reuse while keeping constructors simple and infrastructure objects long-lived.

**Consequence**

Multi-brand scaling improves, but every call site must pass the right brand slice explicitly.

**Evidence**

- [WEEK6.md#L138-L158](WEEK6.md#L138-L158)

### Decision 31 — Full Prompt & System Message Capture

**Date:** 2026-01-16T07:41:11Z
**Number:** 31
**Status:** active

**Decision**

Persist the effective system message and full prompt payload for each LLM decision point.

**Context**

Output-only logging could not explain why the system routed or generated a certain way; the alternative was high-level summary logging.

**Why**

Full prompt capture turns debugging and audit from guesswork into reconstruction.

**Consequence**

Explainability improves substantially, but prompt logs increase storage volume and require careful sensitivity controls.

**Evidence**

- [WEEK6.md#L159-L180](WEEK6.md#L159-L180)

### Decision 32 — Separate Terraform Project for Container App Deployment

**Date:** 2026-01-16T07:41:11Z
**Number:** 32
**Status:** active

**Decision**

Split Azure infrastructure and Container App deployment into separate Terraform projects connected by remote state.

**Context**

AI Foundry provisioning states blocked app deployment in a single Terraform apply; alternatives were retries, delays, or longer timeouts in one project.

**Why**

Separate state files isolate resource cadences and remove non-terminal infrastructure updates from the application deployment path.

**Consequence**

CI/CD becomes more reliable, but the infrastructure stack now spans multiple Terraform workspaces and backends.

**Evidence**

- [WEEK7.md#L34-L61](WEEK7.md#L34-L61)

### Decision 33 — GitHub Actions Build & Deploy Workflow

**Date:** 2026-01-16T07:41:11Z
**Number:** 33
**Status:** active

**Decision**

Build container images in GitHub Actions and push only images to ACR before Terraform deployment.

**Context**

The pipeline needed secure automation for a private repo; alternatives included ACR Tasks, Azure DevOps, and manual deployment.

**Why**

GitHub-hosted builds keep source inside GitHub while preserving traceable image tags and flexible environment control.

**Consequence**

Delivery becomes automated and auditable, but pipeline secrets and workflow maintenance move into GitHub.

**Evidence**

- [WEEK7.md#L62-L91](WEEK7.md#L62-L91)

### Decision 34 — Unified Application Codebase for Local and Azure Deployment

**Date:** 2026-01-16T07:41:11Z
**Number:** 34
**Status:** active

**Decision**

Keep one application entry point and select storage and provider behavior from environment variables.

**Context**

Separate local and production apps would drift and double the test surface; alternatives were split apps or a PostgreSQL-only local setup.

**Why**

Environment-driven switching maximizes parity while preserving a simple local workflow.

**Consequence**

The same artifact runs in both environments, but configuration correctness becomes critical.

**Evidence**

- [WEEK7.md#L92-L120](WEEK7.md#L92-L120)

### Decision 35 — PostgreSQL Managed Identity Authentication

**Date:** 2026-01-16T07:41:11Z
**Number:** 35
**Status:** active

**Decision**

Use Azure AD managed identity for PostgreSQL authentication instead of database passwords.

**Context**

Password-based access added rotation, secret retrieval, and Key Vault dependencies; the alternative was storing DB secrets.

**Why**

Managed identity removes shared secrets and fits Azure’s native trust model.

**Consequence**

Security and operations improve, but the deployment becomes more tightly aligned with Azure identity services.

**Evidence**

- [WEEK7.md#L121-L151](WEEK7.md#L121-L151)

### Decision 36 — Hexagonal Architecture - Framework-Agnostic Core with Ports & Adapters

**Date:** 2026-01-16T07:41:11Z
**Number:** 36
**Status:** active

**Decision**

Formalize the system as hexagonal architecture with protocol-defined ports and framework-specific adapters.

**Context**

The project needed durable reuse across orchestration frameworks and infrastructure implementations; alternatives were tight Agent Framework coupling or ad-hoc wrappers.

**Why**

Ports and adapters isolate business logic from framework churn while preserving full-feature integrations where needed.

**Consequence**

The core becomes future-proof and testable, but adapter layers and protocol evolution add architectural overhead.

**Evidence**

- [WEEK8.md#L36-L65](WEEK8.md#L36-L65)
- [README.md#L21-L22](../README.md#L21-L22)
- [README.md#L145-L146](../README.md#L145-L146)

### Decision 37 — Dual-Protocol LLM Adapter - LLMClientProtocol + ChatClientProtocol

**Date:** 2026-01-16T07:41:11Z
**Number:** 37
**Status:** active

**Decision**

Implement a single adapter that satisfies both the core LLM protocol and Agent Framework chat protocol.

**Context**

Core services and Agent Framework components needed different interfaces to the same LLM client; alternatives were separate wrappers or instrumenting the raw client directly.

**Why**

One dual-protocol adapter unifies observability and avoids duplicated integration code.

**Consequence**

All LLM calls share the same telemetry path, but the adapter becomes a critical integration point.

**Evidence**

- [WEEK8.md#L66-L95](WEEK8.md#L66-L95)

### Decision 38 — Hexagonal Tools Architecture - Framework-Agnostic Core with Framework Adapters

**Date:** 2026-01-16T07:41:11Z
**Number:** 38
**Status:** active

**Decision**

Put tool logic in framework-agnostic core functions and wrap them with framework-specific decorators.

**Context**

LangGraph and Agent Framework use incompatible tool declaration models; alternatives were duplicated tool files or one framework’s tooling only.

**Why**

Adapter wrappers preserve a single source of truth for tool behavior while satisfying each framework.

**Consequence**

Adding a new orchestrator becomes cheaper, but tool contracts now span both core and adapter layers.

**Evidence**

- [WEEK8.md#L96-L126](WEEK8.md#L96-L126)

### Decision 39 — Simplified Research Architecture - Direct Tool Execution Over LLM-Based Research Agent

**Date:** 2026-01-16T07:41:11Z
**Number:** 39
**Status:** active

**Decision**

Let the research executor run tools directly from the planner’s decision instead of adding a separate research agent.

**Context**

A research chat agent would repeat tool-selection logic the planner had already performed; the alternative was an LLM-based researcher.

**Why**

Direct execution cuts redundant model calls while preserving the same research capability.

**Consequence**

Cost and latency fall, but the planner must remain strong enough to make accurate tool choices upfront.

**Evidence**

- [WEEK8.md#L127-L156](WEEK8.md#L127-L156)

### Decision 40 — Brand-Agnostic Configuration for Search and Fact-Checking

**Date:** 2026-01-16T07:41:11Z
**Number:** 40
**Status:** active

**Decision**

Move search preferences and fact-checking settings into brand YAML configuration.

**Context**

Different brands needed different trusted domains and verification patterns; alternatives were hardcoded lists or a single global config.

**Why**

Brand-level config keeps search behavior tunable without code deployment and matches the existing configuration pattern.

**Consequence**

Multi-tenant customization improves, but configuration sprawl must be governed.

**Evidence**

- [WEEK8.md#L157-L185](WEEK8.md#L157-L185)

### Decision 41 — Full Microsoft Agent Framework Adoption (Option A)

**Date:** 2026-01-16T07:41:11Z
**Number:** 41
**Status:** active

**Decision**

Adopt Agent Framework protocols and builders fully rather than using the framework as a thin wrapper.

**Context**

The team had to choose between manual observability wrappers, a hybrid migration, or full platform adoption; alternatives were the wrapper-only and hybrid paths.

**Why**

Full adoption unlocks built-in telemetry, multi-agent patterns, MCP integration, and Azure Functions hosting.

**Consequence**

The system gains deeper ecosystem capabilities, but the architecture commits more strongly to Microsoft abstractions.

**Evidence**

- [WEEK8.md#L186-L217](WEEK8.md#L186-L217)
- [README.md#L60-L66](../README.md#L60-L66)
- [README.md#L178-L182](../README.md#L178-L182)

### Decision 42 — BlobConfigLoader for Brand Configuration Storage

**Date:** 2026-01-16T07:41:11Z
**Number:** 42
**Status:** active

**Decision**

Store cloud brand configs in Azure Blob Storage and load them with managed identity.

**Context**

Azure Files would require access keys, and baking configs into images slowed updates; alternatives were keyed file shares or image-bundled configs.

**Why**

Blob storage matches the no-keys principle while preserving runtime configuration changes.

**Consequence**

Config deployment becomes passwordless and dynamic, but local and cloud loaders both need to be maintained.

**Evidence**

- [WEEK8.md#L218-L246](WEEK8.md#L218-L246)

### Decision 43 — Cloudflare as Security Perimeter for Access Control

**Date:** 2026-01-16T07:41:11Z
**Number:** 43
**Status:** active

**Decision**

Put Cloudflare at the edge as the primary perimeter for DDoS protection, bot management, WAF, and zero-trust access.

**Context**

The application needed strong access control and attack absorption for sensitive content workflows; alternatives were application-only auth, Azure WAF/App Gateway, or VPN/IP allowlists.

**Why**

Moving the security boundary to Cloudflare reduces origin exposure and delegates commodity edge security to a specialized network.

**Consequence**

Application code can stay focused on business logic, but the deployment now depends on Cloudflare policy configuration and its observability boundary.

**Evidence**

- [WEEK9-12.md#L27-L60](WEEK9-12.md#L27-L60)
- [README.md#L35-L36](../README.md#L35-L36)

### Decision 44 — OpenTelemetry Observability Architecture with Application Insights Integration

**Date:** 2026-01-16T07:41:11Z
**Number:** 44
**Status:** active

**Decision**

Use hybrid observability with automatic OTEL from BaseChatClient plus manual spans for business logic, exported to Application Insights.

**Context**

The production system needed both system metrics and decision-level tracing; alternatives were logs-only, self-hosted Jaeger, or App Insights without OTEL.

**Why**

Hybrid OTEL captures both low-level LLM telemetry and high-level workflow reasoning without excessive custom instrumentation.

**Consequence**

Debugging and audit improve substantially, but teams must manage span design, sampling, and attribute discipline.

**Evidence**

- [WEEK9-12.md#L61-L92](WEEK9-12.md#L61-L92)
- [README.md#L45-L46](../README.md#L45-L46)
- [README.md#L181-L182](../README.md#L181-L182)

### Decision 45 — Dual-Model Architecture for Provider-Agnostic LLM Configuration

**Date:** 2026-01-16T07:41:11Z
**Number:** 45
**Status:** active

**Decision**

Define both development and production model choices declaratively in config with automatic provider detection.

**Context**

The system runs on different providers across environments and needed a single artifact; alternatives were environment-bound model selection or multiple separate configs.

**Why**

Dual-model config decouples deployment environment from model choice and keeps provider details out of business logic.

**Consequence**

Switching providers becomes a config change, but configuration schemas become more complex.

**Evidence**

- [WEEK9-12.md#L93-L107](WEEK9-12.md#L93-L107)
- [README.md#L60-L66](../README.md#L60-L66)

### Decision 46 — HITL Storage and Approval Architecture (PostgreSQL, Folder-per-Status, Two Gates)

**Date:** 2026-01-16T07:41:11Z
**Number:** 46
**Status:** active

**Decision**

Use PostgreSQL as the system of record, store markdown bodies by status, and enforce two explicit human approval gates.

**Context**

YAML-only content handling could not support governed multi-step workflows; alternatives were pure file storage or ad-hoc status models.

**Why**

A canonical state machine with durable metadata supports auditability, cost control, and operational clarity.

**Consequence**

HITL flows become governable and resumable, but storage reconciliation and status maintenance become core operational concerns.

**Evidence**

- [WEEK9-12.md#L108-L135](WEEK9-12.md#L108-L135)
- [README.md#L35-L36](../README.md#L35-L36)
- [README.md#L145-L146](../README.md#L145-L146)

### Decision 47 — Hexagonal Persistence and Service Ports for HITL Content

**Date:** 2026-01-16T07:41:11Z
**Number:** 47
**Status:** active

**Decision**

Add explicit service and persistence protocols for HITL content, checkpoints, and orchestration-facing services.

**Context**

HITL UI and services were coupled directly to PostgreSQL and filesystem classes; the alternative was continuing direct concrete calls.

**Why**

Protocols extend the project’s hexagonal discipline to human-governed content management.

**Consequence**

Testing and swappability improve, but more abstraction layers must be maintained.

**Evidence**

- [WEEK9-12.md#L136-L160](WEEK9-12.md#L136-L160)

### Decision 48 — Deterministic, Serialized Workflow Execution for HITL Content

**Date:** 2026-01-16T07:41:11Z
**Number:** 48
**Status:** active

**Decision**

Serialize HITL generation and regeneration behind a single workflow lane and use synchronous persistence from background threads.

**Context**

Concurrent UI-driven workflows caused event-loop and connection-pool failures; alternatives were fine-grained async concurrency or per-request service isolation.

**Why**

For low-volume HITL work, deterministic correctness matters more than throughput.

**Consequence**

Operators get stable execution and recovery behavior, but throughput is intentionally capped.

**Evidence**

- [WEEK9-12.md#L161-L186](WEEK9-12.md#L161-L186)

### Decision 49 — Persisted Workflow Traces and UI-Agnostic Workflow Views for HITL Content

**Date:** 2026-01-16T07:41:11Z
**Number:** 49
**Status:** active

**Decision**

Persist each workflow as a curated JSON trace and expose UI-agnostic trace and summary views.

**Context**

Rich runtime state existed, but there was no coherent per-content trace artifact for humans to inspect; alternatives were relying on Application Insights or aggregate summaries only.

**Why**

A stable trace artifact makes governance, demos, and debugging understandable outside raw logs.

**Consequence**

Each content item gains replayable audit history, but trace storage and schema evolution must be managed.

**Evidence**

- [WEEK9-12.md#L187-L217](WEEK9-12.md#L187-L217)
- [README.md#L45-L46](../README.md#L45-L46)

### Decision 50 — PII Sanitization Architecture for HITL and Agentic Workflow

**Date:** 2026-01-16T07:41:11Z
**Number:** 50
**Status:** active

**Decision**

Apply centralized PII sanitization at workflow entry and after research synthesis using a shared `PIIGuard`.

**Context**

Raw human input and retrieved evidence could carry PII into LLM prompts and logs; alternatives were per-executor checks or trusting upstream hygiene.

**Why**

Two explicit sanitization boundaries cover all LLM-facing text without duplicating calls across the workflow.

**Consequence**

PII leakage risk drops and auditability improves, but the system must preserve both sanitized and original records appropriately.

**Evidence**

- [WEEK9-12.md#L218-L243](WEEK9-12.md#L218-L243)
- [README.md#L35-L36](../README.md#L35-L36)

### Decision 51 — HITL Identity Logging with Entra User GUID (No PII)

**Date:** 2026-01-16T07:41:11Z
**Number:** 51
**Status:** active

**Decision**

Persist the authenticated Entra user GUID for HITL actions while excluding names and email addresses.

**Context**

Approval and regeneration actions needed attributable human accountability without expanding the application’s personal-data footprint; alternatives were no identity logging, full PII logging, or relying only on upstream identity logs.

**Why**

A stable opaque GUID is sufficient for audit and insurance needs while preserving privacy by design.

**Consequence**

Approvals become attributable and reconstructable, but the solution depends on upstream Easy Auth identity propagation.

**Evidence**

- [WEEK9-12.md#L244-L266](WEEK9-12.md#L244-L266)
- [README.md#L35-L36](../README.md#L35-L36)
