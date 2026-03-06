# -*- coding: utf-8 -*-
"""
@Date : 2026-03-04
@Author : xiezizhe
"""

from typing import Annotated, List, Any
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

from csc_ai_deep_mining.schema.research_question import ResearchQuestion
from csc_ai_deep_mining.schema.document import Document, DialogueLog
from csc_ai_deep_mining.schema.evidence import Evidence


class ResearcherState(TypedDict):
    """
    Represents the state of the Researcher agent during the gathering of evidence.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Context
    research_question: ResearchQuestion
    documents: List[Document]
    dialogue_logs: List[DialogueLog]
    
    # Pre-built tools
    search_tool: Any
    dialogue_tool: Any
    
    # Accumulated data
    search_queries: List[str]
    evidence_list: List[Evidence]
    
    # Decisions
    conclusion: str
    is_fully_answered: bool
