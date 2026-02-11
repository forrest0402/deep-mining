# -*- coding: utf-8 -*-

"""
@Date : 2026-02-09
@Author : xiezizhe
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
import time

class Chunk(BaseModel):
    """
    Represents a chunk of text split from a document.
    Used for embedding and retrieval.
    """
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class Document(BaseModel):
    """
    Represents a source document (e.g., a PDF, text file, etc.).
    """
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    source: str # File path or URL
    chunks: List[Chunk] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
