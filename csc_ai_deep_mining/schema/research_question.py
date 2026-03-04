# -*- coding: utf-8 -*-

"""
@Date : 2026-03-01
"""
from typing import List
from pydantic import BaseModel, Field
import uuid

class ResearchQuestion(BaseModel):
    """
    Represents a specific research question formulated by the Planner to guide Phase II (Researcher).
    It is a combination of exactly one user intent and a set of multiple constraints.
    """
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_intent: str = Field(..., description="The single underlying core user intent identified from logs")
    constraints: List[str] = Field(default_factory=list, description="A list of valid constraints associated with this intent")
    question_text: str = Field(..., description="The structured or human-readable representation of this combination")
