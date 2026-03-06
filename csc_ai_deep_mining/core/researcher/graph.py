# -*- coding: utf-8 -*-
"""
@Date : 2026-03-04
@Author : xiezizhe
"""

from langgraph.graph import StateGraph, START, END
from .state import ResearcherState
from .nodes import think_node, tool_node, check_action

def build_researcher_graph():
    """
    Builds and compiles the LangGraph state machine for the Researcher.

    The graph consists of a 'think' node where the LLM decides the next action,
    and a 'tool' node where external search is executed. The graph loops between
    thinking and tool usage until the LLM decides it has fully answered the
    research question.

    Returns:
        CompiledStateGraph: The compiled LangGraph application.
    """
    
    builder = StateGraph(ResearcherState)
    
    # Add nodes
    builder.add_node("think", think_node)
    builder.add_node("tool", tool_node)
    
    # Add edges
    builder.add_edge(START, "think")
    
    # Conditional routing after thinking
    builder.add_conditional_edges("think", check_action, {
        "tool_node": "tool",
        "__end__": END
    })
    
    # Loop back to think after tool
    builder.add_edge("tool", "think")
    
    return builder.compile()

# Instantiate for use
researcher_graph = build_researcher_graph()
