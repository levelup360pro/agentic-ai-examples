# Low Level Design (LLD)

## 1. Purpose
This document describes the detailed design of the **current public implementation** located in `/home/runner/work/agentic-ai-examples/agentic-ai-examples/marketing-team`.

It focuses on executable code paths and local data structures, and it intentionally separates them from later private production features described elsewhere.

## 2. Source Scope
### Primary runtime sources
- `app.py`
- `src/core/**`
- `src/infrastructure/**`
- `src/orchestration/microsoft_agent_framework/**`
- `src/shared/tools/**`
- `configs/*.yaml`

### Supporting documentation sources
- `README.md`
- `reports/DECISIONS.md`
- `architecture/*.png`

## 3. Module Layout
| Module | Responsibility |
|---|---|
| `app.py` | Gradio app, startup initialization, brand loading, document ingestion, workflow invocation |
| `src/core/utils/config_loader.py` | Brand config loading and validation |
| `src/core/utils/paths.py` | Canonical project paths |
| `src/core/rag/document_loader.py` | File loading into raw document objects |
| `src/core/rag/rag_helper.py` | Chunking and embedding preparation |
| `src/core/rag/vector_store.py` | ChromaDB wrapper |
| `src/core/prompt/templates.py` | Prompt template registry |
| `src/core/prompt/prompt_builder.py` | Prompt assembly from config and contexts |
| `src/core/generation/content_generator.py` | Deterministic and agentic generation logic |
| `src/core/evaluation/content_evaluator.py` | Structured critique schema and evaluation logic |
| `src/infrastructure/llm/llm_client.py` | Chat/embedding provider wrapper, retry, cost logging |
| `src/infrastructure/search/tavily_client.py` | Tavily API integration |
| `src/shared/tools/*.py` | Tool factories used by orchestrators |
| `src/orchestration/microsoft_agent_framework/**` | Active workflow, agents, executors, state models |
| `src/orchestration/langgraph/**` | Alternative workflow implementation |
| `src/orchestration/crewai/**` | Historical framework spike |

## 4. Startup and Application State
### 4.1 `initialize_app()`
At UI startup, `initialize_app()` creates and stores the following in global `APP_STATE`:
- `completion_client`: `LLMClient` configured for OpenRouter
- `embedding_client`: `LLMClient` configured for OpenRouter
- `vector_store`: `VectorStore` using `data/chroma_db`
- `collection`: Chroma collection `marketing_content`
- `document_loader`: `DocumentLoader`
- `rag_helper`: initially `None`, later brand-specific
- `collection_name`: `marketing_content`

### 4.2 Global state model
`APP_STATE` is a simple process-global dictionary used by the Gradio callbacks. It is not persisted outside the running process.

## 5. Brand Configuration Design
### 5.1 Storage model
Brand definitions are stored as YAML files under `configs/`.

### 5.2 Loader behavior
`load_brand_config(brand)`:
- resolves `CONFIG_DIR / <brand>.yaml`
- parses YAML
- validates presence and structure of required sections
- returns the validated config dict

### 5.3 Required sections
`_validate_brand_config()` requires:
- `name`
- `positioning`
- `messaging_pillars`
- `context_specific_points`
- `content_generation_rules`
- `factual_accuracy`
- `models`
- `voice`
- `formatting_rules`
- `retrieval`

### 5.4 Required model groups
- `content_planning`
- `content_generation`
- `content_evaluation`
- `content_optimization`
- `search_optimization`
- `vectorization`

### 5.5 Important implementation note
The filename `cosmetics.yaml` contains `name: "aurora"`.

Current behavior:
- the **filename stem** is the lookup key for loading configs from disk
- the **`name` field** becomes the runtime brand identifier once the config is loaded and passed into generation/retrieval flows

This makes the mismatch a known public-reference inconsistency.

## 6. UI Design
### 6.1 Tabs
| Tab | Responsibilities |
|---|---|
| Brand Configuration | Load existing config, upload new config, show active brand |
| Knowledge Base | Upload docs, process/store them, clear brand docs, inspect indexed docs |
| Content Generation | Capture prompt inputs and display content, evaluation, and trace |

### 6.2 Brand management callbacks
- `load_brand_from_disk(brand_name)`
- `process_uploaded_brand(file_obj)`
- `_initialize_rag_helper(config, brand_name)`

`_initialize_rag_helper()` creates a brand-aware `RAGHelper` from `models.vectorization`.

### 6.3 Knowledge-base callbacks
- `upload_documents(files, brand_name)`
- `get_brand_document_stats(brand_name)`
- `clear_brand_documents(brand_name)`

### 6.4 Content generation callback
`generate_content(topic, template_name, examples_list, use_cot, brand_config)`:
- validates brand and topic inputs
- derives `brand_name` from `brand_config['name']`
- reads quality threshold from `models.content_evaluation.quality_threshold`
- builds the Microsoft Agent Framework workflow
- runs the workflow asynchronously
- extracts `ContentThreadState`
- returns content, iteration info, score info, reasoning, and serialized trace

## 7. Data Structures
### 7.1 `ContentThreadState`
The active workflow shares one mutable Pydantic state object with these fields:
- request context: `topic`, `brand`, `brand_config`
- audit trail: `messages`
- generation controls: `template`, `examples`, `use_cot`
- outputs: `content`, `critique`
- planning/research artifacts: `planning_decision`, `research_result`
- loop controls: `iteration_count`, `max_iterations`, `quality_threshold`, `meets_quality_threshold`
- metadata: `generation_metadata`, `evaluation_metadata`
- optional `pattern`

### 7.2 Planning models
The workflow uses structured planning/result models from `models/planning_models.py`, including:
- `PlanningInput`
- `PlanningDecision`
- `ResearchResult`
- `EvaluationDecision`
- `WritingPlan`

## 8. RAG Design
### 8.1 Document loading
`DocumentLoader` loads files into `RawDocument` objects with:
- `content`
- `metadata`
- `source`

### 8.2 Chunking
`RAGHelper`:
- tokenizes using `tiktoken`
- chunks documents when token count exceeds `chunk_threshold`
- uses `chunk_size` and `chunk_overlap`
- creates one embedding per chunk

### 8.3 Storage
`VectorStore` wraps ChromaDB persistent storage.

Current public storage design:
- persist directory: `data/chroma_db`
- collection: `marketing_content`
- similarity metric: cosine
- brand isolation: metadata filtering via `where={"brand": brand}`

### 8.4 Query behavior
`VectorStore.query()`:
- queries the collection with a single query embedding
- optionally applies metadata and document filters
- optionally applies a post-query `max_distance` filter
- returns normalized flat lists via `QueryResult`

## 9. Prompt Design
### 9.1 Template registry
The public implementation exposes these template families:
- LinkedIn short post (zero-shot / few-shot)
- LinkedIn long post (zero-shot / few-shot)
- Blog post
- Newsletter
- Facebook post (zero-shot / few-shot)

### 9.2 Prompt assembly responsibilities
`PromptBuilder`:
- formats brand guidelines from config
- optionally retrieves RAG context
- optionally retrieves web search context
- optionally appends chain-of-thought scaffolding
- selects formatting requirements from template family
- renders the final template

### 9.3 Deterministic vs agentic prompt building
- `build_user_message(...)`: may call RAG/search internally
- `build_generation_prompt(...)`: expects pre-fetched tool contexts from orchestration

## 10. Generation Design
### 10.1 `ContentGenerator`
`ContentGenerator` is reusable across deterministic and agentic paths.

Key methods:
- `generate(...)`: self-contained prompt building path
- `generate_from_context(...)`: orchestration-friendly path using provided tool contexts
- `generate_batch(...)`: convenience wrapper

### 10.2 Pattern handling
The generator supports:
- `single_pass`
- `reflection`
- `evaluator_optimizer`

However, in the active Microsoft Agent Framework path, `ContentGenerationAgent.run()` forces `pattern = "single_pass"` for each pass and relies on the outer workflow loop for retries.

### 10.3 Regeneration behavior
When `iteration_count > 0` and the previous evaluation did not meet threshold, `ContentGenerationAgent` replaces the normal generation system message with the `content_optimization.system_message`.

## 11. Evaluation Design
### 11.1 Structured critique
`Critique` is a Pydantic schema with:
- `brand_voice`
- `structure`
- `accuracy`
- `violations`
- `reasoning`
- weighted `average_score`

### 11.2 Evaluation patterns
`ContentEvaluator.evaluate_content()` supports:
- `reflection`
- `evaluator_optimizer`

### 11.3 Rubric generation
For `evaluator_optimizer`, `_generate_rubric()` builds a rubric from:
- brand positioning and voice
- banned terms
- content generation rules
- factual accuracy rules
- formatting requirements selected by content type

### 11.4 Workflow usage
`ContentEvaluationAgent.run()`:
- reads evaluator settings from `brand_config['models']['content_evaluation']`
- calls `ContentEvaluator.evaluate_content()`
- calculates threshold satisfaction
- returns critique, metadata, and `meets_quality_threshold`

### 11.5 Important implementation note
Known bug: the agent passes `brand_config=evaluator_config` into `ContentEvaluator.evaluate_content()` instead of the full brand config. As implemented, rubric generation depends on evaluator config shape rather than the full YAML schema in the active path.

## 12. LLM and Search Infrastructure
### 12.1 `LLMClient`
Responsibilities:
- initialize provider clients
- make completion calls
- make embedding calls
- log API usage
- expose structured output handling
- provide retry/backoff behavior

### 12.2 Providers used in the public code
- OpenRouter for completion in the workflow builder
- OpenRouter for both completion and embeddings in app startup state
- Azure provider for embeddings inside `build_content_generation_workflow()`

This creates a provider split between ingestion-time and workflow-time embeddings.

### 12.3 Search integration
`TavilySearchClient` supports external search, and `create_tavily_search_tool()` adapts it into a shared tool callable.

## 13. Tool Design
### 13.1 `rag_search`
Produced by `create_rag_search_tool(...)`.

Input:
- `query`
- `brand`

Behavior:
- embeds query
- retrieves similar chunks from ChromaDB with brand filter
- returns summarized result payload plus raw results

### 13.2 `web_search`
Produced by `create_tavily_search_tool(...)`.

Behavior:
- optionally optimizes the query with an LLM
- calls Tavily
- filters/normalizes result payload
- returns a `sources` list used by the research executor

### 13.3 Tool invocation model
In the active Microsoft Agent Framework workflow, tools are **not** invoked through dynamic LLM tool-calling. The planner chooses tool names, and `ResearchExecutor.run()` invokes the selected tools deterministically.

## 14. Workflow Design
### 14.1 Builder
`build_content_generation_workflow(brand)` performs all runtime assembly:
- load config
- initialize vector store
- initialize completion and embedding clients
- initialize RAG helper, search client, prompt builder, evaluator, generator
- create tool callables
- create domain agents and executor adapters
- wire the workflow graph

### 14.2 Executors
| Executor | Purpose |
|---|---|
| `StartExecutor` | Seeds `ContentThreadState` from the input message |
| `ContentPlanningExecutor` | Produces route and selected tools |
| `ResearchExecutor` | Runs tool calls and stores `ResearchResult` |
| `ContentGenerationExecutor` | Produces draft content and generation metadata |
| `ContentEvaluationExecutor` | Produces critique and decides to yield or loop |
| `FinalStateExecutor` | Yields final state as workflow output |

### 14.3 Graph topology
`Start -> Planning`

`Planning -> Research` when route is `research`

`Planning -> Generation` when route is `write`

`Planning -> FinalState` as safety fallback for unexpected route

`Research -> Planning`

`Generation -> Evaluation`

`Evaluation -> yield_output` when threshold met or retry limit reached

`Evaluation -> Generation` when regeneration is needed

### 14.4 Planner behavior
`ContentPlanningAgent` has two phases:
- initial planning via LLM structured output
- post-research routing which currently always returns `write` with adjusted confidence

### 14.5 Research behavior
`ResearchExecutor.run()`:
- executes `rag_search` if requested
- executes `web_search` if requested
- builds `evidence` and serialized `tool_contexts`
- returns `ResearchResult`

### 14.6 Generation behavior
`ContentGenerationAgent.run()`:
- applies optimization system prompt on regeneration turns
- forces single-pass pattern
- calls `ContentGenerator.generate_from_context()`
- returns content and metadata

### 14.7 Evaluation behavior
`content_evaluation_node()`:
- appends evaluation system and payload messages to thread audit trail
- sanitizes previous messages for the evaluator
- stores critique and evaluation metadata
- increments iteration count

`ContentEvaluationExecutor.handle()`:
- yields workflow output if done
- otherwise sends a regeneration message

## 15. Sequence Flows
### 15.1 Sequence A: load brand
1. User selects config in Gradio.
2. `load_brand_from_disk()` loads YAML.
3. `_validate_brand_config()` checks required fields.
4. `_initialize_rag_helper()` instantiates the brand-specific `RAGHelper`.
5. Brand state is stored in Gradio state variables.

### 15.2 Sequence B: ingest documents
1. User uploads files.
2. `upload_documents()` reads each file with `DocumentLoader.load_text_file()`.
3. `RAGHelper.prepare_raw_document()` chunks and embeds content.
4. `VectorStore.add_documents()` stores chunks in `marketing_content`.
5. UI refreshes brand-level stats from Chroma metadata.

### 15.3 Sequence C: generate content
1. User submits topic/template/options.
2. `generate_content()` builds the workflow and input message.
3. `StartExecutor` creates `ContentThreadState`.
4. `ContentPlanningExecutor` invokes the planner.
5. Optional research executes and loops back.
6. `ContentGenerationExecutor` writes draft content.
7. `ContentEvaluationExecutor` evaluates the draft.
8. Workflow yields final thread state or loops for another draft.
9. UI renders content, scores, critique, and trace.

## 16. Persistence Model
| Artifact | Location | Purpose |
|---|---|---|
| Brand configs | `configs/*.yaml` | Runtime behavior definition |
| Vector DB | `data/chroma_db/` | Persistent knowledge base |
| Cost log | `data/api_calls.csv` | Cost and latency tracking |
| Past post corpus | `data/past_posts/` | Source material for ingestion/testing |
| Reports | `reports/*.md` | Design history and supporting docs |

## 17. Known Implementation-Specific Constraints
1. Public code documents and diagrams include private-production concepts not implemented here.
2. The public implementation uses ChromaDB rather than PostgreSQL + pgvector.
3. The active path lacks public HITL approval or publishing steps.
4. Brand isolation is metadata-based, not physically separated per collection/table.
5. `generate_content()` does not pass a `pattern` input, so `StartExecutor` defaults thread pattern to `single_pass`.
6. Known bug: `ContentEvaluationAgent.run()` currently uses evaluator config where full brand config would be expected for rubric generation.
7. Known bug: `generate_content()` contains duplicate `except Exception` blocks; the second block is unreachable.
8. Embedding provider configuration differs between app initialization and workflow construction.

## 18. Alignment Guidance
When reconciling this LLD with `README.md`, `DECISIONS.md`, and architecture diagrams:
- treat this LLD as the source of truth for the **current public runnable code**
- treat later Azure/HITL/governance material as documentation of a broader or later private production design
- interpret Decision 4 (`PostgreSQL + pgvector`) as production-direction documentation, not as the storage technology used by the current public code path
- interpret the current effective retrieval threshold from `configs/*.yaml` (`0.50`) rather than the earlier `0.60` value recorded in Decision 5
- note that only rendered PNG architecture diagrams are present in `architecture/`; the Draw.io source file is not in this checkout

## 19. Conclusion
The public `marketing-team` implementation is a modular local reference system with:
- config-driven multi-brand setup
- persisted local RAG
- reusable prompt/generation/evaluation services
- Microsoft Agent Framework orchestration
- deterministic research routing and bounded regeneration

Its low-level design is strong on modularity and experimentation, while governance-heavy production features remain outside the public code path.
