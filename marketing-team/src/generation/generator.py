"""
Content Generator
Orchestrates content generation using LLM, RAG, and optional search
"""

from typing import Dict, Optional, List
from datetime import datetime
from utils.llm_client import LLMClient
from rag.vector_store import VectorStore
from rag.rag_helper import RAGHelper
from search.tavily_client import TavilySearchClient
from prompts.prompt_builder import PromptBuilder
from prompts.templates import (
    LINKEDIN_POST_ZERO_SHOT,
    LINKEDIN_POST_FEW_SHOT,
    LINKEDIN_ARTICLE,
    FACEBOOK_POST_ZERO_SHOT,
    FACEBOOK_POST_FEW_SHOT
)


class ContentGenerator:
    """Generate content using LLM with optional RAG and optional search"""

    # Template mapping
    TEMPLATE_MAP = {
        "linkedin_post": LINKEDIN_POST_ZERO_SHOT,
        "linkedin_post_few_shot": LINKEDIN_POST_FEW_SHOT,
        "linkedin_article": LINKEDIN_ARTICLE,
        "facebook_post": FACEBOOK_POST_ZERO_SHOT,
        "facebook_post_few_shot": FACEBOOK_POST_FEW_SHOT
    }

    def __init__(self,
                 llm_client: LLMClient,
                 vector_store: VectorStore,
                 rag_helper: RAGHelper,
                 brand_config: Dict,
                 collection_name: str = "marketing_content",
                 search_client: Optional[TavilySearchClient] = None):
        """
        Initialize ContentGenerator
        
        Args:
            llm_client: LLMClient instance for LLM calls
            vector_store: VectorStore instance for RAG retrieval
            rag_helper: RAGHelper instance for embedding generation
            brand_config: Brand configuration dict (from YAML)
            collection_name: Vector store collection name
            search_client: Optional TavilySearchClient for web search
        """
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.rag_helper = rag_helper
        self.brand_config = brand_config
        self.collection_name = collection_name
        self.search_client = search_client

        # Initialize prompt builder
        self.prompt_builder = PromptBuilder(vector_store=vector_store,
                                            rag_helper=rag_helper,
                                            search_client=search_client)

    def generate(self,
                 topic: str,
                 content_type: str = "post",
                 include_rag: bool = True,
                 include_search: bool = False,
                 search_depth: str = 'basic',
                 search_type: str = 'general',
                 rag_max_distance: Optional[float] = 0.50,
                 model: str = "gpt-4o-mini",
                 system_message: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 1500,
                 num_examples: int = 0,
                 ) -> Dict:
        """
        Generate content for given topic
        
        Args:
            topic: What to write about
            content_type: Type of content ("post", "article")
            include_rag: Whether to include RAG context
            include_search: Whether to include web search results
            model: LLM model to use
            temperature: LLM temperature (0.0-1.0)
            max_tokens: Maximum output tokens
            num_examples: Number of examples for few-shot (0 = zero-shot)
        
        Returns:
            Dict with keys:
                - content: Generated text
                - metadata: Dict with cost, latency, tokens, prompt, etc.
        """
        # Select template
        template_key = content_type
        if num_examples > 0 and content_type == "post":
            template_key = "post_few_shot"

        template = self.TEMPLATE_MAP.get(template_key)
        if not template:
            raise ValueError(
                f"Unknown content_type: {content_type}. "
                f"Valid options: {list(self.TEMPLATE_MAP.keys())}")

        # Build user prompt
        user_message = self.prompt_builder.build_user_message(
            collection_name=self.collection_name,
            template=template,
            topic=topic,
            brand=self.brand_config['name'].lower(),
            brand_config=self.brand_config,
            include_rag=include_rag,
            max_distance=rag_max_distance,
            include_search=include_search,
            search_depth=search_depth,
            search_type=search_type,
            llm_client=self.llm_client,
            num_examples=num_examples)

        # Build messages
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": user_message})

        # Call LLM
        result = self.llm_client.get_completion(model=model,
                                                messages=messages,
                                                temperature=temperature,
                                                max_tokens=max_tokens)

        # Package result
        return {
            "content": result.content,
            "metadata": {
                "topic": topic,
                "content_type": content_type,
                "brand": self.brand_config['name'],
                "model": result.model,
                "cost": result.cost,
                "latency": result.latency,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "include_rag": include_rag,
                "include_search": include_search,
                "num_examples": num_examples,
                "temperature": temperature,
                "prompt_used": user_message,  # Full prompt for debugging
                "timestamp": datetime.now().isoformat()
            }
        }

    def generate_batch(self,
                       topics: List[str],
                       content_type: str = "post",
                       include_rag: bool = True,
                       include_search: bool = False,
                       rag_max_distance: Optional[float] = 0.50,
                       model: str = "gpt-4o-mini",
                       temperature: float = 0.7,
                       max_tokens: int = 1500,
                       num_examples: int = 0) -> List[Dict]:
        """
        Generate content for multiple topics
        
        Args:
            topics: List of topics to write about
            content_type: Type of content (same for all)
            include_rag: Whether to include RAG context
            include_search: Whether to include web search
            model: LLM model to use
            temperature: LLM temperature
            max_tokens: Maximum output tokens
            num_examples: Number of examples for few-shot
        
        Returns:
            List of result dicts (same structure as generate())
        """
        results = []

        for topic in topics:
            result = self.generate(topic=topic,
                                   content_type=content_type,
                                   include_rag=include_rag,
                                   include_search=include_search,
                                   rag_max_distance=rag_max_distance,
                                   model=model,
                                   temperature=temperature,
                                   max_tokens=max_tokens,
                                   num_examples=num_examples)
            results.append(result)

        return results

    def get_total_cost(self, results: List[Dict]) -> float:
        """
        Calculate total cost for batch of results
        
        Args:
            results: List of result dicts from generate() or generate_batch()
        
        Returns:
            Total cost in EUR
        """
        return sum(r['metadata']['cost'] for r in results)

    def get_average_latency(self, results: List[Dict]) -> float:
        """
        Calculate average latency for batch of results
        
        Args:
            results: List of result dicts from generate() or generate_batch()
        
        Returns:
            Average latency in seconds
        """
        if not results:
            return 0.0
        return sum(r['metadata']['latency'] for r in results) / len(results)

    def get_total_tokens(self, results: List[Dict]) -> Dict[str, int]:
        """
        Calculate total tokens for batch of results
        
        Args:
            results: List of result dicts from generate() or generate_batch()
        
        Returns:
            Dict with keys: input_tokens, output_tokens, total_tokens
        """
        input_tokens = sum(r['metadata']['input_tokens'] for r in results)
        output_tokens = sum(r['metadata']['output_tokens'] for r in results)

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
