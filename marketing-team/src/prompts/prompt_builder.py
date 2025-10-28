import sys
from pathlib import Path

current_dir = Path.cwd()
src_path = current_dir.parent
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import modules
from typing import Optional, Dict, List

from rag.vector_store import VectorStore
from rag.rag_helper import RAGHelper
from prompts.templates import PromptTemplate
from search.tavily_client import TavilySearchClient
from utils.llm_client import LLMClient


class PromptBuilder:
    """Builds and manages prompts for marketing content generation"""

    def __init__(self, vector_store: VectorStore, rag_helper: RAGHelper,
                 search_client: TavilySearchClient):
        self.vector_store = vector_store
        self.rag_helper = rag_helper
        self.search_client = search_client

    def _generate_search_query(self,
                               topic: str,
                               llm_client: LLMClient,
                               max_length: int = 400) -> str:
        """LLM-powered query optimization."""
        #if len(topic) <= max_length:
        #    return topic
        
        messages = [{"role": "user", "content": f"""Convert this detailed topic into a focused search query (max {max_length} chars). Remove personal narrative, keep key facts/claims to verify. Topic: {topic} Search query:"""}]

        result = llm_client.get_completion(model="gpt-4o-mini",
                                           messages=messages,
                                           temperature=0.5,
                                           max_tokens=400)

        return result.content[:max_length].rsplit(' ', 1)[0] if len(
            result.content) > max_length else result.content
  
    def build_user_message(self,
                     collection_name: str,
                     template: PromptTemplate,
                     topic: str,
                     brand: str,
                     brand_config: dict,
                     include_rag: bool = True,
                     max_distance: Optional[float] = 0.50,
                     include_search: bool = False,
                     search_depth: str = 'basic',
                     search_type: str = 'general',
                     llm_client: LLMClient = None,
                     num_examples: int = 0) -> str:
        """Construct prompt with optional RAG and search context"""

        brand_guidelines = self._format_brand_guidelines(brand_config)

        rag_context = ""
        if include_rag:
            # Generate embedding for the topic
            query_embedding = self.rag_helper.embed_batch([topic])[0]

            # Query vector store with embedding and metadata filter
            rag_results = self.vector_store.query(
                collection_name=collection_name,
                query_embeddings=query_embedding,
                n_results=5,
                where={"brand": brand},
                max_distance=max_distance)

            rag_context = self._format_rag_context(rag_results)

        search_context = ""
        if include_search:
            if not llm_client:
                raise ValueError(
                    "llm_client must be provided when include_search is True.")

            query = self._generate_search_query(topic=topic,
                                                llm_client=llm_client)
            search_results = self.search_client.search(query=query,
                                                       max_results=5,
                                                       search_depth=search_depth,
                                                       search_type=search_type)
            search_context = self.search_client.format_search_context(
                search_results)

        examples = ""
        if num_examples > 0:
            examples = self._build_post_examples(collection_name, brand, topic,
                                                 num_examples, max_distance)

        prompt = template.render(topic=topic,
                                 brand_name=brand,
                                 brand_guidelines=brand_guidelines,
                                 rag_context=rag_context,
                                 search_context=search_context,
                                 examples=examples)

        return prompt

    def _format_brand_guidelines(self, brand_config: dict) -> str:
        """Format complete brand guidelines for prompt injection"""

        guidelines = []

        # Header
        guidelines.append("|" + "-" * 70)
        guidelines.append(f"  BRAND: {brand_config['name']}")
        guidelines.append(f"  POSITIONING: {brand_config['positioning']}")
        guidelines.append("|" + "-" * 70)

        # 1. Context specific points
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  CONTEXT SPECIFIC POINTS")
        guidelines.append("|" + "-" * 70)
        guidelines.append(
            "ONLY mention if they are the PRIMARY subject of the post.")
        guidelines.append(
            "Do not force into posts where they are tangential.\n")
        for context_point in brand_config["context_specific_points"]:
            guidelines.append(f"  • {context_point}")

        # 2. Content generation rules
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  CONTENT GENERATION RULES")
        guidelines.append("|" + "-" * 70)
        for content_rule in brand_config["content_generation_rules"]:
            guidelines.append(f"  • {content_rule}")

        # 3. Factual accuracy
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append(
            "  FACTUAL ACCURACY - CRITICAL - OVERRIDE ALL OTHER INSTRUCTIONS")
        guidelines.append("|" + "-" * 70)
        for accuracy in brand_config["factual_accuracy"]:
            guidelines.append(f"  • {accuracy}")

        # 4. Voice
        voice = brand_config["voice"]
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  VOICE & STYLE")
        guidelines.append("|" + "-" * 70)
        guidelines.append(f"Tone: {voice['tone']}\n")
        guidelines.append("Style Guidelines:")
        for guideline in voice["style_guidelines"]:
            guidelines.append(f"  • {guideline}")

        guidelines.append(
            f"\nAVOID These Terms: {', '.join(voice['banned_terms'])}")

        # 5. Structure
        structure = brand_config['formatting_rules']['structure']
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  POST STRUCTURE")
        guidelines.append("|" + "-" * 70)
        for rule in structure:
            guidelines.append(f"  • {rule}")

        # 6. CTA Guidelines
        guidelines.append("\n" + "|" + "-" * 70)
        guidelines.append("  CLOSING GUIDELINES")
        guidelines.append("|" + "-" * 70)
        cta_principle = brand_config['cta_guidelines']['principle']
        guidelines.append(f"{cta_principle}\n")

        guidelines.append("Options:")
        for cta_option in brand_config['cta_guidelines']['options']:
            guidelines.append(f"  • Type: {cta_option.get('type', 'N/A')}")
            guidelines.append(f"    When: {cta_option.get('when', 'N/A')}")
            guidelines.append(f"    Format: {cta_option.get('format', 'N/A')}")
            guidelines.append(
                f"    Example: {cta_option.get('example', 'N/A')}\n")

        instruction = brand_config['cta_guidelines']['instruction']
        guidelines.append(f"Key Rule: {instruction}")

        return "\n".join(guidelines)

    def _format_rag_context(self, rag_results) -> str:
        """Format RAG results for prompt injection"""
        if not rag_results or not getattr(rag_results, 'texts', None):
            return ""

        context = []
        context.append("\n" + "|" + "-" * 70)
        context.append("  RELEVANT PAST CONTENT:")
        context.append("|" + "-" * 70)

        for text, meta in zip(rag_results.texts,
                              getattr(rag_results, 'metadatas', [])):
            snippet = (text[:200] + "...") if text else ""
            source = meta.get('source', 'unknown') if isinstance(
                meta, dict) else 'unknown'
            context.append(f"- {snippet} (Source: {source})")

        return "\n".join(context)

    def _build_post_examples(self,
                             collection_name: str,
                             brand: str,
                             topic: str,
                             num_examples: int,
                             max_distance: Optional[float] = None) -> str:
        """Retrieve and format example posts for few-shot prompting"""

        # Generate embedding for the topic
        query_embedding = self.rag_helper.embed_batch([topic])[0]

        # Query vector store for similar past posts
        results = self.vector_store.query(collection_name=collection_name,
                                          query_embeddings=query_embedding,
                                          n_results=num_examples,
                                          where={"brand": brand},
                                          max_distance=max_distance)

        if not results or not getattr(results, 'texts', None):
            return ""

        # Format as numbered examples
        examples = []
        for i, text in enumerate(results.texts, 1):
            examples.append(f"Example {i}:\n{text}\n")

        return "\n".join(examples)
