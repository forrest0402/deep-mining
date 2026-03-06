# -*- coding: utf-8 -*-

"""
@Date : 2026-03-04
@Author : xiezizhe
"""

import logging
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, List, Optional

from csc_ai_agent.llm.base import ModelServiceError
from csc_ai_agent.llm.schema import ASSISTANT, Message

logger = logging.getLogger(__name__)

class BaseLLMService(ABC):
    """Abstract base class for LLM Services.
    
    Provides common implementation for generating responses with built-in
    retries, caching, and standard message formatting. Subclasses must implement
    the _invoke_api method to integrate with specific LLM providers.
    """

    def __init__(self, model: str, max_retries: int = 3):
        self.model = model
        self.max_retries = max_retries

    @abstractmethod
    def _invoke_api(self, prompt: str, model_name: str, timeout: int) -> Optional[str]:
        """Subclasses must implement the actual API call logic.
        
        Args:
            prompt: The full text prompt.
            model_name: The target model name.
            timeout: Request timeout in milliseconds.
            
        Returns:
            The raw text response, or None if the API call naturally failed (which triggers a retry).
            Can also raise exceptions, which will be caught and trigger a retry.
        """
        pass

    @lru_cache(maxsize=100000)
    def _get_response_cached(self, prompt: str, model: str, timeout: int) -> str:
        """Internal method to fetch and cache LLM responses with retry logic.

        Args:
            prompt: The full system/user prompt.
            model: The name of the model to use.
            timeout: Request timeout in milliseconds.

        Returns:
            str: The generated response text.

        Raises:
            ModelServiceError: If the request fails after max_retries attempts.
        """
        for attempt in range(self.max_retries):
            try:
                response = self._invoke_api(prompt, model, timeout)
                if response:
                    return response
                logger.warning(f"[{self.__class__.__name__}] Returned empty response (Attempt {attempt + 1}/{self.max_retries}).")
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] Exception fetching LLM response (Attempt {attempt + 1}/{self.max_retries}): {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(2)  # Sleep for 2 seconds before retrying
                
        raise ModelServiceError(code="1", message=f"LLM request failed after {self.max_retries} attempts for prompt={prompt[:100]}...")

    def __call__(self, prompt: Any, **kwargs) -> List[Message]:
        """Syntactic sugar to call the LLM service like a function.

        Handles string conversion for the prompt and wraps the response in 
        standard Message objects.

        Args:
            prompt: The prompt content (string or object with to_string()).
            **kwargs: Configuration overrides for model name or request_timeout.

        Returns:
            List[Message]: A list containing the generated assistant message.

        Raises:
            ModelServiceError: If the LLM request fails completely.
        """
        if not isinstance(prompt, str):
            if hasattr(prompt, 'to_string'):
                prompt = prompt.to_string()
            else:
                prompt = str(prompt)

        model = kwargs.get('model', self.model)
        timeout = kwargs.get('request_timeout', 600000)

        response_text = self._get_response_cached(prompt, model, timeout)

        return [
            Message(role=ASSISTANT,
                    extra={"prompt": prompt},
                    content=response_text)
        ]
