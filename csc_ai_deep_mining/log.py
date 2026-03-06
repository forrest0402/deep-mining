# -*- coding: utf-8 -*-

"""
@Date : 2026-08-25
@Author : xiezizhe
"""

"""Logging configuration and management for the agent framework."""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(log_file="grpc.log", level=None):
    """Configures and returns a centralized logger with rotation and console output.

    Args:
        log_file (str): Path to the log file.
        level (Optional[int]): Logging level (e.g., logging.INFO). If None,
            the level is determined by the `UED_AGENT_DEBUG` environment variable.

    Returns:
        logging.Logger: The configured logger instance.
    """
    # 1. 获取 Logger 实例 (Configure base package logger)
    _logger = logging.getLogger('csc_ai_deep_mining')

    # 防止重复添加 Handler（如果 logger 已经配置过，直接返回）
    if _logger.handlers:
        return _logger

    # 2. 确定日志级别
    if level is None:
        debug_env = os.getenv('UED_AGENT_DEBUG', '0').strip().lower()
        level = logging.DEBUG if debug_env in ('1', 'true') else logging.INFO

    _logger.setLevel(level)

    # 3. 定义统一的格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s:[line:%(lineno)d][%(process)d] - %(levelname)s - %(message)s'
    )

    # 4. 配置控制台 Handler (StreamHandler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)

    # 5. 配置文件 Handler (RotatingFileHandler)
    # 使用 RotatingFileHandler 可以自动切分文件，避免单个日志文件过大
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB 自动切分
            backupCount=5,  # 保留5个旧文件
            encoding='utf-8'  # 关键！显式指定编码为 UTF-8
        )
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)
    except Exception as e:
        print(f"无法创建日志文件: {e}")

    return _logger


# 实例化
logger = setup_logger()
