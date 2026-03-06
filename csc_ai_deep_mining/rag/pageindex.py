# -*- coding: utf-8 -*-
"""
@Date : 2026-03-04
@Author : xiezizhe
"""

import re
import json
import uuid
import logging
import os
import hashlib
from typing import List, Dict, Any, Tuple
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from csc_ai_deep_mining.schema.document import Document
from csc_ai_deep_mining.llm import LLMModelService
from csc_ai_deep_mining.config import config
from csc_ai_deep_mining.utils.llm import extract_json_from_llm

logger = logging.getLogger(__name__)

def extract_nodes_from_markdown(markdown_content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Extracts headers and their line numbers from a Markdown document.

    This function parses the provided Markdown content line by line, identifying
    headers (e.g., # Header, ## Subheader) and recording their line positions.
    It properly ignores headers that are encapsulated within Markdown code blocks.

    Args:
        markdown_content (str): The full content of the Markdown document.

    Returns:
        Tuple[List[Dict[str, Any]], List[str]]: A tuple containing a list of dictionaries,
            where each dictionary represents a header node with its title and line number,
            and a list of all lines in the document.
    """
    header_pattern = r'^(#{1,6})\s+(.+)$'
    code_block_pattern = r'^```'
    node_list = []
    
    lines = markdown_content.split('\n')
    in_code_block = False
    
    for line_num, line in enumerate(lines, 1):
        stripped_line = line.strip()
        if re.match(code_block_pattern, stripped_line):
            in_code_block = not in_code_block
            continue
        if not stripped_line:
            continue
            
        if not in_code_block:
            match = re.match(header_pattern, stripped_line)
            if match:
                title = match.group(2).strip()
                node_list.append({'node_title': title, 'line_num': line_num})

    return node_list, lines

def extract_node_text_content(node_list: List[Dict[str, Any]], markdown_lines: List[str]) -> List[Dict[str, Any]]:
    """
    Extracts the text content associated with each header node.

    This function takes the list of header nodes and the raw Markdown lines,
    then assigns the corresponding text block to each node. The text block for a 
    given node spans from its header line down to the line just before the next header.

    Args:
        node_list (List[Dict[str, Any]]): The list of header nodes extracted previously.
        markdown_lines (List[str]): The list of raw lines from the Markdown document.

    Returns:
        List[Dict[str, Any]]: The enhanced list of nodes, each now containing
            its associated 'text' content and hierarchy 'level'.
    """    
    all_nodes = []
    for node in node_list:
        line_content = markdown_lines[node['line_num'] - 1]
        header_match = re.match(r'^(#{1,6})', line_content)
        
        if header_match is None:
            continue
            
        processed_node = {
            'title': node['node_title'],
            'line_num': node['line_num'],
            'level': len(header_match.group(1))
        }
        all_nodes.append(processed_node)
    
    for i, node in enumerate(all_nodes):
        start_line = node['line_num'] - 1 
        if i + 1 < len(all_nodes):
            end_line = all_nodes[i + 1]['line_num'] - 1 
        else:
            end_line = len(markdown_lines)
        
        node['text'] = '\n'.join(markdown_lines[start_line:end_line]).strip()    
    return all_nodes

def build_tree_from_nodes(node_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Builds a hierarchical tree structure from a flat list of header nodes.

    This function uses the header levels of the nodes to establish parent-child
    relationships, converting the flat list into a nested tree format suitable
    for structured retrieval and reasoning.

    Args:
        node_list (List[Dict[str, Any]]): A list of nodes, each with a title,
            text content, line number, and header level.

    Returns:
        List[Dict[str, Any]]: A list of root nodes, where each node may contain
            a 'nodes' list representing its children in the document hierarchy.
    """
    if not node_list:
        return []
    
    stack = []
    root_nodes = []
    
    for node in node_list:
        current_level = node['level']
        
        tree_node = {
            'title': node['title'],
            'node_id': str(uuid.uuid4())[:8],
            'text': node['text'],
            'line_num': node['line_num'],
            'nodes': []
        }
        
        while stack and stack[-1][1] >= current_level:
            stack.pop()
        
        if not stack:
            root_nodes.append(tree_node)
        else:
            parent_node, parent_level = stack[-1]
            parent_node['nodes'].append(tree_node)
        
        stack.append((tree_node, current_level))
    
    return root_nodes

class BasePageIndex(ABC):
    """
    A base implementation of PageIndex for Reasoning-based RAG.
    Instead of vector DBs, it builds a hierarchical tree of the document,
    and uses LLM reasoning to identify relevant sections.
    """
    
    def __init__(self, summary_prompt_base_name: str = "pageindex_summary", search_prompt_base_name: str = "pageindex_search"):
        """
        Initializes the BasePageIndex.

        Sets up the LLM service connection and initializes dictionaries
        for storing the document trees and a flat node mapping for quick access.
        Loads the reasoning prompt template based on the LANGUAGE environment variable.
        """
        self.llm = LLMModelService()
        self.doc_trees = {} # doc_id -> tree details mapping
        self.node_mapping = {} # node_id -> node obj dictionary
        
        # Load localized prompt
        language = config.language
        prompt_filename = f"{search_prompt_base_name}_{language}.md" if language == "zh_CN" else f"{search_prompt_base_name}.md"
        prompt_path = os.path.join(
            os.path.dirname(__file__), 
            "../prompts", 
            prompt_filename
        )
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.search_prompt_template = f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found at {prompt_path}. Using fallback English prompt.")
            self.search_prompt_template = """
You are a reasoning-based retrieval assistant. You are given a question and a tree structure of a document collection.
Each node contains a node_id, title, and a corresponding summary.
Your task is to find all nodes that are likely to contain the answer to the question.

Question: {{ query }}

Document tree structure:
{{ document_tree }}

Please reply in the following JSON format:
{
    "thinking": "<Your thinking process on which nodes are relevant to the question>",
    "node_list": ["node_id_1", "node_id_2"]
}
Directly return the final JSON structure. Do not output anything else.
"""

        # Load localized summary prompt
        summary_prompt_filename = f"{summary_prompt_base_name}_{language}.md" if language == "zh_CN" else f"{summary_prompt_base_name}.md"
        summary_prompt_path = os.path.join(
            os.path.dirname(__file__), 
            "../prompts", 
            summary_prompt_filename
        )
        
        try:
            with open(summary_prompt_path, 'r', encoding='utf-8') as f:
                self.summary_prompt_template = f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found at {summary_prompt_path}. Using fallback English prompt.")
            self.summary_prompt_template = "Please provide a one-sentence summary for the following text:\n\n{{ node_text }}"
        
    def _generate_node_summary(self, node_text: str) -> str:
        """
        Calls the LLM to generate a very brief summary of the node text.

        Args:
            node_text (str): The full text content of the node.

        Returns:
            str: A one-sentence summary of the provided text.
        """
        # Simple threshold, if text is short, no need to summarize
        if len(node_text) < 200:
            return node_text[:200]
            
        prompt = self.summary_prompt_template.replace("{{ node_text }}", node_text[:2000])
        try:
            resp = self.llm(prompt)
            return resp[0].content.strip()
        except Exception as e:
            logger.error(f"Failed to summarize node: {e}")
            return "Summary unavailable."

    def _traverse_and_summarize(self, nodes: List[Dict[str, Any]]):
        """
        Recursively traverses the tree structure and generates summaries for each node.

        Populates the node object with a 'summary' key and adds it to the internal
        flat tracking dictionary `node_mapping` for efficient retrieval later.

        Args:
            nodes (List[Dict[str, Any]]): The list of tree nodes to traverse.
        """
        for node in nodes:
            node['summary'] = self._generate_node_summary(node['text'])
            self.node_mapping[node['node_id']] = node
            if node.get('nodes'):
                self._traverse_and_summarize(node['nodes'])

    @abstractmethod
    def _build_doc_tree(self, doc: Document) -> List[Dict[str, Any]]:
        """
        Abstract method to build the hierarchy tree from a specific document format.

        Args:
            doc (Document): The document object to process.

        Returns:
            List[Dict[str, Any]]: The parsed document represented as an ordered hierarchical tree.
        """
        pass

    def build_index(self, documents: List[Document], use_local_cache: bool = True):
        """
        Builds the complete hierarchical document tree and generates reasoning summaries.

        This is the primary ingestion method that processes a list of Documents,
        extracts their headers and text, builds a tree, and uses the LLM to summarize
        each section for the reasoning step. Extends support for local caching to skip
        heavy inference on unchanging documents.

        Args:
            documents (List[Document]): The list of Document objects to index.
            use_local_cache (bool): Whether to retrieve/store page indices to disk.
        """
        logger.info(f"Building PageIndex tree for {len(documents)} documents.")
        
        def process_doc(doc: Document):
            if not doc.content:
                logger.warning(f"Document {doc.doc_id} has no content.")
                return
                
            hash_md5 = hashlib.md5()
            hash_md5.update(doc.content.encode('utf-8'))
            doc_hash = hash_md5.hexdigest()
            
            doc_name = doc.name or doc.metadata.get('filename', 'unknown_doc')
            cache_key = f"{doc_name}_{doc_hash}.json"
            cache_dir = os.path.join(os.getcwd(), config.page_index_cache_dir)
            cache_path = os.path.join(cache_dir, cache_key)
            
            if use_local_cache and os.path.exists(cache_path):
                logger.info(f"Loading cached PageIndex for {doc_name}")
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cached_tree = json.load(f)
                    self.doc_trees[doc.doc_id] = {
                        "source": doc.source,
                        "tree": cached_tree
                    }
                    # Recursively populate node_mapping from the loaded tree structure
                    def populate_mapping(nodes):
                        for node in nodes:
                            self.node_mapping[node['node_id']] = node
                            if node.get('nodes'):
                                populate_mapping(node['nodes'])
                    
                    populate_mapping(cached_tree)
                    return # Skip the resource-heavy LLM build process
                except Exception as e:
                    logger.warning(f"Failed to load cache for {doc_name}: {e}. Rebuilding...")

            try:
                tree = self._build_doc_tree(doc)
            except Exception as e:
                logger.error(f"Failed to build tree for {doc_name}: {e}. Falling back to single node.")
                tree = [{
                    'title': doc_name,
                    'node_id': str(uuid.uuid4())[:8],
                    'text': doc.content[:10000], 
                    'summary': 'Fallback flat extraction',
                    'line_num': 1,
                    'nodes': []
                }]
                self.node_mapping[tree[0]['node_id']] = tree[0]
                
            self.doc_trees[doc.doc_id] = {
                "source": doc.source,
                "tree": tree
            }
            
            if use_local_cache:
                try:
                    os.makedirs(cache_dir, exist_ok=True)
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(tree, f, ensure_ascii=False, indent=2)
                    logger.info(f"Saved PageIndex cache for {doc_name} to {cache_path}")
                except Exception as e:
                    logger.warning(f"Failed to save cache for {doc_name}: {e}")

        # Execute indexing workload in parallel
        with ThreadPoolExecutor(max_workers=config.page_index_workers) as executor:
            futures = [executor.submit(process_doc, doc) for doc in documents]
            for future in tqdm(as_completed(futures), total=len(documents), desc="Building PageIndex"):
                try:
                    future.result()
                except Exception as exc:
                    logger.error(f"Document parsing generated an exception during multiprocessing: {exc}")
                
        logger.info("PageIndex tree build complete.")
        
    def _create_simplified_tree(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Strips full text from the tree to minimize context window usage during LLM reasoning.

        Args:
            nodes (List[Dict[str, Any]]): The full tree nodes.

        Returns:
            List[Dict[str, Any]]: A simplified tree structure containing only
                node IDs, titles, and summaries.
        """
        simplified = []
        for node in nodes:
            simple_node = {
                'node_id': node['node_id'],
                'title': node['title'],
                'summary': node['summary']
            }
            if node.get('nodes'):
                simple_node['nodes'] = self._create_simplified_tree(node['nodes'])
            simplified.append(simple_node)
        return simplified

    def search(self, query: str) -> str:
        """
        Performs a reasoning-based search over the indexed document trees.

        Submits the simplified tree structure (with summaries) to the LLM
        alongside the user's query. The LLM then reasons about which nodes
        likely contain the required information and returns their IDs.
        The full text for those selected nodes is then retrieved and returned.

        Args:
            query (str): The search query or question to answer.

        Returns:
            str: The concatenated full text content of the relevant document sections.
        """
        if not self.doc_trees:
            return "Error: Index is empty."
            
        full_simplified_tree = []
        for doc_id, doc_data in self.doc_trees.items():
            full_simplified_tree.append({
                "document": doc_data["source"],
                "tree": self._create_simplified_tree(doc_data["tree"])
            })
            
        search_prompt = self.search_prompt_template.replace("{{ query }}", query)
        search_prompt = search_prompt.replace("{{ document_tree }}", json.dumps(full_simplified_tree, indent=2, ensure_ascii=False))
        
        try:
            resp = self.llm(search_prompt)
            result_text = resp[0].content.strip()
            
            # parse json
            parsed = extract_json_from_llm(result_text)
            if not parsed:
                return "PageIndex could not identify any relevant sections for this query."
            
            node_ids = parsed.get("node_list", [])
            if not node_ids:
                return "PageIndex could not identify any relevant sections for this query."
                
            retrieved_content = []
            for nid in node_ids:
                if nid in self.node_mapping:
                    node = self.node_mapping[nid]
                    retrieved_content.append(f"--- [Section: {node['title']}] ---\n{node['text']}\n")
                    
            if not retrieved_content:
                return "The identified node IDs were not valid."
                
            return "\n".join(retrieved_content)
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return "Error during PageIndex reasoning search."

class DocumentPageIndex(BasePageIndex):
    """
    Subclass of BasePageIndex restricted to formatting and building trees 
    from Markdown Document objects.
    """
    def _build_doc_tree(self, doc: Document) -> List[Dict[str, Any]]:
        node_list, lines = extract_nodes_from_markdown(doc.content)
        if not node_list:
            # Fallback if no markdown headers: create a single root node
            tree = [{
                'title': doc.name or 'unknown_doc',
                'node_id': str(uuid.uuid4())[:8],
                'text': doc.content[:10000],  # safety cutoff
                'line_num': 1,
                'nodes': []
            }]
        else:
            nodes_with_content = extract_node_text_content(node_list, lines)
            tree = build_tree_from_nodes(nodes_with_content)
        
        # Add summaries to standard document trees
        self._traverse_and_summarize(tree)
        return tree

class DialogueLogPageIndex(BasePageIndex):
    """
    Subclass of BasePageIndex restricted to formatting and reasoning over
    customer service dialogue logs using LLM-aided slicing.
    """
    def __init__(self, summary_prompt_base_name: str = "dialogue_summary", search_prompt_base_name: str = "pageindex_search"):
        super().__init__(summary_prompt_base_name, search_prompt_base_name)
        
        # Load localized dialogue chunking prompt
        language = config.language
        chunking_prompt_filename = f"dialogue_chunking_{language}.md" if language == "zh_CN" else "dialogue_chunking.md"
        chunking_prompt_path = os.path.join(
            os.path.dirname(__file__), 
            "../prompts", 
            chunking_prompt_filename
        )
        
        try:
            with open(chunking_prompt_path, 'r', encoding='utf-8') as f:
                self.chunking_prompt_template = f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found at {chunking_prompt_path}. Using fallback English prompt.")
            self.chunking_prompt_template = "Return a JSON array of conversational slices:\n\n{{ dialogue_history }}"

    def _build_doc_tree(self, doc: Document) -> List[Dict[str, Any]]:
        # Use LLM-based chunking for dialogue logs to preserve semantic context
        doc_name = doc.name or doc.metadata.get('filename', 'unknown_doc')
        logger.info(f"Using LLM chunking for dialogue log {doc_name}")
        prompt = self.chunking_prompt_template.replace("{{ dialogue_history }}", doc.content[:28000])
        
        resp = self.llm(prompt)
        # Extract JSON array from LLM response
        resp_text = resp[0].content
        parsed_slices = extract_json_from_llm(resp_text)
        slices = parsed_slices if isinstance(parsed_slices, list) else []
        
        tree = []
        for s in slices:
            tree.append({
                'title': s.get('title', 'Unknown Slice'),
                'node_id': str(uuid.uuid4())[:8],
                'text': s.get('messages_text', ''),
                'summary': s.get('summary', ''),
                'line_num': 1,
                'nodes': []
            })
        
        # Store immediate mapping since we already built summaries within the chunking payload
        for node in tree:
            self.node_mapping[node['node_id']] = node
            
        return tree
