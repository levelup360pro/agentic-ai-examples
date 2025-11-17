# Week 5: Framework Evaluation & Production Architecture

**Status**: Complete ✅   
**Focus**: Framework-agnostic architecture design, CrewAI evaluation (agents/tasks/flow spike), enterprise deployment requirements analysis, Microsoft Agent Framework validation

---

## Executive Summary

Week 5 pivoted from a full CrewAI build to a strategic evaluation after a rapid spike exposed architectural friction with our custom LLMClient. We implemented a minimal CrewAI setup (agents, tasks, and a flow harness) to empirically validate the assessment, then rejected CrewAI early without building the full content-generation notebooks. In parallel, we validated Microsoft Agent Framework for Azure production fit using our custom LLMClient; validation was successful. We will adopt and build in Week 6 using Microsoft Agent Framework instead of LangGraph.

**Key Outcomes**:
- ✅ Framework-agnostic core architecture confirmed (domain logic fully separated from orchestration)
- ✅ Minimal CrewAI spike implemented (agents, tasks, flow) to validate incompatibility with custom LLMClient
- ✅ Early rejection of CrewAI (no full E2E notebooks) based on spike results and prior analysis
- ✅ Microsoft Agent Framework validated for Azure production and for use with our custom LLMClient (adopt in Week 6)
- ✅ Enterprise deployment requirements analyzed (observability, security, compliance for Azure production)

**Architecture Achievement**: Confirmed clean separation between domain logic (ContentGenerator, ContentEvaluator—zero framework dependencies) and orchestration (framework-specific wiring). This allowed fast, objective framework evaluation without touching business logic. Week 4’s LangGraph build proved the pattern; Week 5’s CrewAI spike and Microsoft Agent Framework validation confirmed portability and guided the framework decision.

**Critical Discovery**: Our LLMClient (model-agnostic, cost/latency tracking, OpenAI-native tool-calling, structured logging) is a strategic asset. CrewAI’s agent model expects LiteLLM/LangChain-compatible LLMs; adapting our client would require a sizable adapter with little value-add. Flows-only would ignore most of CrewAI’s features and offer no advantage over LangGraph. Microsoft Agent Framework aligns with Azure production requirements and preserves our LLMClient advantages.

**Production Deployment Analysis**: For Azure in regulated environments, enterprise frameworks (e.g., Microsoft Agent Framework) provide built-in observability (Azure Monitor), native security (Entra ID, VNets, Key Vault), and inherited compliance—reducing production readiness effort by 65–75 hours versus stitching equivalents around open-source orchestrators.

---

## Design Decisions

### Decision 17: Framework-Agnostic Core Services

**Challenge**: Avoid duplicating business logic when comparing frameworks and moving toward production.

**Decision**: Keep all domain logic in plain Python classes (`ContentGenerator`, `ContentEvaluator`, `PromptBuilder`) with zero framework dependencies. Orchestrators (LangGraph, CrewAI, Microsoft Agent Framework) are thin shells that call these services.

**Rationale**:
- **Zero lock-in** and **testability**
- **Maintenance simplicity** (fix once, benefit everywhere)
- **Fast evaluation** (swap orchestrator, keep business logic)

**Alternatives Considered**:
1. Duplicate logic per framework — rejected (divergence risk)
2. Heavy abstraction layer — rejected (over-engineering)
3. “One-size” orchestration facade — rejected (weakest-common-denominator)

**Impact**:
- ✅ Core shared across frameworks
- ✅ Orchestration limited to wiring
- ⚠️ Core API changes require touchpoints in adapters (mitigated by stability discipline)

---

### Decision 18: Orchestration Boundary - Agentic vs Deterministic Split

**Challenge**: Preserve a clear boundary: agentic research vs deterministic generation/evaluation and quality loop.

**Decision**: Agentic planning only for research (tool choice). Generation is single-pass; evaluation owns the accept/regenerate loop. Orchestrator controls `iteration_count`, `max_iterations`.

**Rationale**:
- **Governance** and **auditability**
- **Predictable cost/latency** for gen/eval
- **Framework-agnostic** concept

**Alternatives Considered**:
1. Fully agentic — rejected (opaque loops, governance gaps)
2. Fully deterministic — rejected (research flexibility loss)
3. Agentic evaluation — rejected (audit thresholds break)

**Impact**:
- ✅ LangGraph ToolNode for research; deterministic nodes for gen/eval loop
- ✅ CrewAI (spike): researcher agent possible; kept gen/eval deterministic
- ✅ State fields drive governance/observability

---

### Decision 19: State Fields as API for Control/Audit

**Challenge**: Consistent governance and observability across frameworks.

**Decision**: Treat state fields as an explicit API: `iteration_count`, `max_iterations`, `quality_threshold`, `meets_quality_threshold`, `generation_metadata`, `evaluation_metadata`.

**Rationale**:
- **Compliance readiness** and **traceability**
- **Cross-framework parity** in telemetry
- **Debuggability** without scraping prompts

**Alternatives Considered**:
1. Implicit control — rejected (no governance)
2. Framework-specific state — rejected (breaks parity)
3. Logs-only — rejected (state is source of truth)

**Impact**:
- ✅ Same contracts across orchestrators
- ✅ External dashboards/alerts consume common fields

---

### Decision 20: CrewAI Evaluation and Early Rejection

**Challenge**: Implement CrewAI in Week 5 to compare with LangGraph.

**Action Taken (Spike)**:
- Implemented **minimal CrewAI agents, tasks, and a flow** harness to validate integration.
- Wired planner agent with routing rules and structured output (Pydantic).
- Bound compose/evaluate as tools (return_direct) for deterministic gen/eval.
- Kept research deterministic in the flow to reduce variables.

**Technical Incompatibility (Validated)**:

Our core architecture uses a custom `LLMClient` providing:
- **Unified interface** (OpenAI/Azure/Anthropic/…)
- **Built-in cost tracking** (tokens, latency, provider pricing)
- **Structured logging/retries**
- **OpenAI-native tool-calling**

**CrewAI Architectural Constraint**:
CrewAI agents expect LiteLLM/LangChain-style LLMs. To preserve `LLMClient` we would need:
1. **200–300 line adapter** to mimic `BaseChatModel` and translate tool schemas/callbacks
2. **Duplicated cost/telemetry plumbing** (or lose current instrumentation)
3. **Format translation** (OpenAI tool-calling ↔ LangChain bind_tools)

**Flows-only Option**:
- Using **only** CrewAI Flows (decorators) and calling `LLMClient` directly bypasses agents/tasks/tools—uses ~10% of CrewAI and offers no practical benefit over LangGraph’s explicit graph.

**Decision Rationale**:
1. Minimal spike confirmed adapter complexity with no upside.
2. Flows-only yields no value over LangGraph and worsens observability.
3. LangGraph already meets our requirements (routing accuracy, state/cost tracking).
4. Early exit based on evidence (spike + prior analysis) prevented 20+ hours of low-ROI work.

**Week 5 Revised Scope**:
- Implemented the **CrewAI spike** (agents, tasks, flow) to validate assumptions.
- **Rejected CrewAI** early—did not build full content-generation notebooks.
- Pivoted time to Azure production evaluation and Microsoft Agent Framework validation.

**Lessons**:
- Validate with a spike before committing.
- Preserve proven custom infrastructure (LLMClient) unless a framework provides clear, measurable net benefit.

---

### Decision 21: Production Deployment Requirements for Regulated Industries (Azure) — Microsoft Agent Framework Validated and Adopted

**Challenge**: Select an orchestrator aligned to Azure production for regulated workloads (EU AI Act, GDPR, ISO 27001).

**Analysis**:
- Open-source orchestrators (e.g., LangGraph) meet functional needs but require custom observability (OTel), security (Entra ID/VNets), compliance documentation, and procurement justification (65–90 hours).
- **Microsoft Agent Framework (Microsoft Agent Framework)** on Azure provides:
  - **Built-in observability** via Azure Monitor/App Insights (tracing, cost/latency dashboards)
  - **Native security** (Entra ID, VNets, Key Vault, managed identity)
  - **Inherited compliance** (Azure certifications)
  - **Procurement velocity** (single-vendor, SLAs)

**Validation (Spike)**:
- Built a **minimal Microsoft Agent Framework test notebook** using our `LLMClient`.
- Confirmed we can **preserve LLMClient** (cost tracking, model-agnostic interface, OpenAI-native tool-calling).
- Verified Azure-native integrations (monitoring, identity) meet our production needs.

**Decision**:
- **Adopt Microsoft Agent Framework** for production.
- Week 6 will **build using Microsoft Agent Framework** (replace LangGraph as the primary orchestrator for our solution).

**Trade-off**:
- Accept potential migration effort later (40–60h orchestration rewrite) in exchange for 65–75h saved now and smoother enterprise compliance/procurement.

---

## Architecture Overview

### Framework-Agnostic Core Pattern

- **Domain Layer (framework-agnostic)**: `ContentGenerator`, `ContentEvaluator`, `PromptBuilder` take explicit params and return domain outputs (drafts, `Critique`, metadata). No imports from any orchestrator.
- **Orchestration Layer (framework-specific)**:
  - Week 4: LangGraph (ToolNode for research, deterministic gen/eval loop)
  - Week 5: CrewAI spike (agents/tasks/flow) to validate assumptions, then early rejection
  - Week 6+: Microsoft Agent Framework (Azure-native), preserving domain layer and `LLMClient`

### Orchestration Boundary: Agentic vs Deterministic

- **Research**: agentic decision (tools selection) with deterministic execution
- **Generation/Evaluation**: deterministic; evaluation owns the quality loop and thresholds; orchestrator controls iterations

---

## What Worked

### 1. Framework-Agnostic Architecture Enabled Fast Validation

**Approach**: Domain/orchestration separation. CrewAI spike and Microsoft Agent Framework agent both reused `ContentGenerator`/`ContentEvaluator` without code changes.

**Outcome**: We validated CrewAI’s limitations and Microsoft Agent Framework’s fit quickly, without rewriting business logic. The architecture supports evidence-based framework selection.

**Transferable Pattern**: Keep business rules independent of workflow engines (graphs, crews, agents) to preserve flexibility and ease of evaluation/migration.

---

## What Didn't Work

### 1. CrewAI + Custom LLMClient Integration

**Problem**: CrewAI agent model expects LiteLLM/LangChain-compatible LLMs; our `LLMClient` is a native client with custom telemetry and tool-calling.

**Impact**: Minimal CrewAI spike confirmed a non-trivial adapter would be required. This duplicates telemetry and adds maintenance without clear value.

**Lesson**: Validate framework <-> client compatibility early with a spike; don’t assume “framework-agnostic” at the marketing level implies seamless integration with a custom client.

**Mitigation**: Early rejection; pivot to Microsoft Agent Framework where Azure-native features plus LLMClient preservation align with production goals.

---

## Lessons Learned

### 1. Architectural Compatibility > Framework Popularity

**Discovery**: Preserving `LLMClient` (cost, telemetry, tool-calling) outweighs benefits of adopting CrewAI. Microsoft Agent Framework fits the Azure context and preserves our client.

**Enterprise Transfer**: Choose frameworks based on integration with existing infra and deployment environment, not on hype.

### 2. Framework Value = Features You Actually Use

**Discovery**: CrewAI Flows-only would underutilize the framework (~10%). LangGraph already covered routing/state; Microsoft Agent Framework provides Azure-native production capabilities.

**Checklist**:
- Use >50% of a framework to justify the complexity.
- Unique platform integrations (observability/security/compliance) can justify enterprise frameworks.

### 3. Match Framework to Deployment Environment

**Discovery**: Azure + regulated workloads → Microsoft Agent Framework provides fastest path to compliant production with maintained `LLMClient`.

**Alignment**:
- Azure (regulated): Microsoft Agent Framework
- Kubernetes (self-hosted): open-source (e.g., LangGraph)
- Multi-cloud: open-source
- MVP/startup: open-source

### 4. Document Rejected Approaches

**Discovery**: Keeping the CrewAI spike and rejection rationale demonstrates rigor and prevents second-guessing later.

**ADR Discipline**: Preserve alternatives, criteria, and trade-offs.

---

## Week 5 Outputs

### Documentation Artifacts

- Updated design decisions (including CrewAI spike + rejection, Microsoft Agent Framework validation + adoption)
- Production deployment requirements analysis for Azure (observability, security, compliance)
- Framework-to-environment alignment principle

### Code Artifacts

- **CrewAI spike**: minimal agents, tasks, and flow harness (for planner/gen/eval shape)

### Notebooks

**Testing Notebooks**:
- `week5_agent_framework_test.ipynb`: Microsoft Agent Framework validation

## Progress Against 12-Week Plan

### Month 1: Foundation Complete (Weeks 1-4) ✅

- Week 1: Evaluation framework, infra setup  
- Week 2: RAG system build, corpus testing  
- Week 3: Pattern testing (eval-optimizer winner), model selection  
- Week 4: LangGraph multi-agent, supervisor pattern, 100% routing accuracy

### Week 5: Strategic Inflection Point ✅

- **Planned**: Full CrewAI implementation + comparison  
- **Actual**: CrewAI spike (agents/tasks/flow) → early rejection; Microsoft Agent Framework validation successful; production framework decision made

**Value**: Saved significant integration time; aligned framework choice with Azure production realities while preserving `LLMClient`.

### Month 2 Adjustment: Build on Microsoft Agent Framework (Weeks 6-7)

- **Week 6**: Rebuild the marketing team on Microsoft Agent Framework (Planner/Generator/Evaluator); wire Azure Monitor/App Insights; keep `LLMClient`
- **Week 7**: Azure hardening (Entra ID, VNets, Key Vault), dual-brand workflows; Case Study 1

**If Microsoft Agent Framework had failed**: would have invested in LangGraph with added production integrations. It passed; we adopt Microsoft Agent Framework.

---

## Cost Summary

### Week 5 Costs

**LLM Calls**: €0–€1 (CrewAI and Microsoft Agent Framework spikes used minimal calls; negligible)  
**Infrastructure**: €0

**Total Week 5**: ~€0

### Cumulative Costs

- Week 1: €2.15  
- Week 2: €8.60  
- Week 3: €5.24  
- Week 4: €2.41  
- Week 5: ~€0

**Total (Weeks 1–5)**: ~€18.40

---

## Next Steps

### Week 5 Completion (remaining time)

- Finalize documentation: CrewAI spike results, early rejection rationale, Microsoft Agent Framework validation notes
- Prep Azure resources for Week 6 build (AI Foundry, Monitor, Entra ID/Key Vault baseline)

### Week 6–7: Production Build on Microsoft Agent Framework

- Rebuild content generation workflow on Microsoft Agent Framework (Planner → deterministic gen/eval loop)  
- Integrate Azure Monitor tracing and cost dashboards; enforce budgets/alerts  
- Apply Entra ID (RBAC), VNets, and Key Vault for secrets  
- Dual-brand validation; Case Study 1 publish-ready by end of Week 7

### Weeks 8–12: Deployment & Portfolio

- Week 8: Production polish + Case Study 1 (LevelUp360)  
- Weeks 9–10: Cosmetics brand Case Study 2; governance patterns; evidence pack  
- Weeks 11–12: Portfolio consolidation; outreach targeting 1–2 gig inquiries

---

## Conclusion

Week 5 delivered a rapid, evidence-based framework decision. A **minimal CrewAI spike** (agents/tasks/flow) confirmed the **integration mismatch** with our custom `LLMClient` and led to **early rejection** without investing in full E2E notebooks. In parallel, a **Microsoft Agent Framework spike** validated **Azure-native** production fit while **preserving `LLMClient`** (cost/latency tracking, model-agnostic interface, native tool-calling). We will **adopt Microsoft Agent Framework** and **build in Week 6** on Azure, replacing LangGraph as the primary orchestrator for this solution.

The architecture remains **framework-agnostic at the core**, enabling decisive pivots without rewriting business logic. We continue to measure frameworks by integration fit and production value—not popularity—staying aligned with regulated-industry requirements and Azure operational realities.

---

**Week 5 Status**: Complete ✅   
**Next Milestone**: Week 6 build on Microsoft Agent Framework (adopted)  
**12-Week Progress**: 42% complete (5/12 weeks), foundations strong, production path chosen