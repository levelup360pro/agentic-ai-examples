"""Unified LLM client for the marketing_team example.

Wraps provider-specific SDKs (OpenAI, Azure OpenAI, OpenRouter) with
consistent retry, pricing, cost logging, and optional structured
output parsing. All externally consumed results are immutable
Pydantic models for clarity and downstream safety.

Public API
        LLMClient: High-level client with `get_completion` and `get_embedding`.
        CompletionResult, EmbeddingResult: Pydantic results with cost/latency.

Notes
        - This module centralizes provider differences so example code can
            depend on a stable interface.
        - Pricing values are configurable via environment variables; defaults
            are provided for local development and examples.
        - Methods are instrumented with `langsmith.traceable` for optional
            tracing during example runs.
"""

from openai import OpenAI, AzureOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional, Any
import os
import time
import csv
import random
import logging
import json
import re
import uuid
from openai import RateLimitError, APIConnectionError, InternalServerError, APITimeoutError
from langsmith import traceable
from langchain_openai import ChatOpenAI, AzureChatOpenAI



class CompletionResult(BaseModel):
    """Result from an LLM completion call with metadata.

    For tool-calling responses, raw_response/tool_calls may be populated.
    structured_output holds a Pydantic instance when response_format is used.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    content: str = Field(..., description="Generated text from LLM")
    input_tokens: int = Field(ge=0, description="Number of input tokens")
    output_tokens: int = Field(ge=0, description="Number of output tokens")
    cost: float = Field(ge=0.0, description="Cost in EUR")
    latency: float = Field(gt=0.0, description="Latency in seconds")
    model: str = Field(..., description="Model used (e.g., 'gpt-4o-mini')")
    timestamp: datetime = Field(..., description="When the API call was initiated (UTC)")
    tool_calls: Optional[list] = None
    raw_response: Optional[Any] = None
    structured_output: Optional[BaseModel] = Field(default=None, description="Structured output (Pydantic model) when response_format is used")


class EmbeddingResult(BaseModel):
    """Result from an embedding generation call with metadata."""
    model_config = ConfigDict(frozen=True)

    embedding: list[float] = Field(..., description="Generated embedding vector")
    input_tokens: int = Field(ge=0, description="Number of input tokens")
    cost: float = Field(ge=0.0, description="Cost in EUR")
    latency: float = Field(gt=0.0, description="Latency in seconds")
    model: str = Field(..., description="Model used (e.g., 'gpt-4o-mini')")
    timestamp: datetime = Field(..., description="When the API call was initiated (UTC)")


class LLMClient:

    def __init__(self,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0):
        """Initialize client with retry/backoff configuration.

        Args:
            max_retries: Max retry attempts for transient errors.
            base_delay: Base seconds used for exponential backoff.
            max_delay: Ceiling for any individual backoff sleep.
        """
        # Load environment variables once at initialization
        load_dotenv()

        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.client = None

        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Load and cache pricing information
        self._load_pricing_config()

    def configure_retries(self,
                          max_retries: int = 3,
                          base_delay: float = 1.0,
                          max_delay: float = 60.0):
        """Update retry configuration at runtime."""
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.logger.info(
            f"Retry configuration updated: max_retries={max_retries}, base_delay={base_delay}s, max_delay={max_delay}s"
        )

    def get_client(self, provider: str, tool_calling_enabled: bool = False):
        """Initialize and cache provider client for subsequent calls.

        Args:
            provider: One of 'openrouter' or 'azure'.
            tool_calling_enabled: Reserved flag (not used yet).

        Returns:
            Underlying provider client instance.
        """
        if provider == "openrouter":
            if not os.getenv("OPENROUTER_API_KEY") or not os.getenv(
                    "OPENROUTER_BASE_URL"):
                raise ValueError(
                    "OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be set in environment variables."
                )

            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL")
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        elif provider == "azure":
            if not os.getenv("AZURE_OPENAI_KEY") or not os.getenv(
                    "AZURE_OPENAI_ENDPOINT") or not os.getenv(
                        "AZURE_OPENAI_API_VERSION"):
                raise ValueError(
                    "AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_VERSION must be set in environment variables."
                )
            api_key = os.getenv("AZURE_OPENAI_KEY")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION")
            self.client = AzureOpenAI(api_key=api_key,
                                      azure_endpoint=azure_endpoint,
                                      api_version=api_version)

        self.provider = provider
        return self.client

    @traceable(name="llm_completion", run_type="llm")
    def get_completion(self,
                       model: str,
                       messages: list[dict[str, str]],
                       temperature: float = None,
                       max_tokens: int = None,
                       response_format: type[BaseModel] | None = None,
                       tool_support: bool = False,
                       tools: list = None) -> CompletionResult:
        """Obtain a text or structured completion with retry logic.

        Routes to tool-support path if tool_support=True, otherwise
        uses native or manual structured output parsing when a
        response_format is supplied.
        """
        call_id = str(uuid.uuid4())
        self.logger.info(
            f"[LLMClient] Initiating | call_id={call_id} model={model} temperature={temperature} messages_count={len(messages)}"
        )

        result = None
        if tool_support:
            # Route to tool calling path
            result = self._execute_with_retry(
                operation=self._get_completion_with_tool_support,
                operation_name="get_completion_tool_support",
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools)
        else:
            # Route to regular completion path
            result = self._execute_with_retry(
                operation=self._get_completion_internal,
                operation_name="get_completion",
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format)
        
        if result:
            self.logger.info(
                f"[LLMClient] Complete | call_id={call_id} tokens={result.input_tokens}/{result.output_tokens} cost={result.cost:.6f} EUR latency={result.latency:.3f}s"
            )
        
        return result

    @traceable(name="embedding_generation", run_type="embedding")
    def get_embedding(self, model: str, text: str) -> EmbeddingResult:
        """Generate embeddings with retry logic and cost tracking."""
        call_id = str(uuid.uuid4())
        self.logger.info(
            f"[LLMClient] Initiating Embedding | call_id={call_id} model={model} text_len={len(text)}"
        )

        result = self._execute_with_retry(operation=self._get_embedding_internal,
                                        operation_name="get_embedding",
                                        model=model,
                                        text=text)
        
        if result:
            self.logger.info(
                f"[LLMClient] Complete Embedding | call_id={call_id} tokens={result.input_tokens} cost={result.cost:.6f} EUR latency={result.latency:.3f}s"
            )
        return result

    def log_api_call(self, model: str, input_tokens: int, output_tokens: int,
                     cost: float, latency: float, timestamp: datetime):
        """Append a single API call record to the cost tracking CSV."""

        log_file = "data/api_calls.csv"

        # Create file with headers if doesn't exist
        if not os.path.exists(log_file):
            os.makedirs("data", exist_ok=True)
            with open(log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "model", "input_tokens", "output_tokens",
                    "cost_eur", "latency_seconds"
                ])

        # Append log
        with open(log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp.isoformat(), model, input_tokens, output_tokens,
                f"{cost:.6f}", f"{latency:.3f}"
            ])

        # Log to CSV only - console output handled by caller if needed

    def _load_pricing_config(self):
        """Load pricing configuration from environment variables (with defaults)."""
        # Note: load_dotenv() is called once in __init__

        # Default pricing in EUR per 1K tokens (as of October 2025)
        # These are fallback values - always set environment variables for production
        default_pricing = {
            "GPT4O_MINI_INPUT_PRICE_PER_1K": "0.000150",  # $0.15 per 1M tokens
            "GPT4O_MINI_OUTPUT_PRICE_PER_1K":
            "0.000600",  # $0.60 per 1M tokens
            "GPT4O_INPUT_PRICE_PER_1K": "0.005000",  # $5.00 per 1M tokens
            "GPT4O_OUTPUT_PRICE_PER_1K": "0.015000",  # $15.00 per 1M tokens
            "EMBEDDING_PRICE_PER_1K": "0.000020",  # $0.02 per 1M tokens
            "CLAUDE_SONET_4_INPUT_PRICE_PER_1K":
            "0.003000",  # $3.00 per 1M tokens
            "CLAUDE_SONET_4_OUTPUT_PRICE_PER_1K":
            "0.015000",  # $15.00 per 1M tokens
            "GPT5_INPUT_PRICE_PER_1K": "0.001500",  # $1.50 per 1M tokens
            "GPT5_OUTPUT_PRICE_PER_1K": "0.01000"  # $10.00 per 1M tokens
        }

        self.pricing = {}
        for key, default_value in default_pricing.items():
            env_value = os.getenv(key)
            if env_value:
                self.pricing[key] = float(env_value)
            else:
                self.pricing[key] = float(default_value)
                self.logger.warning(
                    f"Using default price for {key}: {default_value} EUR/1K tokens"
                )

    def _calculate_cost(self,
                        model: str,
                        input_tokens: int,
                        output_tokens: int = 0) -> float:
        """Calculate cost for an API call based on token usage.

        Args:
            model: Model name (pricing key inferred heuristically).
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens (0 for embeddings).

        Returns:
            Cost in EUR.

        Raises:
            ValueError: If the model is unknown to pricing config.
        """
        if "gpt-4o-mini" in model.lower():
            input_price_per_1k = self.pricing["GPT4O_MINI_INPUT_PRICE_PER_1K"]
            output_price_per_1k = self.pricing[
                "GPT4O_MINI_OUTPUT_PRICE_PER_1K"]
        elif "gpt-4o" in model.lower():
            input_price_per_1k = self.pricing["GPT4O_INPUT_PRICE_PER_1K"]
            output_price_per_1k = self.pricing["GPT4O_OUTPUT_PRICE_PER_1K"]
        elif "gpt-5" in model.lower():
            input_price_per_1k = self.pricing["GPT5_INPUT_PRICE_PER_1K"]
            output_price_per_1k = self.pricing["GPT5_OUTPUT_PRICE_PER_1K"]
        elif "embedding" in model.lower() or "ada" in model.lower():
            # Embedding models (output_tokens should be 0)
            input_price_per_1k = self.pricing["EMBEDDING_PRICE_PER_1K"]
            output_price_per_1k = 0.0
        elif "sonnet-4" in model.lower():
            input_price_per_1k = self.pricing[
                "CLAUDE_SONET_4_INPUT_PRICE_PER_1K"]
            output_price_per_1k = self.pricing[
                "CLAUDE_SONET_4_OUTPUT_PRICE_PER_1K"]
        else:
            raise ValueError(f"Pricing not configured for model: {model}")

        # Calculate total cost
        input_cost = (input_tokens * input_price_per_1k) / 1000
        output_cost = (output_tokens * output_price_per_1k) / 1000

        return input_cost + output_cost

    def _calculate_delay(self, attempt: int) -> float:
        """Compute exponential backoff delay with jitter."""
        delay = min(self.base_delay * (2**attempt), self.max_delay)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0.1, 0.3) * delay
        return delay + jitter

    def _is_retryable_error(self, error) -> bool:
        """Return True if error type is considered transient/retryable."""

        retryable_errors = (
            RateLimitError,  # Rate limit exceeded
            APIConnectionError,  # Network/connection issues
            InternalServerError,  # Server errors (5xx)
            APITimeoutError,  # Request timeout
        )

        return isinstance(error, retryable_errors)

    def _execute_with_retry(self, operation, operation_name: str, **kwargs):
        """Execute an operation with retry + transient error handling."""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                return operation(**kwargs)

            except Exception as error:
                last_error = error

                if attempt == self.max_retries:
                    self.logger.error(
                        f"{operation_name} failed after {self.max_retries + 1} attempts: {error}"
                    )
                    raise

                if not self._is_retryable_error(error):
                    self.logger.error(
                        f"{operation_name} failed with non-retryable error: {error}"
                    )
                    raise

                delay = self._calculate_delay(attempt)
                self.logger.warning(
                    f"{operation_name} attempt {attempt + 1} failed: {error}. Retrying in {delay:.2f} seconds..."
                )
                time.sleep(delay)

        # This should never be reached, but just in case
        raise last_error

    def _create_chat_client(self, model: str, temperature: float, max_tokens: int):
        """Create a LangChain chat client for tool-calling flows."""

        if self.provider == "openrouter":
            return ChatOpenAI(model=model,
                              temperature=temperature,
                              max_tokens=max_tokens,
                              openai_api_key=os.getenv("OPENROUTER_API_KEY"),
                              openai_api_base=os.getenv("OPENROUTER_BASE_URL"))
        elif self.provider == "azure":
            return AzureChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"))

    def _parse_structured_output(
        self,
        content: str,
        response_format: type[BaseModel],
    ) -> BaseModel:
        """Extract and validate structured output from a raw text response.

        Performs a resilient JSON extraction for non-native providers.
        """

        # Manual JSON parsing for non-OpenAI models
        try:
            # Try direct parsing first (clean JSON)
            parsed_data = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: Extract JSON from response
            cleaned = re.sub(r'^```(?:json)?\s*',
                             '',
                             content,
                             flags=re.MULTILINE)
            cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.MULTILINE)

            # Find first complete JSON object
            json_match = re.search(r'\{.*?\}\s*(?:\n|$)', cleaned, re.DOTALL)

            if not json_match:
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
                                       cleaned, re.DOTALL)

            if not json_match:
                raise ValueError(
                    f"No valid JSON found in response.\nFull content:\n{content}"
                )

            json_str = json_match.group(0).strip()
            parsed_data = json.loads(json_str)

        # Validate with Pydantic
        try:
            return response_format(**parsed_data)
        except Exception as e:
            raise ValueError(
                f"Failed to validate structured output with Pydantic.\n"
                f"Error: {e}\n"
                f"Parsed data: {parsed_data}\n"
                f"Content:\n{content[:1000]}")

    def _add_json_instruction_to_messages(
            self, messages: list[dict[str, str]],
            response_format: type[BaseModel]) -> list[dict[str, str]]:
        """Append strict JSON formatting instructions to final user message."""

        json_instruction = (
            f"\n\nYou must respond with ONLY valid JSON matching this exact structure. "
            f"No markdown, no explanations, just raw JSON:\n"
            f"{response_format.model_json_schema()}")

        modified_messages = messages.copy()
        if modified_messages and modified_messages[-1]["role"] == "user":
            modified_messages[-1] = {
                "role": "user",
                "content": modified_messages[-1]["content"] + json_instruction
            }

        return modified_messages

    def _get_completion_internal(
            self,
            model: str,
            messages: list[dict[str, str]],
            temperature: float,
            max_tokens: int,
            response_format: type[BaseModel] | None = None
    ) -> CompletionResult:
        """Internal completion path (no tool calling)."""
        call_timestamp = datetime.now(timezone.utc)
        start_time = time.perf_counter()

        # Check if model supports native structured outputs (OpenAI models only)
        supports_native_parse = not model.startswith(
            ("anthropic/", "meta-llama/", "google/"))

        if response_format and supports_native_parse:
            # Use OpenAI's native structured output API
            response = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format)
            structured_output = response.choices[0].message.parsed
            content = response.choices[0].message.content

        elif response_format:
            # Manual JSON parsing for non-OpenAI models
            modified_messages = self._add_json_instruction_to_messages(
                messages, response_format)

            response = self.client.chat.completions.create(
                model=model,
                messages=modified_messages,
                temperature=temperature,
                max_tokens=max_tokens)
            content = response.choices[0].message.content
            structured_output = self._parse_structured_output(
                content=content,
                response_format=response_format)

        else:
            # Regular completion
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens)
            content = response.choices[0].message.content
            structured_output = None

        end_time = time.perf_counter()

        # Extract usage and calculate cost
        latency = end_time - start_time
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        self.log_api_call(model=model,
                          input_tokens=input_tokens,
                          output_tokens=output_tokens,
                          cost=cost,
                          latency=latency,
                          timestamp=call_timestamp)

        return CompletionResult(content=content,
                                model=model,
                                cost=cost,
                                latency=latency,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                timestamp=call_timestamp,
                                structured_output=structured_output)

    def _get_completion_with_tool_support(
            self,
            model: str,
            messages: list[dict[str, str]],
            temperature: float,
            max_tokens: int,
            tools: list,
            response_format: type[BaseModel] | None = None
    ) -> CompletionResult:
        """Internal path for tool-calling completions with cost tracking."""

        call_timestamp = datetime.now(timezone.utc)
        start_time = time.perf_counter()

        # Create LangChain client
        chat_client = self._create_chat_client(model=model, temperature=temperature, max_tokens=max_tokens)
        llm_with_tools = chat_client.bind_tools(tools)

        # Add structured output if requested
        if response_format:
            # LangChain supports .with_structured_output()
            llm_with_tools = llm_with_tools.with_structured_output(
                response_format)

        # Invoke
        response = llm_with_tools.invoke(messages)

        end_time = time.perf_counter()

        # Extract content and structured output
        if response_format:
            # Response IS the structured output
            structured_output = response
            content = str(response)  # Fallback string representation
        else:
            content = response.content if hasattr(response,
                                                  'content') else str(response)
            structured_output = None

        # Extract usage
        latency = end_time - start_time
        usage_metadata = getattr(response, 'usage_metadata', {})
        input_tokens = usage_metadata.get("input_tokens", 0)
        output_tokens = usage_metadata.get("output_tokens", 0)

        cost = self._calculate_cost(model, input_tokens, output_tokens)

        self.log_api_call(model=model,
                          input_tokens=input_tokens,
                          output_tokens=output_tokens,
                          cost=cost,
                          latency=latency,
                          timestamp=call_timestamp)

        return CompletionResult(content=content,
                                model=model,
                                cost=cost,
                                latency=latency,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                timestamp=call_timestamp,
                                tool_calls=getattr(response, 'tool_calls', None),
                                raw_response=response,
                                structured_output=structured_output
        )

    def _get_embedding_internal(self, model: str,
                                text: str) -> EmbeddingResult:
        """Internal embedding generation helper."""
        # Capture timestamp when API call starts
        call_timestamp = datetime.now(timezone.utc)
        start_time = time.perf_counter()

        response = self.client.embeddings.create(model=model, input=text)

        end_time = time.perf_counter()

        latency = end_time - start_time
        usage = response.usage
        input_tokens = usage.prompt_tokens

        # Use helper method for cost calculation (embeddings have 0 output tokens)
        cost = self._calculate_cost(response.model, input_tokens, 0)

        result = EmbeddingResult(embedding=response.data[0].embedding,
                                 input_tokens=input_tokens,
                                 cost=cost,
                                 latency=latency,
                                 model=response.model,
                                 timestamp=call_timestamp)

        # Log the API call (embeddings have 0 output tokens)
        self.log_api_call(response.model, input_tokens, 0, cost, latency,
                          call_timestamp)

        return result
