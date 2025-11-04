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
from langsmith import traceable



class CompletionResult(BaseModel):
    """Result from LLM completion call with metadata"""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    
    content: str = Field(..., description="Generated text from LLM")
    input_tokens: int = Field(ge=0, description="Number of input tokens")
    output_tokens: int = Field(ge=0, description="Number of output tokens")
    cost: float = Field(ge=0.0, description="Cost in EUR")
    latency: float = Field(gt=0.0, description="Latency in seconds")
    model: str = Field(..., description="Model used (e.g., 'gpt-4o-mini')")
    timestamp: datetime = Field(..., description="When the API call was initiated (UTC)")
    structured_output: Optional[BaseModel] = Field(default=None, description="Structured output (Pydantic model) when response_format is used")


class EmbeddingResult(BaseModel):
    """Result from LLM embedding call with metadata"""
    model_config = ConfigDict(frozen=True)

    embedding: list[float] = Field(..., description="Generated embedding vector")
    input_tokens: int = Field(ge=0, description="Number of input tokens")
    cost: float = Field(ge=0.0, description="Cost in EUR")
    latency: float = Field(gt=0.0, description="Latency in seconds")
    model: str = Field(..., description="Model used (e.g., 'gpt-4o-mini')")
    timestamp: datetime = Field(..., description="When the API call was initiated (UTC)")

class LLMClient:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Initialize LLM client with retry configuration
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay for exponential backoff in seconds (default: 1.0)
            max_delay: Maximum delay between retries in seconds (default: 60.0)
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
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Load and cache pricing information
        self._load_pricing_config()
    
    def _load_pricing_config(self):
        """Load pricing configuration from environment variables with defaults"""
        # Note: load_dotenv() is called once in __init__
        
        # Default pricing in EUR per 1K tokens (as of October 2025)
        # These are fallback values - always set environment variables for production
        default_pricing = {
            "GPT4O_MINI_INPUT_PRICE_PER_1K": "0.000150",     # $0.15 per 1M tokens
            "GPT4O_MINI_OUTPUT_PRICE_PER_1K": "0.000600",    # $0.60 per 1M tokens
            "GPT4O_INPUT_PRICE_PER_1K": "0.005000",          # $5.00 per 1M tokens
            "GPT4O_OUTPUT_PRICE_PER_1K": "0.015000",         # $15.00 per 1M tokens
            "EMBEDDING_PRICE_PER_1K": "0.000020",            # $0.02 per 1M tokens
            "CLAUDE_SONET_4_INPUT_PRICE_PER_1K": "0.003000", # $3.00 per 1M tokens
            "CLAUDE_SONET_4_OUTPUT_PRICE_PER_1K": "0.015000", # $15.00 per 1M tokens
            "GPT5_INPUT_PRICE_PER_1K": "0.001500", # $1.50 per 1M tokens
            "GPT5_OUTPUT_PRICE_PER_1K": "0.01000" # $10.00 per 1M tokens
        }
        
        self.pricing = {}
        for key, default_value in default_pricing.items():
            env_value = os.getenv(key)
            if env_value:
                self.pricing[key] = float(env_value)
            else:
                self.pricing[key] = float(default_value)
                self.logger.warning(f"Using default price for {key}: {default_value} EUR/1K tokens")
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int = 0) -> float:
        """
        Calculate cost for API call based on model and token usage
        
        Args:
            model: Model name (e.g., 'gpt-4o-mini', 'gpt-4o', 'text-embedding-ada-002')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens (0 for embeddings)
            
        Returns:
            Cost in EUR
            
        Raises:
            ValueError: If model pricing is not configured
        """
        if "gpt-4o-mini" in model.lower():
            input_price_per_1k = self.pricing["GPT4O_MINI_INPUT_PRICE_PER_1K"]
            output_price_per_1k = self.pricing["GPT4O_MINI_OUTPUT_PRICE_PER_1K"]
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
            input_price_per_1k = self.pricing["CLAUDE_SONET_4_INPUT_PRICE_PER_1K"]
            output_price_per_1k = self.pricing["CLAUDE_SONET_4_OUTPUT_PRICE_PER_1K"]
        else:
            raise ValueError(f"Pricing not configured for model: {model}")
        
        # Calculate total cost
        input_cost = (input_tokens * input_price_per_1k) / 1000
        output_cost = (output_tokens * output_price_per_1k) / 1000
        
        return input_cost + output_cost
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff with jitter"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0.1, 0.3) * delay
        return delay + jitter
    
    def _is_retryable_error(self, error) -> bool:
        """Determine if an error is retryable"""
        # Import here to avoid circular imports
        from openai import RateLimitError, APIConnectionError, InternalServerError, APITimeoutError
        
        retryable_errors = (
            RateLimitError,      # Rate limit exceeded
            APIConnectionError,  # Network/connection issues
            InternalServerError, # Server errors (5xx)
            APITimeoutError,     # Request timeout
        )
        
        return isinstance(error, retryable_errors)
    
    def _execute_with_retry(self, operation, operation_name: str, **kwargs):
        """Execute an operation with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation(**kwargs)
                
            except Exception as error:
                last_error = error
                
                if attempt == self.max_retries:
                    self.logger.error(f"{operation_name} failed after {self.max_retries + 1} attempts: {error}")
                    raise
                
                if not self._is_retryable_error(error):
                    self.logger.error(f"{operation_name} failed with non-retryable error: {error}")
                    raise
                
                delay = self._calculate_delay(attempt)
                self.logger.warning(f"{operation_name} attempt {attempt + 1} failed: {error}. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
        
        # This should never be reached, but just in case
        raise last_error
    
    def configure_retries(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Update retry configuration
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff in seconds
            max_delay: Maximum delay between retries in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.logger.info(f"Retry configuration updated: max_retries={max_retries}, base_delay={base_delay}s, max_delay={max_delay}s")
    
    def get_client(self, provider: str):
        """Initialize and return the appropriate OpenAI client based on provider"""
        if provider == "openrouter":
            if not os.getenv("OPENROUTER_API_KEY") or not os.getenv("OPENROUTER_BASE_URL"):
                raise ValueError("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be set in environment variables.")
            
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL")
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        elif provider == "azure":
            if not os.getenv("AZURE_OPENAI_KEY") or not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_API_VERSION"):
                raise ValueError("AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_VERSION must be set in environment variables.")
            api_key = os.getenv("AZURE_OPENAI_KEY")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION")
            self.client = AzureOpenAI(api_key=api_key, azure_endpoint=azure_endpoint, api_version=api_version)

        return self.client
    
    @traceable(name="llm_completion", run_type="llm")
    def get_completion(self, model: str, messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 1000, response_format: type[BaseModel] | None = None) -> CompletionResult:
        """Get completion with automatic retry logic"""
        return self._execute_with_retry(
            operation=self._get_completion_internal,
            operation_name="get_completion",
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )
    
    def _get_completion_internal(self, model: str, messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 1000, response_format: type[BaseModel] | None = None) -> CompletionResult:
        """Internal completion logic with cost tracking"""
        call_timestamp = datetime.now(timezone.utc)
        start_time = time.perf_counter()
        
        # Check if model supports native structured outputs (OpenAI models only)
        supports_native_parse = not model.startswith(("anthropic/", "meta-llama/", "google/"))
        
        if response_format and supports_native_parse:
            # Use OpenAI's native structured output API
            response = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
            structured_output = response.choices[0].message.parsed
            content = response.choices[0].message.content
            
        elif response_format:
            # Manual JSON parsing for non-OpenAI models (OpenRouter, etc.)
            json_instruction = f"\n\nYou must respond with ONLY valid JSON matching this exact structure. No markdown, no explanations, just raw JSON:\n{response_format.model_json_schema()}"
            
            # Modify messages to request JSON
            modified_messages = messages.copy()
            if modified_messages and modified_messages[-1]["role"] == "user":
                modified_messages[-1] = {
                    "role": "user",
                    "content": modified_messages[-1]["content"] + json_instruction
                }
            
            response = self.client.chat.completions.create(
                model=model,
                messages=modified_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            
            # Parse JSON with robust extraction
            try:
                import json
                import re
                
                # Try direct parsing first (clean JSON)
                try:
                    parsed_data = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: Extract JSON from response
                    # Remove markdown code fences if present
                    cleaned = re.sub(r'^```(?:json)?\s*', '', content, flags=re.MULTILINE)
                    cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.MULTILINE)
                    
                    # Find first complete JSON object (first { to matching })
                    json_match = re.search(r'\{.*?\}\s*(?:\n|$)', cleaned, re.DOTALL)
                    
                    if not json_match:
                        # Try finding JSON anywhere in response
                        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
                    
                    if not json_match:
                        raise ValueError(
                            f"No valid JSON found in response.\n"
                            f"Full content:\n{content}"
                        )
                    
                    json_str = json_match.group(0).strip()
                    parsed_data = json.loads(json_str)
                
                # Validate with Pydantic
                structured_output = response_format(**parsed_data)
                
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Failed to parse JSON from model response.\n"
                    f"Error: {e}\n"
                    f"Content:\n{content}"
                )
            except Exception as e:
                raise ValueError(
                    f"Failed to validate structured output with Pydantic.\n"
                    f"Error: {e}\n"
                    f"Parsed data: {parsed_data if 'parsed_data' in locals() else 'N/A'}\n"
                    f"Content:\n{content[:1000]}"
                )
        else:
            # Regular completion without structured output
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            structured_output = None
        
        end_time = time.perf_counter()
        
        latency = end_time - start_time
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        
        self.log_api_call(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency=latency,
            timestamp=call_timestamp
        )
        
        return CompletionResult(
            content=content,
            model=model,
            cost=cost,
            latency=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=call_timestamp,
            structured_output=structured_output
        )
    
    @traceable(name="embedding_generation", run_type="embedding")
    def get_embedding(self, model: str, text: str) -> EmbeddingResult:
        """Get embedding with automatic retry logic"""
        return self._execute_with_retry(
            operation=self._get_embedding_internal,
            operation_name="get_embedding",
            model=model,
            text=text
        )
    
    def _get_embedding_internal(self, model: str, text: str) -> EmbeddingResult:
        # Capture timestamp when API call starts
        call_timestamp = datetime.now(timezone.utc)
        start_time = time.perf_counter()

        response = self.client.embeddings.create(
            model=model,
            input=text
        )

        end_time = time.perf_counter()

        latency = end_time - start_time
        usage = response.usage
        input_tokens = usage.prompt_tokens
        
        # Use helper method for cost calculation (embeddings have 0 output tokens)
        cost = self._calculate_cost(response.model, input_tokens, 0)

        result = EmbeddingResult(
            embedding=response.data[0].embedding,
            input_tokens=input_tokens,
            cost=cost,
            latency=latency,
            model=response.model,
            timestamp=call_timestamp
        )

        # Log the API call (embeddings have 0 output tokens)
        self.log_api_call(response.model, input_tokens, 0, cost, latency, call_timestamp)

        return result


    def log_api_call(self, model: str, input_tokens: int, output_tokens: int, cost: float, latency: float, timestamp: datetime):
        """Log API call to CSV for cost tracking"""
        
        log_file = "data/api_calls.csv"
        
        # Create file with headers if doesn't exist
        if not os.path.exists(log_file):
            os.makedirs("data", exist_ok=True)
            with open(log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "model", "input_tokens", "output_tokens", "cost_eur", "latency_seconds"])
        
        # Append log
        with open(log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp.isoformat(),
                model,
                input_tokens,
                output_tokens,
                f"{cost:.6f}",
                f"{latency:.3f}"
            ])
        
        # Log to CSV only - console output handled by caller if needed

            
