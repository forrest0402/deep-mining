# -*- coding: utf-8 -*-
"""
@Date : 2026-03-05
@Author : xiezizhe
"""

from typing import List
from pydantic import BaseModel, Field
from csc_ai_deep_mining.schema.sop import SOPGraph
from csc_ai_deep_mining.schema.skill import AtomicSkill

class SynthesisResult(BaseModel):
    """
    Represents the final, distilled output from the Analyst Phase.
    Contains the global process map and all granular behavioral skills.
    """
    sop_graph: SOPGraph = Field(..., description="The comprehensive Mermaid-compatible SOP graph")
    skills: List[AtomicSkill] = Field(default_factory=list, description="A registry of all AtomicSkills mapped to nodes in the graph")
