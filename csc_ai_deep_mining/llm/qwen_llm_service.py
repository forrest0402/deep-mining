# -*- coding: utf-8 -*-

"""
@Date : 2026-03-04
@Author : xiezizhe
"""

import logging
import os
import random
from http import HTTPStatus
from typing import Optional

import dashscope
from dashscope.api_entities.dashscope_response import GenerationResponse

from csc_ai_deep_mining.config import config
from .base_service import BaseLLMService

logger = logging.getLogger(__name__)

class QwenLLMModelService(BaseLLMService):
    """Service for interacting with the Qwen LLM platform using Dashscope.

    Inherits logic from BaseLLMService to standardize caching, retry logic
    and standardized API error wrapping.
    """

    def __init__(self, concurrency_limit: int = 2, qpm_limit: int = 15):
        """Initializes the Qwen LLM service."""
        model_name = config.qwen_model
        super().__init__(model=model_name, max_retries=3)
        # Read API keys from config, separated by comma if multiple
        api_key_env = config.llm_api_key
        self.api_keys = [k.strip() for k in api_key_env.split(",")] if api_key_env else []
        if not self.api_keys:
            logger.warning("api_key in config.yaml is not set. Qwen API calls will fail.")

    def _invoke_api(self, prompt: str, model_name: str, timeout: int) -> Optional[str]:
        """Internal method to fetch LLM responses from DashScope synchronously."""
        if not self.api_keys:
            logger.error("No API keys configured for DashScope.")
            return None
            
        dashscope.api_key = random.choice(self.api_keys)
        messages = [{'role': 'user', 'content': prompt}]

        response: GenerationResponse = dashscope.Generation.call(
            model=model_name,
            messages=messages,
            result_format='message',
            stream=False,
        )

        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            logger.warning(f"Qwen call failed. Request ID: {response.request_id}, Status: {response.status_code}, Msg: {response.message}")
            return None
