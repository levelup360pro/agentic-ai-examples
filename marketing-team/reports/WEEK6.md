# Week 6: Microsoft Agent Framework & Production UI

**Status**: Complete ✅
**Focus**: Microsoft Agent Framework implementation, simple Gradio UI for end-users, RAG stabilization, and transition to production hardening.

---

## Executive Summary

Week 6 marks a pivotal milestone: **the completion of the public reference implementation**. I have successfully migrated the core orchestration to the **Microsoft Agent Framework**, validated its suitability for Azure production environments, and delivered a user-friendly **Gradio UI** that democratizes access to the agentic workflow.

**Key Outcomes**:
- ✅ **Microsoft Agent Framework Migration**: Replaced LangGraph with Microsoft Agent Framework for the primary content workflow, leveraging Azure-native patterns while preserving the custom `LLMClient`.
- ✅ **Production UI**: Delivered a simple yet functional Gradio application (`app.py`) allowing users to configure brands, ingest documents, and generate content.
- ✅ **RAG Stabilization**: Resolved critical metadata and retrieval issues, ensuring reliable context injection for brand-specific content.
- ✅ **Auditability Architecture**: Implemented full prompt capture and thread-centric state, ensuring every decision (routing, research, drafting) is inspectable.
- ✅ **Milestone Reached**: Final public code drop completed. Reference architecture is feature-complete.

**Architecture Achievement**: Built a **custom strongly-typed state model** (`ContentThreadState`) on top of Microsoft Agent Framework's `SharedState` infrastructure, mirroring LangGraph's typed state ergonomics (shared state, strong typing, validation) while utilizing Microsoft's workflow primitives. This approach combines the type safety of Pydantic models with the flexibility of Microsoft Agent Framework's executor pattern.

**Critical Discovery**: The initial "Node" abstraction in the Microsoft Agent Framework implementation was a thin wrapper adding unnecessary indirection. Removing it in favor of **Executor/Agent Separation** simplified the architecture significantly, making Executors the primary callable units and Agents pure domain helpers.

**Production Readiness**: The system demonstrates **production-ready foundations** built through evaluation-driven development (Weeks 1-3: systematic pattern testing, model selection) and production framework implementation (Weeks 4-6: LangGraph, Microsoft Agent Framework). The public reference provides a complete, working system (routing, RAG, evaluation, UI) that anyone can run locally. The architecture is designed for production (framework-agnostic, type-safe, auditable, multi-brand), but production hardening (Azure IaC, Entra ID, VNETs, HITL automation, advanced functionality, advanced observability...) remains private work for Weeks 7+.

**What Changes After Week 6**:

This week marks the transition from "maximum sharing" to "reference implementation + strategic insights." The codebase is now frozen at **v1.0-reference**, providing a stable foundation that demonstrates the full architecture. From Week 7 onward:

**What Continues to be Shared** (Documentation & Insights):
- ✅ **Architecture Diagrams**: Updated designs showing production deployment patterns, governance flows, and infrastructure evolution.
- ✅ **Design Decisions**: Documented trade-offs, what worked, what didn't, and why—the same rigor applied in Weeks 1-6.
- ✅ **High-Level Implementation Guides**: Conceptual explanations of HITL workflows, Azure security integration patterns, observability strategies.
- ✅ **Demos & Videos**: Short recordings showing the live system in action (both brands, approval workflows, monitoring dashboards).
- ✅ **Metrics & Learnings**: Cost analysis, quality trends, operational insights from running the system in production.

**What Becomes Private** (Production IP):
- ❌ **Azure Infrastructure Code**: Full Terraform/Bicep for production environments, CI/CD pipelines, exact MAF/Agent Service deployment scripts.
- ❌ **Production Features**: Advanced functionality, admin dashboards, monitoring panels, ...
- ❌ **Brand-Specific Tuning**: Real scoring rubrics, threshold configurations, prompt engineering strategies that embody LevelUp360/Ossie's competitive advantage.
- ❌ **Governance Implementation**: Detailed approval workflow code, compliance automation, audit trail mechanisms.
- ❌ **Proprietary Integrations**: Client-specific connectors, custom data pipelines, environment-specific optimizations.


## Design Decisions

### Decision 22: Planner/Research/Writer Orchestration Boundary

**Challenge**: Preserving separation of concerns, observability, and parallelism (RAG + Web) while using `LLMClient.get_completion` (no tool-mode) with structured outputs in the Microsoft Agent Framework.

**Discovery Process**:
We needed a way to route between research and writing without the planner executing tools inline or shaping writer prompts, which would couple concerns tightly.

**Solution**: **Two-Pass Planner**.
- **Pass 1 (Pre-Research)**: Accepts `PlanningInput`, decides `route` (research|write) and tool mix (`rag_search`, `web_search`), without executing tools.
- **Pass 2 (Post-Research)**: Accepts `ResearchResult`, evaluates evidence presence, and returns a new `PlanningDecision` (usually to write).

**Rationale**:
- **Clear Metrics**: Enables distinct cost/latency attribution for planning vs. research vs. writing.
- **Retries/Backoff**: Research step can be retried independently of planning logic.
- **Type Safety**: Routing is handled via structured `PlanningDecision` objects.

**Impact**:
- Planner delegates prompt construction to the writer layer.
- Clear separation enables distinct cost/latency attribution for planning, research, and writing steps.

**Alternative Rejected**: Planner executes tools inline. Rejected because it obscures the cost of tools and makes the planner monolithic and harder to test.

---

### Decision 23: Custom Typed State Model for Microsoft Agent Framework Workflows

**Challenge**: Microsoft Agent Framework provides a generic `SharedState` container, but I needed strongly-typed, domain-specific state with validation for the content generation workflow, similar to LangGraph's typed `ContentGenerationState`.

**Solution**: **Custom `ContentThreadState` Pydantic Model**.
- Created a strongly-typed Pydantic model `ContentThreadState` with validation.
- Mirrors LangGraph state shape (topic, brand, loop controls, content).
- Adds planner artefacts (`planning_decision`, `research_result`).
- Stored in Microsoft Agent Framework's workflow shared state infrastructure.

**Rationale**:
- **Type Safety**: Pydantic validation catches errors at state mutation, unlike generic dictionary access.
- **Domain Modeling**: State fields are explicit and documented (not arbitrary keys in `SharedState`).
- **IDE Support**: Strong typing enables autocomplete and type checking across all executors.

**Impact**:
- Introduced custom `ContentThreadState` Pydantic model with full validation.
- All executors (planner, research, writer, evaluator) share a single typed state object.
- Enables IDE autocomplete, type checking, and runtime validation across the workflow.

**Alternative Rejected**: Use Microsoft Agent Framework's generic `SharedState` directly with string keys. Rejected because it sacrifices type safety, validation, and IDE support for a complex multi-step workflow.

---

### Decision 24: Executor/Agent Separation

**Challenge**: The initial "Node" abstraction was a thin wrapper that translated between framework types and executor inputs, adding indirection without value.

**Solution**: **Remove Nodes, Elevate Executors**.
- Executors (`ContentPlanningExecutor`, etc.) now implement domain orchestration logic directly.
- "Agents" remain as reusable domain components (pure logic).
- Executors are the primary callable units wired into workflows.

**Rationale**:
- **Simplicity**: Reduces stack depth and indirection.
- **Alignment**: Matches Microsoft Agent Framework's executor-first model.
- **Wiring**: Simplifies `WorkflowBuilder` configuration.

**Impact**:
- Simplified workflow wiring by eliminating the intermediate node layer.
- Reduced code complexity and improved maintainability.

**Alternative Rejected**: Keep thin node adapter layer. Rejected as it was merely boilerplate code.

---

### Decision 25: Conversation History on Thread State

**Challenge**: Allow agents (planner, generator, evaluator) to see prior conversation context without coupling them to thread types or requiring each executor to manage its own history.

**Solution**: **Centralized History on `ContentThreadState`**.
- `ContentThreadState` includes a `messages` list (LLM-style history).
- Nodes read from this field to populate inputs (e.g., `PlanningInput.previous_messages`).
- Nodes append new entries after each step; Executors never mutate `messages` directly.

**Rationale**:
- **Separation of Concerns**: Nodes own state mutation; Executors own domain behavior.
- **Auditability**: Creates a linear, inspectable history of the workflow execution.
- **Simplicity**: Centralizes history management in one place.

**Impact**:
- Centralized conversation history in `ContentThreadState.messages`.
- Full audit trail of workflow execution available for debugging and compliance.

**Alternative Rejected**: Each executor maintains internal history. Rejected because it fragments state and makes debugging end-to-end flows difficult.

---

### Decision 26: Brand-Agnostic Executors with Per-Call Brand Slices

**Challenge**: Avoiding the creation of new executor instances for every brand configuration, which is memory-inefficient and complex to manage.

**Solution**: **Per-Call Configuration Injection**.
- Executors store only base behavior/config on the instance.
- Brand-specific slices (e.g., model blocks) are passed per-call via typed inputs.

**Rationale**:
- **Reuse**: Allows a single executor instance to serve multiple brands.
- **Simplicity**: Keeps constructors simple and avoids binding long-lived infra objects to a single brand.
- **Ergonomics**: Balances explicitness with ease of use.

**Impact**:
- Single executor instance can serve multiple brands.
- Simplified initialization and reduced memory footprint for multi-tenant scenarios.

**Alternative Rejected**: One executor per brand. Rejected due to scalability concerns (memory footprint, management overhead).

---

### Decision 27: Full Prompt & System Message Capture

**Challenge**: Debugging "why did the agent do that?" requires more than just the output. We need to know exactly what the LLM saw.

**Solution**: **Audit-Grade Prompt Logging**.
- Executors record the *effective* system message and the *full* prompt payload into `state.messages`.
- Added `metadata.type="planner_system"` and `metadata.type="planner_prompt"` entries.

**Rationale**:
- **Explainability**: Allows reconstruction of the exact context for every decision.
- **Debugging**: Critical for explainability, investigating routing failures or content quality issues.
- **Compliance**: Provides a durable audit trail independent of external logging systems.

**Impact**:
- Full prompt capture implemented across all executors.
- Complete reconstruction of LLM context available for every decision point.

**Alternative Rejected**: Log only high-level summaries. Rejected because it's insufficient for deep debugging or compliance audits.

---


## Architecture Overview

### Microsoft Agent Framework Workflow

**Flow**:
START → `StartExecutor` (seeds state) → `ContentPlanningExecutor` (Pass 1: decides route) → `ResearchExecutor` (if needed: executes tools) → `ContentPlanningExecutor` (Pass 2: confirms write) → `ContentGenerationExecutor` (drafts content) → `ContentEvaluationExecutor` (scores & critiques) → `FinalStateExecutor` (or loop back)

**State Management**:
- **`ContentThreadState`**: The backbone of the workflow. It holds the `topic`, `brand_config`, `content`, `critique`, and the linear `messages` history.
- **Executors**: Stateless logic units that transform the state. They read from `ContentThreadState` and return typed results (e.g., `PlanningDecision`, `DraftContent`).
- **WorkflowBuilder**: Wires the executors together into a linear or branching pipeline.

### UI Architecture (Gradio)

**Components**:
- **Brand Manager**: Loads and validates YAML configurations. Initializes the `RAGHelper` with brand-specific settings.
- **Document Ingestion**: Handles file uploads, chunking, and embedding into ChromaDB via `VectorStore`.
- **Content Generator**: The frontend for the agentic workflow. Captures user input (Topic, Template), triggers the workflow, and displays real-time logs and results.
- **Log Viewer**: A dedicated component to visualize the `state.messages` and internal logs for transparency.

---

## Testing & Validation

### Microsoft Agent Framework Parity

**Objective**: Validate that the Microsoft Agent Framework implementation matches the routing accuracy and quality of the Week 4 LangGraph implementation.

**Test Methodology**:
- Re-ran the 22 routing scenarios used in Week 4.
- Compared `PlanningDecision` outputs against Week 4 baselines.

**Results**:
- **Routing Accuracy**: 100% match. The `ContentPlanningAgent` logic (domain layer) remained unchanged, proving the framework-agnostic architecture works.
- **Quality**: Content generation quality remains at 8.5+/10, as the underlying `ContentGenerator` and `ContentEvaluator` classes are identical.

### UI Usability Testing

**Objective**: Ensure the Gradio UI is functional for non-technical users.

**Validation Checks**:
- **Brand Loading**: Successfully loaded config files. Validated error handling for malformed YAMLs.
- **RAG Ingestion**: Uploaded PDF/Text documents. Verified chunks appeared in ChromaDB via `inspect_chroma.py`.
- **Generation**: Ran end-to-end generation for both brands. Verified UI updates with draft and critique.

**Discovery**:
- Resolved port binding conflicts to enable multiple concurrent instances.
- Fixed UI component visibility issues affecting template selection.

---

## What Worked

### 1. Framework-Agnostic Core Pays Off

**Approach**: Because domain logic (`ContentGenerator`, `ContentEvaluator`, `ContentPlanningAgent`) was separated from orchestration in Week 4, migrating to Microsoft Agent Framework was primarily a wiring exercise.

**Outcome**: Ported the entire workflow to a new framework in one week without rewriting any business logic, proving the framework-agnostic architecture design.

### 2. Custom Typed State Model

**Approach**: Building a custom `ContentThreadState` Pydantic model (rather than using generic `SharedState` dictionaries) preserved LangGraph's type safety and validation benefits.

**Outcome**: The Microsoft Agent Framework code maintains the same strong typing as the LangGraph implementation. Type hints and validation catch errors early, and the state structure is self-documenting.

---

## What Didn't Work

### 1. Initial "Node" Abstraction

**Problem**: Initially attempted to wrap executors in a "Node" abstraction layer to strictly mimic LangGraph's pattern.

**Impact**: Created unnecessary boilerplate and added indirection without value.

**Correction**: Removed the abstraction layer, exposing executors directly and simplifying the architecture.

---

## Lessons Learned

### 1. Explainability is a First-Class Citizen

**Discovery**: In a complex agentic workflow, knowing *that* a decision was made isn't enough. You need to know *why*.

**Implication**: Storing the full prompt payload is not "debug logging"—it's a core requirement for enterprise AI. It turns the "black box" into a "glass box". This is critical for compliance.


## Progress Against 12-Week Plan

### Month 2: Production Build (Weeks 5-8)

**Week 5**: ✅ Framework Evaluation (CrewAI rejected, Microsoft Agent Framework selected)
**Week 6**: ✅ **Microsoft Agent Framework Build & UI** (Completed)
- Rebuilt marketing team on Microsoft Agent Framework.
- Delivered Gradio UI for local deployment.
- Finalized public reference implementation (**v1.0-reference**).
- Tagged stable release: Anyone can now run the full system locally.

**Week 7+**: 📅 **Private Production Hardening** (Code Private, Insights Public)
- Azure deployment (Entra ID, VNETs, Key Vault, IaC).
- Production functionality evolution (advanced features, dashboards).
- Governance layers (HITL approval workflows, compliance automation).
- Brand-specific tuning and proprietary optimizations.
- **Shared via**: Architecture diagrams, decision docs, demos, metrics—not full code.

---

## Cost Summary

### Week 6 Costs

**Development & Testing**:
- **Migration Testing**: ~50 runs to validate Microsoft Agent Framework parity.
- **UI Testing**: ~30 end-to-end generation runs during UI development.
- **RAG Debugging**: ~20 embedding calls for metadata fixes.

**Estimated Total**: ~€3.50

**Cumulative Costs**:
- Week 1: €2.15
- Week 2: €8.60
- Week 3: €5.24
- Week 4: €2.41
- Week 5: ~€0.00
- Week 6: ~€3.50
- **Total**: ~€21.90

**Budget Status**: Well within the €60/month budget. The efficiency of the **Eval-Optimizer** pattern and **Two-Pass Planner** (avoiding unnecessary tool calls) continues to keep costs low.

---

## Reference Release & Transition

### Week 6 Milestone: v1.0-reference

This week marks the completion of the **public reference implementation**. The repository is now tagged as **v1.0-reference** and includes:

**What's Included**:
- ✅ **Full Agentic Workflow**: Microsoft Agent Framework orchestration (planning → research → generation → evaluation).
- ✅ **Alternative Implementation**: LangGraph version for framework comparison.
- ✅ **RAG Integration**: Complete vector store setup (ChromaDB), document ingestion, retrieval with brand-specific filtering.
- ✅ **Evaluation Framework**: Automated critique generation, scoring, quality thresholds.
- ✅ **Simple UI**: Functional Gradio application for brand configuration, document upload, and content generation.
- ✅ **Testing Notebooks**: End-to-end validation notebooks demonstrating routing accuracy, quality metrics, and cross-brand workflows.
- ✅ **Documentation**: Architecture diagrams, design decisions (Weeks 1-6), and implementation guides.

**How to Run Locally**:
```bash
# Clone the repository
git clone https://github.com/levelup360pro/levelup360-agentic-ai-examples
cd levelup360-agentic-ai-eil

# Create virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
# OR: source .venv/bin/activate  # Linux/Mac

# Install core framework and example dependencies
pip install -e .
pip install -r /marketing_team/requirements.txt

# Set environment variables (see .env.example)
cp .env.example .env
# Edit .env with your API keys (OPENROUTER_API_KEY, TAVILY_API_KEY, etc.)

# Navigate to the marketing team example
cd examples/marketing_team

# Run the Gradio UI
python app.py

# Access the UI at http://127.0.0.1:7860 (or the port shown in terminal)
```

### What Changes After This Release

**Code Repository Status**: The codebase is now **frozen at v1.0-reference**. This provides a stable, working implementation built using **evaluation-driven development** and **production frameworks** (Microsoft Agent Framework, LangGraph), following production implementation patterns throughout. The architecture demonstrates production-ready foundations—systematic pattern testing (Weeks 1-3), framework-agnostic design (Week 4), strategic framework selection (Week 5), and enterprise-ready orchestration (Week 6).

What's demonstrated: Full agentic workflow with routing accuracy, RAG integration, quality evaluation loops, multi-brand support, auditability, and type-safe state management.

What's not yet implemented: Production hardening (Azure IaC, Entra ID, VNETs), governance automation (HITL workflows, approval gates), advanced observability (Application Insights integration, custom dashboards), and proprietary functionality and brand tuning. The high-level architecture for these capabilities is documented; implementation details will be shared as decisions and patterns (not full code) in coming weeks.


**Continued Knowledge Sharing** (Public):

From Week 7 onward, the journey continues with **production hardening and operational evolution**, shared through documentation and insights rather than full code:

1. **Architecture Diagrams**:
   - Azure deployment patterns (App Services, Container Apps, AKS)
   - Security architecture (Entra ID, VNETs, Managed Identities)
   - Governance flows (HITL approval, compliance automation)
   - Observability patterns (Application Insights, custom dashboards)

2. **Design Decisions**:
   - Same rigor as Weeks 1-6: Challenge → Solution → Rationale → Impact
   - Trade-off analyses for production choices
   - What worked, what didn't, and why
   - Lessons learned from operating at scale

3. **High-Level Implementation Guides**:
   - "How to integrate HITL workflows into agentic systems"
   - "Securing agentic AI on Azure for regulated industries"
   - "Cost optimization strategies for production LLM applications"
   - "Monitoring and alerting for agentic workflows"

4. **Demos & Videos**:
   - Screen recordings of the live system in production
   - Both brands (LevelUp360, Ossie Naturals) generating content
   - Approval workflows in action
   - Monitoring dashboards showing real metrics

5. **Metrics & Operational Insights**:
   - Cost per workflow execution trends
   - Quality score distributions over time
   - Latency breakdowns (planning, research, generation, evaluation)
   - Infrastructure performance data


**What Becomes Private** (Production IP):

1. **Azure Infrastructure as Code**:
   - Full Terraform/Bicep modules for production deployment
   - CI/CD pipeline configurations
   - Exact Microsoft Agent Framework/Agent Service deployment scripts
   - Environment-specific configurations and secrets management

2. **Production Features**:
   - Advanced functionality for enterprise use
   - Admin dashboards for monitoring and control
   - Brand management interfaces
   - Analytics and reporting panels

3. **Brand-Specific Tuning**:
   - Exact scoring rubrics and threshold configurations
   - Proprietary prompt engineering strategies
   - Model selection and temperature tuning per use case
   - Few-shot example libraries
   - Brand voice enforcement rules

4. **Governance Implementation**:
   - Detailed HITL workflow automation code
   - Approval routing logic and escalation rules
   - Compliance checking implementations
   - Audit trail mechanisms and reporting

5. **Proprietary Integrations**:
   - Client-specific API connectors
   - Custom data pipelines
   - Environment-specific optimizations
   - Third-party service integrations

---

## Future Roadmap (Private Phase)

Week 7 and beyond focus on **production hardening and operational maturity**. While the code for these capabilities remains private, the architectural decisions, patterns, and lessons learned will be shared publicly:

---

*This repository remains a living resource for architectural insights and operational learnings, with v1.0-reference as the stable code foundation.*
