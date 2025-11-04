"""
Content Generator
Orchestrates content generation using LLM, RAG, and optional search
"""

from typing import Dict, Optional, List, Any
from datetime import datetime
from utils.llm_client import LLMClient
from rag.vector_store import VectorStore
from rag.rag_helper import RAGHelper
from search.tavily_client import TavilySearchClient
from prompts.prompt_builder import PromptBuilder
from prompts.templates import (
    LINKEDIN_POST_ZERO_SHOT,
    LINKEDIN_POST_FEW_SHOT,
    LINKEDIN_LONG_POST_ZERO_SHOT,
    LINKEDIN_LONG_POST_FEW_SHOT,
    BLOG_POST,
    NEWSLETTER,
    FACEBOOK_POST_ZERO_SHOT,
    FACEBOOK_POST_FEW_SHOT
)
from evaluation.evaluator import ContentEvaluator, Critique



class ContentGenerator:
    """Generate content using LLM with optional RAG and optional search"""

    # Template mapping
    TEMPLATE_MAP = {
        "linkedin_post": LINKEDIN_POST_ZERO_SHOT,
        "linkedin_post_few_shot": LINKEDIN_POST_FEW_SHOT,
        "linkedin_long_post": LINKEDIN_LONG_POST_ZERO_SHOT,
        "linkedin_long_post_few_shot": LINKEDIN_LONG_POST_FEW_SHOT,
        "blog_post": BLOG_POST,
        "newsletter": NEWSLETTER,
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

        # Initialize evaluator
        self.evaluator = ContentEvaluator(llm_client=llm_client,
                                          brand_config=brand_config)

    def generate(
            self,
            topic: str,
            content_type: str = "linkedin_post",
            include_rag: bool = True,
            include_search: bool = False,
            search_depth: str = 'basic',
            search_type: str = 'general',
            rag_max_distance: Optional[float] = 0.50,
            model: str = "gpt-4o-mini",
            system_message: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 1500,
            examples: Optional[list[str]] = None,
            use_cot: bool = False,
            pattern: str = "single_pass",  # "single_pass", "reflection", "evaluator_optimizer"
            max_iterations: int = 1,
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
            examples=examples,
            use_cot=use_cot)

        # Build messages
        messages = []
        
        
        # Build system message
        generation_system_message = "You are a professional content generator"

        if system_message:
            generation_system_message = system_message
        elif self.brand_config.get('generation_system_message'):
            banned_terms_formatted = "\n   ".join(f"- {term}" for term in self.brand_config['voice']['banned_terms'])
            # Load system message template from brand config and format with banned terms
            template: Optional[str] = self.brand_config.get("generation_system_message")
            if template:
                # use .format_map to avoid KeyError if some placeholders are missing
                generation_system_message = template.format_map({
                    "banned_terms": banned_terms_formatted
                })

        messages.append({"role": "system", "content": generation_system_message})

        if use_cot:
            cot_prompt = """\nBreak down the task into smaller steps before answering.
                Provide your reasoning process clearly, then give the final content.
            """

            messages.append({
                "role": "user",
                "content": user_message + cot_prompt
            })
        else:
            messages.append({"role": "user", "content": user_message})

        # Call LLM
        if pattern == "reflection":
            result = self._generate_with_reflection(model=model,
                                                    messages=messages,
                                                    temperature=temperature,
                                                    max_tokens=max_tokens,
                                                    max_iterations=max_iterations)
        elif pattern == "evaluator_optimizer":
            result = self._generate_with_evaluator_optimizer(
                model=model,
                messages=messages,
                content_type=content_type,
                temperature=temperature,
                max_tokens=max_tokens,
                max_iterations=max_iterations)
        else:
            result = self._generate(model=model,
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
                "system_message": system_message,
                "model": result.model,
                "cost": result.cost,
                "latency": result.latency,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "include_rag": include_rag,
                "include_search": include_search,
                "temperature": temperature,
                "prompt_used": user_message,  # Full prompt for debugging
                "timestamp": datetime.now().isoformat()
            }
        }

    def generate_batch(self,
                    topics: List[str],
                    pattern: str = "single_pass",
                    max_iterations: int = 1,
                    **generate_kwargs) -> List[Dict[str, Any]]:
        """
        Generate multiple pieces of content using specified pattern.
        
        Args:
            topics: List of topics (user input, not full prompts)
            pattern: Generation pattern (single_pass, reflection, evaluator_optimizer)
            max_iterations: Max refinement iterations (for reflection/evaluator_optimizer)
            **generate_kwargs: Additional parameters passed to generate():
                - content_type: str = "post"
                - include_rag: bool = True
                - include_search: bool = False
                - search_depth: str = 'basic'
                - search_type: str = 'general'
                - rag_max_distance: Optional[float] = 0.50
                - model: str = "gpt-4o-mini"
                - system_message: Optional[str] = None
                - temperature: float = 0.7
                - max_tokens: int = 1500
                - examples: Optional[list[str]] = None
                - use_cot: bool = False
        
        Returns:
            List of dicts with structure:
            {
                'content': str,
                'metadata': {
                    'cost': float,
                    'latency': float,
                    'iterations': int,
                    'final_critique': Critique (optional)
                }
            }
        
        Examples:
            # Basic pattern comparison (Week 3)
            results = generator.generate_batch(
                topics=["AI governance", "Azure security", ...],
                pattern="single_pass"
            )
            
            # With reflection pattern
            results = generator.generate_batch(
                topics=["AI governance", "Azure security", ...],
                pattern="reflection",
                max_iterations=3,
            )
            
            # With RAG + search enabled
            results = generator.generate_batch(
                topics=["AI governance", "Azure security", ...],
                pattern="single_pass",
                include_rag=True,
                include_search=True,
                search_depth="advanced"
            )
            
            # With custom model + CoT
            results = generator.generate_batch(
                topics=["AI governance", "Azure security", ...],
                pattern="evaluator_optimizer",
                max_iterations=3,
                model="gpt-4o",
                use_cot=True,
                temperature=0.3
            )
        """
        if isinstance(topics, str):
            topics = [topics]

        results = []
        
        for i, topic in enumerate(topics, 1):
            # logger.info(f"[{i}/{len(topics)}] Generating with {pattern} pattern...")
            
            result = self.generate(
                topic=topic,
                pattern=pattern,
                max_iterations=max_iterations,
                **generate_kwargs
            )
            
            results.append(result)
            
            # Log progress
            cost = result['metadata'].get('total_cost', result['metadata'].get('cost', 0))
            latency = result['metadata'].get('total_latency', result['metadata'].get('latency', 0))
            # logger.info(f"  ✓ Generated ({len(result['content'])} chars, ${cost:.4f}, {latency:.2f}s)")
        
        return results

    def score_content(self,
                      content: str,
                      content_type: str,
                      model: str) -> Dict[str, Any]:
        """
        Score a single piece of content using the evaluator.
        Can score content from batch generation, single generation, or external sources.
        
        Args:
        content: Content text to evaluate
        content_type: Type of content ("post", "long_post", "blog_post", "newsletter")
            
        Returns:
            Dict with structure:
            {
                'quality_scores': dict,  # {brand_voice: float, hook: float, structure: float, accuracy: float}
                'reasoning': str,        # Evaluator's reasoning
                'cost': float,           # Evaluation cost
                'latency': float         # Evaluation latency in seconds
            }
        """

        # logger.info(f"Scoring content ({len(content)} chars) with pattern: {pattern}")

        # Call evaluator
        critique, eval_metadata = self.evaluator.evaluate_content(content=content,
                                                                  content_type=content_type,
                                                                  model=model,
                                                                  pattern="evaluator_optimizer")

        result = {
            'brand_voice_score': critique.brand_voice,
            'structure_score': critique.structure,
            'accuracy_score': critique.accuracy,
            'violations': critique.violations,
            'average_score': critique.average_score,
            'reasoning': critique.reasoning,
            'cost': eval_metadata['cost'],
            'latency': eval_metadata['latency']
        }

        # logger.info(f"  ✓ Scored (${result['cost']:.4f}, {result['latency']:.2f}s)")

        return result

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

    def _generate(self, model: str, messages: List[Dict[str, str]],
                  temperature: float, max_tokens: int) -> Dict[str, any]:
        result = self.llm_client.get_completion(model=model,
                                                messages=messages,
                                                temperature=temperature,
                                                max_tokens=max_tokens)

        return result

    def _generate_with_reflection(self, model: str, messages: List[Dict[str,
                                                                        str]],
                                  temperature: float, max_tokens: int,
                                  max_iterations: int) -> Dict[str, any]:
        '''
        Generate a response with reflection and critique.
        Aggregates costs and latency from all iterations (generation + evaluation).
        '''

        history = messages.copy()  # Add system + user prompt to conversation history

        # Track aggregated costs across all iterations
        total_cost = 0.0
        total_latency = 0.0
        total_input_tokens = 0
        total_output_tokens = 0

        iterations = 0

        while iterations <= max_iterations:
            result = self.llm_client.get_completion(model=model,
                                                    messages=history,
                                                    temperature=temperature,
                                                    max_tokens=max_tokens)

            # Aggregate generation costs
            total_cost += result.cost
            total_latency += result.latency
            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens

            history.append({"role": "assistant", "content": result.content})

            iterations += 1

            if iterations > max_iterations:
                break

            # Evaluate result (with history) - returns (Critique, metadata)
            evaluation, eval_metadata = self.evaluator.evaluate_content(
                content=result.content,
                content_type="",
                history=history,
                model=model,
                pattern="reflection")

            # Aggregate evaluation costs
            total_cost += eval_metadata["cost"]
            total_latency += eval_metadata["latency"]
            total_input_tokens += eval_metadata["input_tokens"]
            total_output_tokens += eval_metadata["output_tokens"]

            if evaluation.meets_threshold:
                break  # Acceptable quality

            # Add evaluation feedback to history
            history = self._add_evaluation_feedback(history=history,
                                                    evaluation=evaluation)

            

        # Create a new CompletionResult with aggregated costs
        from utils.llm_client import CompletionResult
        aggregated_result = CompletionResult(content=result.content,
                                             input_tokens=total_input_tokens,
                                             output_tokens=total_output_tokens,
                                             cost=total_cost,
                                             latency=total_latency,
                                             model=result.model,
                                             timestamp=result.timestamp)

        return aggregated_result

    def _generate_with_evaluator_optimizer(
            self, model: str, messages: List[Dict[str, str]], content_type: str,temperature: float,
            max_tokens: int, max_iterations: int) -> Dict[str, any]:
        '''
        Generate a response with evaluator and prompt optimization.
        Aggregates costs and latency from all iterations (generation + evaluation).
        '''

        #  = messages  # Add system + user prompt to conversation history
        optimize_messages = messages.copy()
        # Track aggregated costs across all iterations
        total_cost = 0.0
        total_latency = 0.0
        total_input_tokens = 0
        total_output_tokens = 0

        iterations = 0

        while iterations <= max_iterations:
            result = self.llm_client.get_completion(model=model,
                                                    messages=optimize_messages,
                                                    temperature=temperature,
                                                    max_tokens=max_tokens)

            # Aggregate generation costs
            total_cost += result.cost
            total_latency += result.latency
            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens

            # history.append({"role": "assistant", "content": result.content})

            iterations += 1

            if iterations > max_iterations:
                break

            # Evaluate result (without history) - returns (Critique, metadata)
            evaluation, eval_metadata = self.evaluator.evaluate_content(
                content=result.content,
                content_type=content_type,
                model=model,
                pattern="evaluator_optimizer")

            # Aggregate evaluation costs
            total_cost += eval_metadata["cost"]
            total_latency += eval_metadata["latency"]
            total_input_tokens += eval_metadata["input_tokens"]
            total_output_tokens += eval_metadata["output_tokens"]

            if evaluation.meets_threshold:
                break  # Acceptable quality
            
            # Build optimization message
            system_message = [{"role": "system", "content": "You are a content optimizer. Improve content based on evaluation feedback."}]         

            if self.brand_config['optimization_system_message']:
                system_message = [{"role": "system", "content": self.brand_config['optimization_system_message']}]         

            assistant_message = [{"role": "assistant", "content": result.content}]

            optimize_messages = system_message + assistant_message

            # Add evaluation feedback to history
            optimize_messages = self._add_evaluation_feedback(history=optimize_messages,
                                                              evaluation=evaluation)


        # Create a new CompletionResult with aggregated costs
        from utils.llm_client import CompletionResult
        aggregated_result = CompletionResult(content=result.content,
                                             input_tokens=total_input_tokens,
                                             output_tokens=total_output_tokens,
                                             cost=total_cost,
                                             latency=total_latency,
                                             model=result.model,
                                             timestamp=result.timestamp)

        return aggregated_result

    def _add_evaluation_feedback(self, history: List[Dict[str, str]],
                                 evaluation: Critique) -> List[Dict[str, str]]:
        '''
        Add evaluation feedback to the message list.
        '''

        messages = history.copy()
        # Create optimization feedback based on evaluation
        feedback = "FEEDBACK:\nThe previous content had the following issues:\n"
        feedback += f"- {evaluation.reasoning}\n"
        feedback += "It also contained the following brand violations:\n"
        for violation in evaluation.violations:
            feedback += f"- {violation}\n"

        feedback += "Improve the content by addressing the feedback.\n"
        feedback += "REMINDER: Do not change the content topic, only improve it."

        # Append optimization feedback to the last user message
        messages.append({"role": "user", "content": feedback})

        return messages
