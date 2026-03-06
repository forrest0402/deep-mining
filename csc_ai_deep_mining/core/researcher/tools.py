# -*- coding: utf-8 -*-
"""
@Date : 2026-03-04
@Author : xiezizhe
"""

import json
from typing import List, Optional
from langchain_core.tools import tool, StructuredTool
from csc_ai_deep_mining.schema.document import Document, DialogueLog
from csc_ai_deep_mining.rag.pageindex import DocumentPageIndex, DialogueLogPageIndex

def create_search_documents_tool(documents: List[Document]) -> StructuredTool:
    """
    Creates a Langchain Tool bound to a specific list of documents,
    allowing the Researcher to query them.

    This acts as a factory function to inject the document list into the tool's 
    closure so the LLM doesn't need to pass the documents themselves as arguments.

    Args:
        documents (List[Document]): The corpus of documents to search.

    Returns:
        StructuredTool: A Langchain tool configured with the LocalPageIndex backend,
            ready to be invoked by the LLM agent.
    """
    # Build the tree once for the provided documents
    page_index = DocumentPageIndex()
    page_index.build_index(documents)
    
    def search_documents(query: str) -> str:
        """
        Search the provided business documents (Policies, SOPs) for information relevant to the question.
        
        Args:
            query: The search query or keywords to look for.
            
        Returns:
            Text snippets from the documents that match the query.
        """
        return page_index.search(query)

    return StructuredTool.from_function(
        func=search_documents,
        name="search_documents",
        description="Search the provided business documents (Policies, SOPs) for information. Always use this tool to find evidence before answering.",
    )

def create_search_dialogue_log_by_pageindex_tool(dialogue_logs: List[DialogueLog]) -> StructuredTool:
    """
    Creates a Langchain Tool bound to a specific list of dialogue logs,
    allowing the Researcher to query them for real-world execution examples.

    Args:
        dialogue_logs (List[DialogueLog]): The dialogue transcripts.

    Returns:
        StructuredTool: A Langchain tool configured with the LocalPageIndex backend
            using the specific dialogue summary prompt.
    """
    # Convert DialogueLogs to standard Documents internally so PageIndex can structure the tree
    docs = [d.to_document() for d in dialogue_logs]
    
    # Build the tree using the specific dialogue summarization prompt
    page_index = DialogueLogPageIndex(summary_prompt_base_name="dialogue_summary")
    page_index.build_index(docs)
    
    def search_dialogues(query: str) -> str:
        """
        Search the provided customer service dialogue logs to understand how issues are handled
        in practice and to identify discrepancies or real-world evidence.
        
        Args:
            query: The search query or keywords to look for.
            
        Returns:
            Text snippets from the dialogues that match the query.
        """
        return page_index.search(query)

    return StructuredTool.from_function(
        func=search_dialogues,
        name="search_dialogue_logs",
        description="Search the provided customer service dialogue logs for historical handling examples, penalty status, and agent behaviors.",
    )
