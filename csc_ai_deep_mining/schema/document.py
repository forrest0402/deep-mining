# -*- coding: utf-8 -*-

"""
@Date : 2026-02-09
@Author : xiezizhe
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
import time
from csc_ai_agent.llm.schema import Message


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
    name: Optional[str] = None
    content: str
    source: str # File path or URL
    chunks: List[Chunk] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)

class DialogueLog(BaseModel):
    """
    Represents a full customer service dialogue session.
    """
    irid: str
    messages: List[Message]
    
    def to_document(self) -> Document:
        """Converts the DialogueLog into a generic Document for PageIndex processing."""
        d_str_lines = []
        for m in self.messages:
            if m.role == 'function':
                d_str_lines.append(f"Tool [{m.name}]: {m.content}")
            else:
                d_str_lines.append(f"{m.role}: {m.content}")
        
        content = "\n".join(d_str_lines)
        return Document(
            doc_id=self.irid,
            name=f"dialogue_log_{self.irid}",
            content=content,
            source=f"dialogue_log_{self.irid}.xlsx"
        )
