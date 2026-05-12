# High Level Design (HLD)

## 1. Purpose
This document describes the **current public implementation** of the `marketing-team` example in this repository.

It intentionally documents the runnable reference system under `/home/runner/work/agentic-ai-examples/agentic-ai-examples/marketing-team`, not the later private production hardening described in parts of `README.md`, `DECISIONS.md`, and the architecture PNGs.

## 2. Scope
### In scope
- Local Gradio-based content generation application
- Brand-configurable content generation for the public reference implementation
- Microsoft Agent Framework workflow used by the UI
- Framework-agnostic core services used by orchestration adapters
- Local RAG implementation, web search integration, and evaluation loop
- Files, data stores, and runtime boundaries present in the public codebase

### Out of scope
- Private Weeks 7-12 Azure production implementation
- HITL approval workflow implementation
- Cloudflare, PostgreSQL + pgvector, OpenTelemetry, Application Insights, Azure Content Safety, Entra ID, and persisted workflow tracing code, because they are not present in the public source tree

## 3. System Summary
The system is a **local-first agentic marketing content generator** for multiple brands.

A user:
1. Loads or uploads a brand YAML configuration.
2. Uploads supporting documents into a local ChromaDB knowledge base.
3. Submits a topic and template from the Gradio UI.
4. Triggers a Microsoft Agent Framework workflow that plans, optionally researches, drafts, evaluates, and optionally regenerates content.
5. Receives generated content, evaluation scores, critique text, and an execution trace.

The public implementation is optimized for **experimentation and reference use**, not for fully governed publishing.

## 4. Business and Technical Goals
- Generate brand-aligned marketing content from reusable brand configs
- Reuse the same core services across orchestration frameworks
- Support retrieval-augmented generation using local persisted vectors
- Support optional external evidence gathering through Tavily search
- Evaluate output quality and allow bounded regeneration
- Preserve enough trace data for debugging and iterative design work

## 5. Architectural Style
The implementation follows a **layered, framework-agnostic core plus orchestration adapters** model.

### 5.1 Layers
| Layer | Responsibility |
|---|---|
| UI | Gradio interface for brand management, knowledge-base management, and content generation |
| Orchestration | Workflow control, routing, state transitions, loop handling |
| Core domain | Prompt building, generation, evaluation, RAG preparation, config validation |
| Infrastructure | LLM provider integration and Tavily search integration |
| Shared tools | Adapter-friendly tool factories and formatting/serialization helpers |
| Data | YAML configs, local ChromaDB, uploaded files, CSV cost logs, markdown reports |

### 5.2 Active orchestration path
The **active path** is the Microsoft Agent Framework implementation under `src/orchestration/microsoft_agent_framework`.

### 5.3 Alternative implementations retained in the repo
- `src/orchestration/langgraph`: historical/alternative workflow implementation
- `src/orchestration/crewai`: evaluation spike retained for comparison history

These modules are present, but the Gradio app invokes the Microsoft Agent Framework workflow.

## 6. High Level Component View
| Component | Role | Key Outcome |
|---|---|---|
| Gradio UI (`app.py`) | Entry point and operator interface | Runs the full local workflow and displays outputs |
| Brand Config Loader | Loads and validates YAML brand definitions | Enforces required schema before runtime |
| Document Loader + RAG Helper | Reads files, chunks content, generates embeddings | Prepares knowledge documents for storage |
| Vector Store | Persists embeddings in local ChromaDB | Enables brand-filtered retrieval |
| Prompt Builder | Builds prompts from config + retrieved context | Keeps prompting logic reusable |
| Content Generator | Calls LLMs for draft generation/regeneration | Produces content from provided context |
| Content Evaluator | Scores content and returns structured critique | Enables threshold-based iteration |
| Planning Agent | Decides whether research is needed | Routes workflow to research or writing |
| Research Executor | Runs RAG and/or web search tools | Produces tool context for writing |
| Generation Executor | Calls generator with thread state and tool contexts | Writes the draft to shared state |
| Evaluation Executor | Calls evaluator and controls loop completion | Stops or triggers another draft cycle |
| LLM Client | Unified provider wrapper for chat/embeddings | Centralizes model calls, retries, and cost logging |
| Tavily Client | Web search provider integration | Retrieves external supporting sources |

## 7. Runtime Flow
### 7.1 Brand setup
- The UI loads available YAML configs from `configs/`.
- A selected or uploaded config is validated.
- A brand-specific `RAGHelper` is initialized from the config.

### 7.2 Knowledge-base ingestion
- Operators upload `.md` or `.txt` files.
- Files are loaded as raw documents.
- Documents are chunked and embedded.
- Chunks are written into the single ChromaDB collection `marketing_content` with brand metadata.

### 7.3 Content generation flow
1. User provides topic, template, examples, and CoT flag.
2. UI builds a workflow input message.
3. Workflow initializes `ContentThreadState`.
4. Planner decides whether to use `rag_search`, `web_search`, both, or neither.
5. If research is needed, the workflow runs the selected tools and loops back to planning.
6. Generation executor builds content using brand config and any tool contexts.
7. Evaluation executor scores the output.
8. If threshold is met or max iterations is reached, the workflow yields the final state; otherwise it loops back to generation.

## 8. Key Data Boundaries
| Boundary | Current Public Implementation |
|---|---|
| Brand configuration | YAML files in `configs/` |
| Knowledge base | Local ChromaDB persisted under `data/chroma_db/` |
| Retrieval isolation | Metadata filter by brand inside one collection |
| Workflow state | In-memory `ContentThreadState` stored in workflow shared state |
| Cost logging | CSV append log in `data/api_calls.csv` |
| Reports and decisions | Markdown documents under `reports/` |

## 9. Deployment View
### 9.1 Public runtime model
The public implementation runs as a **single local Python application** with external API dependencies.

| Runtime element | Type |
|---|---|
| Gradio app | Local Python process |
| Workflow engine | In-process Microsoft Agent Framework workflow |
| Vector store | Local filesystem-backed ChromaDB |
| LLM provider | External API via OpenRouter and/or Azure OpenAI configuration |
| Web search | External Tavily API |
| Config and report storage | Local files in repository folders |

### 9.2 Public implementation characteristics
- Local-first execution
- File-based persistence
- Config-driven behavior per brand
- No public approval/publishing subsystem
- No public cloud deployment assets in this folder for the runnable Week 6 reference

## 10. External Integrations
| Integration | Purpose | Used in public implementation |
|---|---|---|
| OpenRouter/OpenAI-compatible chat API | Content planning, generation, optimization, evaluation | Yes |
| Azure OpenAI-compatible API | Embeddings in workflow builder path | Yes, in workflow code |
| Tavily | External web research | Yes |
| ChromaDB | Local vector persistence | Yes |
| LangSmith | Development tracing decorators on LLM client | Yes |

## 11. Non-Functional Characteristics
### 11.1 Configurability
Brand behavior, model settings, thresholds, chunking parameters, and search settings are driven by YAML.

### 11.2 Extensibility
The core services are reusable across multiple orchestration stacks, which is why LangGraph and CrewAI variants can coexist with the active Microsoft Agent Framework implementation.

### 11.3 Observability
The public implementation provides:
- workflow message trace returned to the UI
- per-call CSV logging for cost/latency
- LangSmith tracing hooks in the LLM client

It does **not** provide the full production observability stack described for private later phases.

### 11.4 Safety and governance
The public implementation includes configuration-based guidance, banned terms, factual accuracy instructions, evaluation, and bounded retry loops.

It does **not** include public-code implementations of:
- human approval gates
- publishing governance workflow
- PII sanitization pipeline
- production identity and audit persistence
- Azure Content Safety enforcement

## 12. Current Implementation Constraints and Notes
1. The public system uses **ChromaDB**, not PostgreSQL + pgvector.
2. The public system is a **reference implementation**; several README and decision entries describe later private production architecture.
3. Retrieval uses **metadata filtering in a shared collection**, not hard per-brand physical separation.
4. The active UI path is **generate-and-display**, not approve-and-publish.
5. The workflow uses a bounded evaluation loop with a default maximum of 3 iterations.
6. The agentic generation path effectively runs a **single-pass generation per loop cycle**; regeneration is controlled by the outer workflow, not by an internal multi-step generation strategy.

## 13. Risks / Documentation Clarifications Required for Accuracy
To reflect the current public code correctly, any consumer of this HLD should distinguish between:
- **public reference implementation**: local UI, ChromaDB, workflow loop, Tavily, YAML configs
- **private production implementation**: Azure infrastructure, HITL lifecycle, PostgreSQL + pgvector, Cloudflare perimeter, OTEL/App Insights, PII and identity controls

Additional alignment notes:
- `DECISIONS.md` Decision 4 and some README sections describe PostgreSQL + pgvector as the production direction; the current public runnable code uses ChromaDB.
- `DECISIONS.md` Decision 5 records a 0.60 retrieval-distance threshold, while the current public brand configs use 0.50.
- The repository contains rendered PNG architecture views under `architecture/`; the referenced Draw.io source is not present in this checkout.

## 14. Conclusion
The current public implementation is best understood as a **config-driven local reference system for agentic content generation experimentation**.

It already contains:
- reusable domain services
- a working multi-step workflow
- local RAG ingestion and retrieval
- structured evaluation and regeneration
- alternative orchestration implementations for comparison

It does not yet expose the full governed production architecture that later documentation discusses.
