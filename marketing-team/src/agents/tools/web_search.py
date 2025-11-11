"""Tavily web-search tool factory for agent flows.

This module provides the ``create_tavily_search_tool`` factory which returns a
LangChain-compatible ``@tool`` callable wrapping ``TavilySearchClient``.
The tool optionally shortens long queries using an LLM, executes a Tavily
search, and returns a compact, metadata-rich dict for prompt injection or
downstream consumption.

Public API
    create_tavily_search_tool(search_client, llm_client, ...) -> Callable

Notes
    - Encapsulates query optimization and Tavily invocation behind a simple
      tool interface.
    - Returns structured metadata (original/optimized query, sources, counts)
      rather than raw client responses to keep agent prompts stable.
"""

from typing import Dict, Any, Callable
from langchain_core.tools import tool
import logging

from src.search.tavily_client import TavilySearchClient
from src.utils.llm_client import LLMClient
from src.agents.tools.formatters import format_search_results_for_llm

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 400

def create_tavily_search_tool(
        search_client: TavilySearchClient,
        llm_client: LLMClient,
        model: str = "gpt-4o-mini",
        temperature: float = 0.5,
        max_tokens: int = 100, 
        search_depth: str = "advanced",
        max_results: int = 5,
        search_type: str = "general",
        name: str = "web_search") -> Callable:
    """Create a Tavily-powered search tool for LangChain/LangGraph.

    The returned callable is decorated with `@tool` and is intended to be
    registered with an agent or invoked directly from node code. When a query
    exceeds `MAX_QUERY_LENGTH`, the factory uses the provided `llm_client` to
    compress/optimize it before calling the Tavily API.

    Args:
        search_client: Initialized Tavily client used to run searches.
        llm_client: LLM client used to optimize long queries (optional).
        model: LLM model used for query optimization when needed.
        temperature: Temperature for LLM optimization step.
        max_tokens: Max tokens for the optimization response.
        search_depth: Search depth hint passed to Tavily ("basic" | "advanced").
        max_results: Number of results to request from Tavily.
        search_type: Domain/type filter passed to Tavily (e.g. "general").
        name: Tool name to expose to the LLM.

    Returns:
        A callable `tavily_search(query: str) -> Dict[str, Any]` decorated with
        `@tool` that runs the end-to-end optimized search and returns a
        standardized result dict.
    """

    @tool
    def tavily_search(query: str) -> Dict[str, Any]:
        """Run an optimized Tavily search and return structured metadata.

        Behavior summary:
                - If the input query exceeds ``MAX_QUERY_LENGTH``, the tool asks the
          `llm_client` to produce a shorter, focused search query and uses that
          for the actual Tavily call.
        - The tool always returns a dict containing the original `query`, the
          `optimized_query` actually sent to Tavily, a short `summary`, and a
          `sources` list of snippet/URL/score dicts.

        Args:
            query: Free-text search query. May exceed ``MAX_QUERY_LENGTH`` — the
                tool will optimize it automatically.

        Returns:
            A dict with the following keys:
            - `query` (str): the original query supplied by the caller
            - `optimized_query` (str): the query actually executed against
                Tavily (may equal `query` when short)
            - `summary` (str): brief text excerpt useful for quick inspection
            - `sources` (List[Dict]): list of {rank, snippet, url, score}
            - `source_count` (int): number of returned sources
            - `error` (str, optional): present when the tool failed

        Errors are logged and returned in the `error` field instead of
        raising to allow graceful handling inside agent flows.
        """

        try:
            # Step 1: Optimize query if too long
            optimized_query = query

            if len(query) > MAX_QUERY_LENGTH:
                logger.info(
                    f"Query too long ({len(query)} chars), optimizing...")

                # Use LLM to compress query (reuse Week 3 logic)
                messages = [{
                    "role":
                    "user",
                    "content":
                    f"""Convert this detailed topic into a focused search query (max {MAX_QUERY_LENGTH} chars).                 
                                    Remove personal narrative, keep key facts/claims to verify.

                                    Topic: {query}

                                    Search query:"""
                }]

                # Ask LLM to compress the query to fit within the cap
                result = llm_client.get_completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Truncate at word boundary if still too long
                optimized_query = result.content[:MAX_QUERY_LENGTH]
                if len(optimized_query) == MAX_QUERY_LENGTH:
                    optimized_query = optimized_query.rsplit(' ', 1)[0]

                logger.info(
                    f"Optimized query ({len(optimized_query)} chars): {optimized_query}"
                )

            # Step 2: Search with optimized query
            search_results = search_client.search(
                query=optimized_query,  # Use optimized query
                search_depth=search_depth,
                max_results=max_results,
                search_type=search_type)

            # Step 3: Format results for LLM consumption
            return format_search_results_for_llm(
                search_results=search_results,
                query=query,
                optimized_query=optimized_query if optimized_query != query else None,
                max_content_length=2000  # Only truncate if excessive
            )             
            # Note: The line below would be unreachable. Kept intentionally
            # to avoid altering code structure per "no code changes" rule.
            # return formatted_results

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Tavily search failed: {error_msg}", exc_info=True)

            return {
                "query": query,
                "summary": f"Search failed: {error_msg[:100]}",
                "sources": [],
                "error": error_msg
            }

    # Expose a stable tool name (as seen by the LLM/tool-calling runtime)
    tavily_search.name = name
    return tavily_search
