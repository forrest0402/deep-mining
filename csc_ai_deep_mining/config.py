# -*- coding: utf-8 -*-
"""
@Date : 2026-03-05
@Author : xiezizhe
"""

import os
import yaml
import logging

logger = logging.getLogger(__name__)

class AppConfig:
    """
    Singleton Configuration Manager for DeepMining.
    Loads settings from config.yaml at the project root dynamically.
    """
    _instance = None
    _config_data = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        # Locate project root assuming config.py is in csc_ai_deep_mining
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "..", "config.yaml")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config.yaml from {config_path}: {e}. Initializing with empty dict.")
            self._config_data = {}

    def load_from_file(self, custom_path: str):
        """Allows injecting overrides from a custom configuration file."""
        try:
            with open(custom_path, 'r', encoding='utf-8') as f:
                custom_data = yaml.safe_load(f) or {}
                # Simple shallow dict update for demo purposes
                for section_key, section_val in custom_data.items():
                    if section_key not in self._config_data:
                        self._config_data[section_key] = {}
                    if isinstance(section_val, dict):
                        self._config_data[section_key].update(section_val)
                    else:
                        self._config_data[section_key] = section_val
        except Exception as e:
            logger.warning(f"Failed to load custom config from {custom_path}: {e}")

    # --- App ---
    @property
    def language(self) -> str:
        return self._config_data.get("app", {}).get("language", "zh_CN")
        
    @property
    def debug(self) -> bool:
        return self._config_data.get("app", {}).get("debug", False)

    # --- LLM ---
    @property
    def llm_service(self) -> str:
        return os.environ.get("LLM_SERVICE", self._config_data.get("llm", {}).get("service", "qwen")).lower()
        
    @property
    def qwen_model(self) -> str:
        return os.environ.get("LLM_MODEL", self._config_data.get("llm", {}).get("qwen_model", "qwen3-max"))
        
    @property
    def wanqing_model(self) -> str:
        return os.environ.get("LLM_MODEL", self._config_data.get("llm", {}).get("wanqing_model", "wanqing-standard"))

    @property
    def llm_api_key(self) -> str:
        return os.environ.get("DASHSCOPE_API_KEY", self._config_data.get("llm", {}).get("api_key", ""))

    # --- RAG ---
    @property
    def page_index_cache_dir(self) -> str:
        return self._config_data.get("rag", {}).get("page_index_cache_dir", ".pageindex_cache")

    # --- Concurrency ---
    @property
    def page_index_workers(self) -> int:
        return self._config_data.get("concurrency", {}).get("page_index_workers", 8)

    @property
    def analyst_skill_workers(self) -> int:
        return self._config_data.get("concurrency", {}).get("analyst_skill_workers", 5)

    @property
    def researcher_investigate_workers(self) -> int:
        return self._config_data.get("concurrency", {}).get("researcher_investigate_workers", 8)

# Global singleton instance
config = AppConfig()
