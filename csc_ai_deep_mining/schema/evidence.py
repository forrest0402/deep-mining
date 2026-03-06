# -*- coding: utf-8 -*-
"""
@Date : 2026-03-04
@Author : xiezizhe
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from csc_ai_deep_mining.schema.research_question import ResearchQuestion

class Evidence(BaseModel):
    """
    Represents a specific piece of evidence retrieved from documents
    that helps answer a Research Question.
    """
    id: str = Field(..., description="A localized unique identifier for this evidence")
    source_doc_id: str = Field(..., description="The ID or name of the source document")
    content: str = Field(..., description="The actual text or chunk retrieved from the document")
    relevance_score: float = Field(default=1.0, description="A score indicating how relevant this evidence is")
    
class ToolUsage(BaseModel):
    """
    Represents a tool utilized by an agent during a customer service dialogue.
    Extracted by the Researcher to inform the Analyst's Skill generation.
    """
    tool_name: str = Field(..., description="The name of the tool called (e.g., getSellerPunish)")
    input_args: Dict[str, Any] = Field(default_factory=dict, description="Input arguments passed to the tool")
    output_result: str = Field(default="", description="The output returned by the tool")

class ResearchResult(BaseModel):
    """
    Represents the final synthesized output from the Researcher phase 
    for a specific Research Question.
    """
    research_question: ResearchQuestion = Field(..., description="The original RQ being answered")
    evidence_list: List[Evidence] = Field(default_factory=list, description="List of evidence gathered")
    tool_usages: List[ToolUsage] = Field(default_factory=list, description="List of tools observed being used in dialogue logs relevant to this RQ")
    conclusion: str = Field(..., description="The synthesized conclusion answering the RQ based on the evidence")
    sop_baseline: str = Field(default="", description="The theoretical expectation based strictly on SOP/Guidelines documents")
    observed_patterns: str = Field(default="", description="Trends and aggregate behaviors discovered across dialogue logs")
    identified_anomalies: str = Field(default="", description="Inconsistencies where observed reality deviates from the SOP baseline")
    is_fully_answered: bool = Field(default=False, description="Whether the researcher believes the RQ is fully answered")
