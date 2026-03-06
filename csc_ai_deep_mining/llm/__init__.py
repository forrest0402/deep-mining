# -*- coding: utf-8 -*-

"""
@Date : 2026-02-09
@Author : xiezizhe
"""
import os
import logging

from csc_ai_deep_mining.config import config

logger = logging.getLogger(__name__)

# Determine which LLM service to use based on the LLM_SERVICE configuration.
# Defaults to "wanqing". If set to "qwen", it will use the QwenLLMModelService.
llm_service_type = config.llm_service

if llm_service_type == "qwen":
    try:
        from .qwen_llm_service import QwenLLMModelService as LLMModelService
        logger.info("Loaded QwenLLMModelService as the default LLM service.")
    except ImportError as e:
        logger.error(f"Failed to load QwenLLMModelService: {e}. Falling back to wanqing.")
        from .wanqing_llm_service import LLMModelService
else:
    from .wanqing_llm_service import LLMModelService
    logger.info("Loaded WanQing LLMModelService as the default LLM service.")

__all__ = ["LLMModelService"]
