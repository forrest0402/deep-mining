# -*- coding: utf-8 -*-

"""
@Date : 2026-02-09
@Author : xiezizhe
"""

import logging
from typing import Optional

from csc_ai_models.grpc_api.client.wq_client import WanQingPlatformService
from csc_ai_models.grpc_api.proto.kwai_yii_for_biz_pb2 import InvokeWithMessagesRequest, LlmMessageItem

from .base_service import BaseLLMService

logger = logging.getLogger(__name__)


class LLMModelService(BaseLLMService):
    """Service for interacting with the WanQing LLM platform.

    Inherits completely from BaseLLMService, delegating response caching 
    and error handling upstream while providing specific gRPC implementations.
    """

    def __init__(self):
        """Initializes the LLM service with default model and platform client."""
        super().__init__(model='wanQing-deepseek-v3', max_retries=3)
        self.service = WanQingPlatformService()

    def _invoke_api(self, prompt: str, model_name: str, timeout: int) -> Optional[str]:
        """Issues the gRPC request to WanQing."""
        req = self._build_request(prompt, model=model_name, request_timeout=timeout)
        resp = self.service.invoke_with_messages(req, timeout=timeout)
        if resp and resp.response:
            return resp.response
        return None

    def _build_request(self, prompt: str, **kwargs) -> InvokeWithMessagesRequest:
        """Constructs the gRPC request object for the WanQing service."""
        ret = [LlmMessageItem(message={'role': 'system', 'content': prompt})]
        model = kwargs.get('model', self.model)
        return InvokeWithMessagesRequest(model_name=model,
                                         timeout=kwargs.get('request_timeout', 600000),
                                         messages=ret)

if __name__ == '__main__':
    llm_service = LLMModelService()
    print(llm_service('你好，你是谁'))
