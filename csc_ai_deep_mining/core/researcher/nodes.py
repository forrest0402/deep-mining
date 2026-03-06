# -*- coding: utf-8 -*-
"""
@Date : 2026-03-04
@Author : xiezizhe
"""

import json
import logging
import re
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage

from csc_ai_deep_mining.llm import LLMModelService
from .state import ResearcherState
from .tools import create_search_documents_tool, create_search_dialogue_log_by_pageindex_tool
from csc_ai_deep_mining.utils.llm import extract_json_from_llm

logger = logging.getLogger(__name__)

def parse_json_from_llm(text: str) -> dict:
    """
    Extracts and parses JSON content from an LLM response string.
    """
    return extract_json_from_llm(text)


def think_node(state: ResearcherState) -> dict:
    """
    Evaluates the current state to decide the next action for the researcher.

    The LLM reviews the research question, conversation history, and accumulated
    evidence, and decides whether to search for more information (action: "search")
    or to provide a final conclusion (action: "answer").

    Args:
        state (ResearcherState): The current state dictionary containing the
            message history and context.

    Returns:
        dict: A dictionary with the "messages" key appended with the LLM's thought
            process formatted as an AIMessage containing a JSON payload.
    """
    logger.info("Researcher is thinking...")
    llm = LLMModelService()
    
    # We maintain the prompt and conversation history as a single string 
    # to pass to the WanQing LLM service which takes a system prompt.
    prompt_lines = [msg.content for msg in state["messages"] if isinstance(msg, HumanMessage) or isinstance(msg, AIMessage)]
    
    # Send the combined context to LLM
    # In WanQing Service, we just pass the last human prompt (rendered with instructions)
    if not prompt_lines:
        raise ValueError("State must have at least the initial system prompt message.")
        
    compiled_prompt = "\n\n".join(prompt_lines)
    
    try:
        response_messages = llm(compiled_prompt)
        response_text = response_messages[0].content
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        response_text = '{"action": "answer", "is_fully_answered": false, "conclusion": "Error calling LLM."}'
        
    parsed = parse_json_from_llm(response_text)
    
    if not parsed:
        # Fallback to prevent hang
        parsed = {"action": "answer", "conclusion": "Failed to parse valid action.", "is_fully_answered": False}
        
    # Append the raw text to messages
    return {"messages": [AIMessage(content=json.dumps(parsed, ensure_ascii=False), name="think_node")]}


def check_action(state: ResearcherState) -> Literal["tool_node", "__end__"]:
    """
    A conditional edge function that routes execution based on the LLM's decision.

    Reads the parsed JSON output from the most recent AIMessage in the state
    to determine the workflow's next step.

    Args:
        state (ResearcherState): The current state of the graph.

    Returns:
        Literal["tool_node", "__end__"]: The name of the next node to execute.
    """
    last_message = state["messages"][-1]
    parsed = parse_json_from_llm(last_message.content)
    
    action = parsed.get("action", "answer")
    if action == "search":
        return "tool_node"
    return "__end__"


def tool_node(state: ResearcherState) -> dict:
    """
    Executes the appropriate search tool based on the LLM's thought payload.

    Extracts the query from the recent state, executes the document search tool,
    and formulates the tool's output back into a HumanMessage for the LLM's
    next think cycle.

    Args:
        state (ResearcherState): The current state containing the intended search query.

    Returns:
        dict: The updated state dictionary with the search result appended to "messages"
            and the new query added to the "search_queries" tracking list.
    """
    logger.info("Researcher is using search tool...")
    last_message = state["messages"][-1]
    parsed = parse_json_from_llm(last_message.content)
    
    query = parsed.get("query", "")
    
    # Initialize tool from state
    search_tool = state.get("search_tool")
    
    if not query:
        result = "Error: No query provided for search tool."
    else:
        # Execute tool
        doc_result = search_tool.invoke({"query": query})
        
        dialogue_tool = state.get("dialogue_tool")
        if dialogue_tool:
            logger.info("Researcher is using dialogue log search tool...")
            dialogue_result = dialogue_tool.invoke({"query": query})
            
            result = f"--- Document Results ---\n{doc_result}\n\n--- Dialogue Log Results ---\n{dialogue_result}"
        else:
            result = f"--- Document Results ---\n{doc_result}"
        
    tool_message = f"---\nTool Result for query '{query}':\n{result}\n---\nPlease decide your next action (search or answer)."
    
    # Update search queries list
    queries = state.get("search_queries", []) + [query]
    
    return {
        "messages": [HumanMessage(content=tool_message, name="tool_node")],
        "search_queries": queries
    }
