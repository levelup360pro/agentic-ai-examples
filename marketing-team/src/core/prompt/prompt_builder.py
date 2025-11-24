"""Prompt construction helpers for deterministic and agentic content generation.

Builds user messages by injecting brand guidelines and optional tool context
for RAG and web search. Deterministic path can call tools internally; agentic
path expects pre-fetched tool contexts. No model calls are performed here.

Public API
        PromptBuilder: Main class with `build_user_message` and `build_generation_prompt`.

Notes
        - Keep prompt building pure: external I/O or model calls are intentionally
            avoided so the class can be unit-tested easily.
        - The builder relies on `RAGHelper` and `VectorStore` for context
            generation when required but accepts pre-fetched contexts for agentic flows.
"""
from typing import Optional, Dict, List
from src.core.rag.vector_store import VectorStore
from src.core.rag.rag_helper import RAGHelper
from src.core.prompt.templates import PromptTemplate
from src.infrastructure.search.tavily_client import TavilySearchClient
from src.infrastructure.llm.llm_client import LLMClient


class PromptBuilder:
    """Construct user prompts for deterministic and agentic generation flows."""

    def __init__(
        self,
        vector_store: VectorStore,
        rag_helper: RAGHelper,
        search_client: Optional[TavilySearchClient] = None,
    ):
        """Initialize dependencies (framework-agnostic and brand-agnostic)."""
        self.vector_store = vector_store
        self.rag_helper = rag_helper
        self.search_client = search_client

    # ---------------------------
    # Deterministic path (can call tools internally)
    # ---------------------------
    def build_user_message(
        self,
        *,
        collection_name: str,
        template: PromptTemplate,
        topic: str,
        brand: str,
        brand_config: dict,
        include_rag: bool = False,
        max_distance: Optional[float] = None,
        rag_max_results: Optional[int] = None,
        include_search: bool = False,
        search_depth: Optional[str] = None,
        search_type: Optional[str] = None,
        search_max_results: Optional[int] = None,
        llm_client: Optional[LLMClient] = None,
        examples: Optional[List[str]] = None,
        use_cot: bool = False,
    ) -> str:
        """Construct prompt with optional RAG and search context (deterministic).

        Args:
            collection_name: Vector collection for retrieving past content.
            template: Prompt template to render.
            topic: Topic to generate content about.
            brand: Brand key; used for filtering and guideline headers.
            brand_config: Full brand configuration dict.
            include_rag: Include internal RAG lookup when True.
            max_distance: Max vector distance for RAG results.
            rag_max_results: Max number of RAG examples to include.
            include_search: Include Tavily search when True.
            search_depth: Tavily search depth (basic/advanced).
            search_type: Tavily type (general/news/research/code/discussion).
            search_max_results: Max number of web sources to include.
            llm_client: Client to optimize query when include_search=True.
            examples: Optional few-shot examples.
            use_cot: Whether to add CoT scaffolding instructions.
        """
        brand_key = (brand or "").lower()
        brand_guidelines = self._format_brand_guidelines(brand_config)

        # RAG context (internal tool call)
        rag_context = ""
        if include_rag:
            query_embedding = self.rag_helper.embed_query(text=topic)
            rag_cfg = brand_config.get("retrieval", {}).get("rag", {})
            final_max_distance = max_distance if max_distance is not None else rag_cfg.get("max_distance", 0.50)
            final_n_results = rag_max_results if rag_max_results is not None else rag_cfg.get("max_results", 5)

            rag_results = self.vector_store.query(
                collection_name=collection_name,
                query_embeddings=query_embedding,
                n_results=final_n_results,
                where={"brand": brand_key},
                max_distance=final_max_distance,
            )
            rag_context = self._format_rag_context(rag_results)

        # Search context (internal tool call)
        search_context = ""
        if include_search:
            if not llm_client:
                raise ValueError("llm_client must be provided when include_search=True.")
            if not self.search_client:
                raise ValueError("PromptBuilder.search_client is not set but include_search=True.")

            query = self._generate_search_query(
                topic=topic,
                llm_client=llm_client,
                brand_config=brand_config,
            )

            search_cfg = brand_config.get("retrieval", {}).get("search", {})
            final_max_results = search_max_results if search_max_results is not None else search_cfg.get("max_results", 5)
            final_depth = search_depth or search_cfg.get("search_depth", "advanced")
            final_type = search_type or search_cfg.get("search_type", "general")

            search_results = self.search_client.search(
                query=query,
                max_results=final_max_results,
                search_depth=final_depth,
                search_type=final_type,
            )
            search_context = self.search_client.format_search_context(search_results)

        # Optional CoT scaffold (reasoning instruction for the model)
        final_topic = topic
        if use_cot:
            final_topic = topic + """
                \nBefore generating the final content, think through:
                1. What specific problem, failure, or surprising result will hook readers immediately?
                2. How can I create tension or curiosity in the opening (show what didn't work, build contrast)?
                3. What concrete numbers, metrics, or evidence prove the main point?
                4. How does this insight apply beyond the immediate topic (what's the transferable pattern)?

                After thinking, generate the final content. Do not include this reasoning in your output.
                """

        # Requirements by template family
        requirements = self._select_requirements(template, brand_config)

        # Final prompt assembly
        prompt = template.render(
            topic=final_topic,
            brand_name=brand_key,
            brand_guidelines=brand_guidelines,
            rag_context=rag_context,
            search_context=search_context,
            examples=examples,
            requirements=requirements,
        )
        return prompt

    # ---------------------------
    # Agentic path (no internal tool calls)
    # ---------------------------
    def build_generation_prompt(
        self,
        *,
        template: PromptTemplate,
        topic: str,
        brand: str,
        brand_config: dict,
        tool_contexts: Optional[Dict[str, str]] = None,
        examples: Optional[List[str]] = None,
        use_cot: bool = False,
    ) -> str:
        """Build generation prompt using pre-fetched tool contexts (agentic)."""
        brand_key = (brand or "").lower()
        brand_guidelines = self._format_brand_guidelines(brand_config)

        # Extract pre-fetched contexts
        rag_context = (tool_contexts or {}).get("rag_search")
        search_context = (tool_contexts or {}).get("web_search")

        final_topic = topic
        if use_cot:
            final_topic = topic + """
                \nBefore generating the final content, think through:
                1. What specific problem, failure, or surprising result will hook readers immediately?
                2. How can I create tension or curiosity in the opening (show what didn't work, build contrast)?
                3. What concrete numbers, metrics, or evidence prove the main point?
                4. How does this insight apply beyond the immediate topic (what's the transferable pattern)?

                After thinking, generate the final content. Do not include this reasoning in your output.
                """

        requirements = self._select_requirements(template, brand_config)

        prompt = template.render(
            topic=final_topic,
            brand_name=brand_key,
            brand_guidelines=brand_guidelines,
            rag_context=rag_context,
            search_context=search_context,
            examples=examples,
            requirements=requirements,
        )
        return prompt

    # ---------------------------
    # Internal helpers
    # ---------------------------
    def _generate_search_query(self, *, topic: str, llm_client: LLMClient, brand_config: dict) -> str:
        """Optimize a web search query with an LLM (max 400 chars).

        Reads settings from brand_config['models']['query_optimization'] first,
        falling back to 'search_optimization' if missing.
        """
        TAVILY_MAX_QUERY_LENGTH = 400

        models_cfg = brand_config.get("models", {}) or {}
        query_cfg = models_cfg.get("query_optimization") or models_cfg.get("search_optimization")
        if not query_cfg:
            raise ValueError("Missing models.query_optimization (or search_optimization) in brand_config.")

        messages = [{
            "role": "user",
            "content": (
                f"Convert this detailed topic into a focused web search query (<= {TAVILY_MAX_QUERY_LENGTH} chars). "
                "Remove personal narrative, keep key facts/claims to verify.\n\n"
                f"Topic: {topic}\n\nSearch query:"
            ),
        }]

        result = llm_client.get_completion(
            model=query_cfg["model"],
            temperature=query_cfg["temperature"],
            max_tokens=query_cfg["max_tokens"],
            messages=messages,
        )

        content = result.content or ""
        if len(content) > TAVILY_MAX_QUERY_LENGTH:
            # Truncate at word boundary
            return content[:TAVILY_MAX_QUERY_LENGTH].rsplit(" ", 1)[0]
        return content

    def _select_requirements(self, template: PromptTemplate, brand_config: dict) -> List[str]:
        """Select formatting requirements based on template family name."""
        template_name = getattr(template, "name", "") or ""
        formatting_rules = brand_config.get("formatting_rules", {})
        if "LONG_POST" in template_name:
            return formatting_rules.get("long_post_requirements", []) or []
        if "BLOG_POST" in template_name:
            return formatting_rules.get("blog_post_requirements", []) or []
        if "POST" in template_name:
            return formatting_rules.get("post_requirements", []) or []
        if "NEWSLETTER" in template_name:
            return formatting_rules.get("newsletter_requirements", []) or []
        return []

    def _format_brand_guidelines(self, brand_config: dict) -> str:
        """Format brand guidelines for prompt injection."""
        guidelines: List[str] = []

        # Header
        guidelines.append("|" + "-" * 70)
        guidelines.append(f"  BRAND: {brand_config.get('name', 'Unknown')}")
        guidelines.append(f"  POSITIONING: {brand_config.get('positioning', '')}")
        guidelines.append("|" + "-" * 70)

        # Context specific points
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  CONTEXT SPECIFIC POINTS")
        guidelines.append("|" + "-" * 70)
        guidelines.append("ONLY mention if they are the PRIMARY subject—never as mandatory mentions.")
        guidelines.append("Do not force into posts where they are tangential.\n")
        for cp in brand_config.get("context_specific_points", []) or []:
            guidelines.append(f"  • {cp}")

        # Content generation rules
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  CONTENT GENERATION RULES")
        guidelines.append("|" + "-" * 70)
        for rule in brand_config.get("content_generation_rules", []) or []:
            guidelines.append(f"  • {rule}")

        # Factual accuracy
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  FACTUAL ACCURACY - CRITICAL - OVERRIDE ALL OTHER INSTRUCTIONS")
        guidelines.append("|" + "-" * 70)
        for fa in brand_config.get("factual_accuracy", []) or []:
            guidelines.append(f"  • {fa}")

        # Voice & style
        voice = brand_config.get("voice", {}) or {}
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  VOICE & STYLE")
        guidelines.append("|" + "-" * 70)
        if voice.get("tone"):
            guidelines.append(f"Tone: {voice['tone']}\n")
        style = voice.get("style_guidelines", []) or []
        if style:
            guidelines.append("Style Guidelines:")
            for sg in style:
                guidelines.append(f"  • {sg}")
        banned = voice.get("banned_terms", []) or []
        if banned:
            guidelines.append(f"\nAVOID These Terms: {', '.join(banned)}")

        # CTA guidelines
        cta = brand_config.get("cta_guidelines", {}) or {}
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  CLOSING GUIDELINES")
        guidelines.append("|" + "-" * 70)
        if cta.get("principle"):
            guidelines.append(f"{cta['principle']}\n")
        options = cta.get("options", []) or []
        if options:
            guidelines.append("Options:")
            for opt in options:
                guidelines.append(f"  • Type: {opt.get('type', 'N/A')}")
                guidelines.append(f"    When: {opt.get('when', 'N/A')}")
                guidelines.append(f"    Format: {opt.get('format', 'N/A')}")
                guidelines.append(f"    Example: {opt.get('example', 'N/A')}\n")
        instruction = cta.get("instruction")
        if instruction:
            guidelines.append(f"Key Rule: {instruction}")

        return "\n".join(guidelines)

    def _format_rag_context(self, rag_results) -> str:
        """Format RAG results for prompt injection."""
        if not rag_results or not getattr(rag_results, "texts", None):
            return ""

        context: List[str] = []
        context.append("\n" + "|" + "-" * 70)
        context.append("  RELEVANT PAST CONTENT:")
        context.append("|" + "-" * 70)

        texts = rag_results.texts
        metas = getattr(rag_results, "metadatas", [])
        for text, meta in zip(texts, metas):
            snippet = (text[:200] + "...") if text else ""
            source = meta.get("source", "unknown") if isinstance(meta, dict) else "unknown"
            context.append(f"- {snippet} (Source: {source})")

        return "\n".join(context)