# -*- coding: utf-8 -*-
"""
@Date : 2026-03-05
@Author : xiezizhe
"""

import json
import logging
import os
from typing import List
import concurrent.futures

from csc_ai_deep_mining.schema.document import Document
from csc_ai_deep_mining.schema.evidence import ResearchResult
from csc_ai_deep_mining.schema.synthesis import SynthesisResult
from csc_ai_deep_mining.schema.sop import SOPGraph, SOPNode, SOPEdge
from csc_ai_deep_mining.schema.skill import AtomicSkill
from csc_ai_deep_mining.rag.pageindex import DocumentPageIndex
from csc_ai_deep_mining.utils.llm import extract_json_from_llm

logger = logging.getLogger(__name__)

class AnalystAgent:
    """
    Phase III Agent of DeepMining.
    Responsible for taking a set of ResearchResults (from Phase II) and 
    Normative Documents to synthesize a global SOP Graph and Atomic Skills.
    """
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        language = os.getenv("LANGUAGE", "zh_CN")
        suffix = "_zh_CN" if language == "zh_CN" else ""
        
        base_dir = os.path.dirname(__file__)
        def load_prompt(name):
            path = os.path.join(base_dir, f"../../prompts/{name}{suffix}.md")
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
                
        self.sop_builder_prompt = load_prompt("analyst_sop_builder")
        self.skill_identifier_prompt = load_prompt("analyst_skill_identifier")
        self.skill_writer_prompt = load_prompt("analyst_skill_writer")

    def _format_docs(self, docs: List[Document]) -> str:
        formatted = []
        for i, doc in enumerate(docs):
            source = getattr(doc, 'source', f'Document {i+1}')
            content = getattr(doc, 'content', '')
            formatted.append(f"--- Document Source: {source} ---\n{content}")
        return "\n\n".join(formatted)

    def _format_research_results(self, results: List[ResearchResult]) -> str:
        formatted = []
        for i, res in enumerate(results):
            rq = res.research_question
            block = [
                f"--- Research Result {i+1} ---",
                f"Intent: {rq.user_intent}",
                f"Question: {rq.question_text}",
                f"SOP Baseline (理论要求): {res.sop_baseline}",
                f"Observed Reality (实际情况): {res.observed_patterns}",
                f"Anomalies (异常与冲突): {res.identified_anomalies}",
                f"Conclusion: {res.conclusion}",
                "Tools Used in Reality:"
            ]
            
            if res.tool_usages:
                for tu in res.tool_usages:
                    block.append(f"  - Tool: {tu.tool_name} | Args: {tu.input_args}")
            else:
                block.append("  - None observed")
                
            formatted.append("\n".join(block))
            
        return "\n\n".join(formatted)

    def _extract_json_from_llm(self, response_text: str) -> dict:
        """Helper to cleanly extract and parse JSON from an LLM response."""
        return extract_json_from_llm(response_text)

    def _build_sop_graph(self, docs_text: str, results_text: str) -> SOPGraph:
        """Stage 1: Build the highly complex SOP routing graph from documents and anomaly constraints."""
        logger.info("Stage 1: Building Global SOP Graph via LLM...")
        prompt = self.sop_builder_prompt
        prompt = prompt.replace("{{ documents_text }}", docs_text)
        prompt = prompt.replace("{{ research_results_text }}", results_text)
        
        response_msgs = self.llm_service(prompt)
        if not response_msgs:
            raise ValueError("SOP Graph synthesis failed: LLM returned empty response")
            
        parsed_data = self._extract_json_from_llm(response_msgs[0].content)
        if not parsed_data:
            return SOPGraph(scenario_name="Failed Synthesis", nodes=[], edges=[])
            
        nodes = [SOPNode(**n) for n in parsed_data.get("nodes", [])]
        edges = [SOPEdge(**e) for e in parsed_data.get("edges", [])]
        return SOPGraph(
            scenario_name=parsed_data.get("scenario_name", "Global SOP"),
            nodes=nodes,
            edges=edges
        )

    def _identify_skills(self, sop_graph: SOPGraph, docs_text: str, results_text: str) -> List[dict]:
        """Stage 2: Audit the complete SOP and research context to identify functional gaps requiring skills."""
        logger.info("Stage 2: Identifying Required Skills based on SOP Context...")
        prompt = self.skill_identifier_prompt
        prompt = prompt.replace("{{ sop_graph_json }}", sop_graph.model_dump_json(indent=2))
        prompt = prompt.replace("{{ documents_text }}", docs_text)
        prompt = prompt.replace("{{ research_results_text }}", results_text)
        
        response_msgs = self.llm_service(prompt)
        if not response_msgs:
            logger.warning("Skill Identifier returned empty. Proceeding with 0 skills.")
            return []
            
        parsed_data = self._extract_json_from_llm(response_msgs[0].content)
        return parsed_data if isinstance(parsed_data, list) else []

    def _write_deep_skills(self, identified_skills: List[dict], sop_graph: SOPGraph, docs_text: str, results_text: str) -> List[AtomicSkill]:
        """Stage 3: Launch parallel LLM inference for each identified skill to write massive, detailed guidelines."""
        logger.info(f"Stage 3: Deep Writing {len(identified_skills)} Independent Skills (Concurrent: 5)...")
        deep_skills = []
        
        def _process_single_skill(skill_meta: dict) -> AtomicSkill:
            logger.info(f"  -> Writing Deep Skill: {skill_meta.get('name')}")
            prompt = self.skill_writer_prompt
            prompt = prompt.replace("{{ target_skill_name }}", skill_meta.get("name", "unknown"))
            prompt = prompt.replace("{{ target_skill_desc }}", skill_meta.get("description", ""))
            prompt = prompt.replace("{{ target_skill_tools }}", json.dumps(skill_meta.get("required_tools", [])))
            prompt = prompt.replace("{{ sop_graph_json }}", sop_graph.model_dump_json(indent=2))
            prompt = prompt.replace("{{ documents_text }}", docs_text)
            prompt = prompt.replace("{{ research_results_text }}", results_text)
            
            response_msgs = self.llm_service(prompt)
            if not response_msgs:
                logger.error(f"Failed to generate deep skill for {skill_meta.get('name')}")
                return None
                
            parsed_data = self._extract_json_from_llm(response_msgs[0].content)
            if parsed_data:
                try:
                    return AtomicSkill(**parsed_data)
                except Exception as e:
                    logger.error(f"Failed to parse AtomicSkill Pydantic Model for {skill_meta.get('name')}: {e}")
            return None

        from csc_ai_deep_mining.config import config
        workers = config.analyst_skill_workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_skill = {
                executor.submit(_process_single_skill, sm): sm 
                for sm in identified_skills
            }
            
            for future in concurrent.futures.as_completed(future_to_skill):
                result = future.result()
                if result:
                    deep_skills.append(result)
                    
        return deep_skills

    def synthesize(self, research_results: List[ResearchResult], docs: List[Document]) -> SynthesisResult:
        """
        Executes Phase III synthesis via a comprehensive 3-stage LLM pipeline.

        Args:
            research_results: List of findings from Phase II.
            docs: The full corpus of normative policy documents.

        Returns:
            SynthesisResult: Contains the globally synthesized SOPGraph and Deep AtomicSkills.
        """
        logger.info(f"Starting Knowledge Synthesis with {len(research_results)} research results and {len(docs)} documents.")
        
        # Use PageIndex to extract structured SOP knowledge instead of dumping raw texts
        logger.info("Building/loading Document PageIndex to prevent context explosion...")
        page_index = DocumentPageIndex()
        page_index.build_index(docs)
        
        # Query for core guidelines
        language = os.getenv("LANGUAGE", "zh_CN")
        if language == "zh_CN":
            query = "客服领域详细的标准操作规范（SOP）、政策规章、判罚或赔付规则、分步操作指南，以及应对常见异常场景的客服沟通话术和安抚策略有哪些？"
        else:
            query = "What are the detailed standard operating procedures, policies, penalty rules, step-by-step instructions, and handling scripts for customer service topics?"
            
        docs_text = page_index.search(query)
        results_text = self._format_research_results(research_results)
        
        # --- Stage 1: Build SOP Graph ---
        sop_graph = self._build_sop_graph(docs_text, results_text)
        
        # --- Stage 2: Identify Skills ---
        identified_skills_meta = self._identify_skills(sop_graph, docs_text, results_text)
        
        # --- Stage 3: Deep Write Skills ---
        deep_skills = self._write_deep_skills(identified_skills_meta, sop_graph, docs_text, results_text)
        
        # --- Stage 4: Assembly ---
        return SynthesisResult(
            sop_graph=sop_graph,
            skills=deep_skills
        )
