# -*- coding: utf-8 -*-

"""
DeepMiner: The core entry point for the agentic knowledge mining framework.
@Date : 2026-03-05
@Author : xiezizhe
"""

import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Tuple, List
from tqdm import tqdm

from csc_ai_deep_mining.schema.document import Document, DialogueLog
from csc_ai_deep_mining.schema.research_question import ResearchQuestion
from csc_ai_deep_mining.schema.evidence import ResearchResult
from csc_ai_deep_mining.schema.synthesis import SynthesisResult
from csc_ai_deep_mining.schema.sop import SOPGraph
from csc_ai_deep_mining.schema.skill import AtomicSkill

from csc_ai_deep_mining.config import config
from csc_ai_deep_mining.llm import LLMModelService
from csc_ai_deep_mining.core.planner.planner_agent import PlannerAgent
from csc_ai_deep_mining.core.researcher.researcher_agent import ResearcherAgent
from csc_ai_deep_mining.core.analyst.analyst_agent import AnalystAgent
from csc_ai_deep_mining.utils.data_io import read_word_files_to_markdown

logger = logging.getLogger(__name__)

class DeepMiner:
    """
    The main orchestrator for the DeepMining framework.

    This class manages the entire pipeline of hypothesis generation, evidence acquisition,
    knowledge synthesis, and result export. It coordinates the interactions between
    the Planner, Researcher, and Analyst agents.
    """

    def __init__(self, scenario: str, docs_path: str, logs_path: str):
        """
        Initialize the DeepMiner instance.

        Args:
            scenario (str): The name of the business scenario (e.g., "Fresh Fruit Refund").
            docs_path (str): Local file path to normative documents.
            logs_path (str): Local file path to historical dialogue logs.
        """
        self.scenario = scenario
        self.docs_path = docs_path
        self.logs_path = logs_path
        
        # Internal State
        self.docs_data: List[Document] = []
        self.logs_data: List[DialogueLog] = []
        
        self.research_questions: List[ResearchQuestion] = []
        self.evidence_bank: List[ResearchResult] = []
        self.synthesis_result: SynthesisResult = None
        
        # Load Defaults
        self._load_docs()
        self._load_logs()
        
        # Initialize Core Components
        self.llm_service = LLMModelService()
        self.planner = PlannerAgent(llm_service=self.llm_service)
        # Researcher initializes its own LLM interactions or tools as needed
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent(llm_service=self.llm_service)

    def _load_docs(self):
        """Loads documents from Docs path into memory."""
        if not os.path.exists(self.docs_path):
            logger.warning(f"Docs path {self.docs_path} does not exist.")
            return

        logger.info(f"Loading generic documentation from {self.docs_path}...")
        word_content_dict = read_word_files_to_markdown(self.docs_path)
        for filename, content in word_content_dict.items():
            doc = Document(
                name=filename,
                content=content,
                source=os.path.join(self.docs_path, filename),
                metadata={"filename": filename}
            )
            self.docs_data.append(doc)
            
    def _load_logs(self):
        """Loads simple JSON dialogue logs from logs_path into memory."""
        if not os.path.exists(self.logs_path):
            logger.warning(f"Logs path {self.logs_path} does not exist.")
            return
            
        logger.info(f"Scanning for JSON dialogue logs in {self.logs_path}...")
        if os.path.isdir(self.logs_path):
            for filename in os.listdir(self.logs_path):
                if filename.endswith(".json"):
                    try:
                        filepath = os.path.join(self.logs_path, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for item in data:
                                    self.logs_data.append(DialogueLog(**item))
                            else:
                                self.logs_data.append(DialogueLog(**data))
                    except Exception as e:
                        logger.warning(f"Failed to load dialogue log {filename}: {e}")

    def decompose_scenario(self, scenario: str = None, dialogues: List[DialogueLog] = None, docs: List[Document] = None) -> List[ResearchQuestion]:
        """
        Phase I: Generate Research Questions for the scenario using the Planner agent.
        """
        scenario = scenario or self.scenario
        dialogues = dialogues if dialogues is not None else self.logs_data
        docs = docs if docs is not None else self.docs_data
        
        logger.info(f"\n[Phase I] Extracting intents and constraints for scenario: '{scenario}'")
        raw_dialogues = [d.messages for d in dialogues] if dialogues else []
        self.research_questions = self.planner.decompose_scenario(scenario, raw_dialogues, docs)
        logger.info(f"[Phase I] Successfully decomposed into {len(self.research_questions)} Research Questions.")
        return self.research_questions

    def research(self, research_questions: List[ResearchQuestion] = None) -> List[ResearchResult]:
        """
        Phase II: Conduct deep research to validate hypotheses using the Researcher agent.
        """
        r_questions = research_questions if research_questions is not None else self.research_questions
        logger.info(f"\n[Phase II] Initiating deep research across {len(r_questions)} questions...")
        
        self.evidence_bank = []
        
        def _process_rq(rq):
            return self.researcher.investigate(rq, self.docs_data, dialogue_logs=self.logs_data)

        workers = config.researcher_investigate_workers
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_process_rq, rq) for rq in r_questions]
            for future in tqdm(as_completed(futures), total=len(r_questions), desc="Investigating RQs"):
                try:
                    res = future.result()
                    self.evidence_bank.append(res)
                except Exception as e:
                    logger.error(f"Investigation failed for a question: {e}")
                    
        logger.info(f"[Phase II] Successfully gathered {len(self.evidence_bank)} evidence packages.")
        return self.evidence_bank

    def synthesize(self, evidence_bank: List[ResearchResult] = None, docs: List[Document] = None) -> Tuple[SOPGraph, List[AtomicSkill]]:
        """
        Phase III: Synthesize verified evidence into a structured knowledge graph and skills.
        """
        e_bank = evidence_bank if evidence_bank is not None else self.evidence_bank
        d_data = docs if docs is not None else self.docs_data
        
        logger.info(f"\n[Phase III] Synthesizing {len(e_bank)} findings into global SOP...")
        
        self.synthesis_result = self.analyst.synthesize(e_bank, d_data)
        
        return self.synthesis_result.sop_graph, self.synthesis_result.skills

    def export(self, format: str = "mermaid", output_dir: str = "./output"):
        """
        Export the mining results to the specified format and directory.
        """
        if not self.synthesis_result:
            logger.error("No synthesis result found to export. Run synthesize() first.")
            return
            
        logger.info(f"\n[Export] Generating files into {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        
        if format == "mermaid":
            mermaid_str = self.synthesis_result.sop_graph.to_mermaid()
            out_file = os.path.join(output_dir, "sop_graph.md")
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write("```mermaid\n")
                f.write(mermaid_str)
                f.write("\n```\n")
            logger.info(f"  -> Exported SOP Graph to {out_file}")
            
        skills_dir = os.path.join(output_dir, "skills")
        os.makedirs(skills_dir, exist_ok=True)
        
        for skill in self.synthesis_result.skills:
            skill.export_to_folder(skills_dir, self.docs_data)
            
        logger.info(f"  -> Exported {len(self.synthesis_result.skills)} Deep Skills to {skills_dir}")
