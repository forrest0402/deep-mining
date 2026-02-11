# -*- coding: utf-8 -*-

"""
@Date : 2026-02-09
@Author : xiezizhe
"""

from functools import lru_cache
from typing import Any, List, Optional

from csc_ai_agent.llm.base import ModelServiceError
from csc_ai_agent.llm.schema import ASSISTANT, Message
from csc_ai_models.grpc_api.client.wq_client import WanQingPlatformService
from csc_ai_models.grpc_api.proto.kwai_yii_for_biz_pb2 import InvokeWithMessagesRequest, LlmMessageItem


class LLMModelService(object):
    """Service for interacting with the WanQing LLM platform.

    Provides high-level methods for generating responses using specified models
    with built-in LRU caching for prompt-response pairs.
    """

    def __init__(self):
        """Initializes the LLM service with default model and platform client."""
        self.model = 'wanQing-deepseek-v3'
        self.service = WanQingPlatformService()

    @lru_cache(maxsize=100000)
    def _get_response_cached(self, prompt: str, model: str, timeout: int) -> Optional[str]:
        """Internal method to fetch and cache LLM responses.

        Args:
            prompt: The full system/user prompt.
            model: The name of the model to use.
            timeout: Request timeout in milliseconds.

        Returns:
            Optional[str]: The generated response text, or None if failed.
        """
        req = self._build_request(prompt, model=model, request_timeout=timeout)
        resp = self.service.invoke_with_messages(req, timeout=timeout)
        if not resp or not resp.response:
            return None
        return resp.response

    def _build_request(self, prompt: str, **kwargs) -> InvokeWithMessagesRequest:
        """Constructs the gRPC request object for the WanQing service.

        Args:
            prompt: The text content for the system message.
            **kwargs: Additional parameters like model name or request_timeout.

        Returns:
            InvokeWithMessagesRequest: The populated request object.
        """
        ret = []
        ret.append(LlmMessageItem(message={'role': 'system',
                                           'content': prompt}))
        model = kwargs.get('model', self.model)
        return InvokeWithMessagesRequest(model_name=model,
                                         timeout=kwargs.get('request_timeout', 40000),
                                         messages=ret)

    def __call__(self, prompt: Any, **kwargs) -> List[Message]:
        """Syntactic sugar to call the LLM service like a function.

        Handles string conversion for the prompt and wraps the response in 
        standard Message objects.

        Args:
            prompt: The prompt content (string or object with to_string()).
            **kwargs: Configuration overrides for model name or timeout.

        Returns:
            List[Message]: A list containing the generated assistant message.

        Raises:
            ModelServiceError: If the LLM request fails or returns an empty response.
        """
        if not isinstance(prompt, str):
            if hasattr(prompt, 'to_string'):
                prompt = prompt.to_string()
            else:
                prompt = str(prompt)

        model = kwargs.get('model', self.model)
        timeout = kwargs.get('request_timeout', 40000)

        response_text = self._get_response_cached(prompt, model, timeout)

        if not response_text:
            raise ModelServiceError(code="1",
                                    message=f"llm model request failed for prompt={prompt[:100]}...")
        return [
            Message(role=ASSISTANT,
                    extra={"prompt": prompt},
                    content=response_text)
        ]


if __name__ == '__main__':
    llm_service = LLMModelService()
    print(llm_service('你好，你是谁'))
