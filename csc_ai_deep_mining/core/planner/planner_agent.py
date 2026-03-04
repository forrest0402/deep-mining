# -*- coding: utf-8 -*-

"""
@Date : 2026-03-01
"""

import os
import json
from typing import Any, List, Dict
from csc_ai_deep_mining.schema.document import Document
from csc_ai_deep_mining.schema.research_question import ResearchQuestion
from csc_ai_agent.llm.schema import Message
from csc_ai_deep_mining.log import logger

class PlannerAgent:
    """
    The PlannerAgent is responsible for Phase I: Hypothesis Generation and Decomposition.
    It extracts user intents from empirical logs and pairs them with constraints extracted
    from normative documents to form complete Research Questions.
    """
    def __init__(self, llm_service: Any):
        self.llm_service = llm_service
        self.intent_prompt_path = os.path.join(os.path.dirname(__file__), '../../prompts/planner_intent_extraction_zh_CN.md')
        self.constraint_prompt_path = os.path.join(os.path.dirname(__file__), '../../prompts/planner_constraint_extraction_zh_CN.md')
        self.validator_prompt_path = os.path.join(os.path.dirname(__file__), '../../prompts/planner_rq_validator_zh_CN.md')
        
        # Caches for intent and constraint generation per scenario
        self._intent_cache: Dict[str, List[str]] = {}
        self._constraint_cache: Dict[str, Dict[str, List[str]]] = {}

    def extract_user_intent_from_dialogue_logs(self, dialogues: List[List[Message]]) -> List[str]:
        """Reads raw empirical logs and extracts distinct core user intents.

        Formats raw user-agent dialogues into a consistent string layout, substituting it
        into a predefined planner intent prompt. The LLM identifies and extracts the
        distinct core reasons for the user's interaction from these dialogues.

        Args:
            dialogues: A list of dialogue sessions. Each dialogue session is represented
                as a list of Message objects, capturing the interaction turns.

        Returns:
            List[str]: A deduplicated list of distinct core user intents extracted
                from the provided dialogue transcripts.
        """
        formatted_dialogues = []
        for i, dialogue in enumerate(dialogues):
            dialogue_lines = []
            for msg in dialogue:
                role = getattr(msg, 'role', 'unknown').upper()
                content = getattr(msg, 'content', '') or ''
                if getattr(msg, 'function_call', None):
                    content += f" [FunctionCall: {msg.function_call.name}]"
                dialogue_lines.append(f"{role}: {content}")
            formatted_dialogues.append(f"--- Dialogue {i+1} ---\n" + "\n".join(dialogue_lines))
        
        dialogues_str = "\n\n".join(formatted_dialogues)

        with open(self.intent_prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        prompt = prompt_template.replace('{{ dialogues }}', dialogues_str)
        
        response_msgs = self.llm_service(prompt)
        if not response_msgs:
            return []
            
        response_text = response_msgs[0].content
        intents = []
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                intents.append(line[2:].strip())
            elif line and line[0].isdigit() and '. ' in line[:5]:
                intents.append(line.split('. ', 1)[1].strip())
            elif line and not line.startswith('#'):
                # Avoid capturing headers or raw conversational text as intents if possible
                if len(line.split()) < 20:
                    intents.append(line)
        
        # Deduplicate while preserving order
        unique_intents = []
        for intent in intents:
            if intent not in unique_intents and intent:
                unique_intents.append(intent)
                
        return unique_intents

    def extract_constraints_from_docs(self, user_intents: List[str], docs: List[Document]) -> Dict[str, List[str]]:
        """Scans normative business documents to extract business rules and constraints.

        Cross-references the identified user intents with the actual business rules 
        documented in texts (e.g. policies and wikis) to extract specific constraints 
        that apply to those intents. It utilizes the LLM to parse and map these rules.

        Args:
            user_intents: A list of core user intents generated from the dialogue logs.
            docs: A list of normative Document objects containing business policies.

        Returns:
            Dict[str, List[str]]: A dictionary mapping each user intent to a list of 
                applicable constraints derived from the documents.
        """
        # Format user intents
        intents_str = "\n".join([f"- {intent}" for intent in user_intents])
        
        # Format documents
        formatted_docs = []
        for i, doc in enumerate(docs):
            source = getattr(doc, 'source', f'Document {i+1}')
            content = getattr(doc, 'content', '')
            formatted_docs.append(f"--- Source: {source} ---\n{content}")
        docs_str = "\n\n".join(formatted_docs)
        
        with open(self.constraint_prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
            
        prompt = prompt_template.replace('{{ user_intents }}', intents_str)
        prompt = prompt.replace('{{ documents }}', docs_str)
        
        response_msgs = self.llm_service(prompt)
        if not response_msgs:
            return {}
            
        response_text = response_msgs[0].content
        
        constraints_dict = {}
        current_intent = None
        
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('Intent:'):
                current_intent = line[len('Intent:'):].strip()
                if current_intent not in constraints_dict:
                    constraints_dict[current_intent] = []
            elif line.startswith('- ') or line.startswith('* '):
                if current_intent:
                    constraints_dict[current_intent].append(line[2:].strip())
                    
        return constraints_dict

    def decompose_scenario(self, scenario: str, dialogues: List[List[Message]], docs: List[Document], use_intent_cache: bool = True, use_constraint_cache: bool = True) -> List[ResearchQuestion]:
        """Decomposes the given scenario into valid Research Questions.

        Orchestrates Phase I of the deep mining process. It first extracts user intents 
        from dialogue logs, then extracts business constraints from business documents, 
        and finally combines them. The LLM validates these combinations to formulate 
        actionable Research Questions. Intent and constraint extractions can be locally
        cached to save redundant LLM calls across similar runs.

        Args:
            scenario: The high-level name or description of the scenario being mined.
            dialogues: The empirical dialogue logs represented as lists of Messages.
            docs: The normative business documents represented as Document objects.
            use_intent_cache: Flag indicating whether to use locally cached user intents.
            use_constraint_cache: Flag indicating whether to use locally cached constraints.

        Returns:
            List[ResearchQuestion]: A structured list of Research Questions, each 
                combining a specific user intent and its associated policy constraints.
        """
        # 1. Extract Intents
        if use_intent_cache and scenario in self._intent_cache:
            user_intents = self._intent_cache[scenario]
        else:
            user_intents = self.extract_user_intent_from_dialogue_logs(dialogues)
            self._intent_cache[scenario] = user_intents
            
        if not user_intents:
            return []
            
        # 2. Extract Constraints
        if use_constraint_cache and scenario in self._constraint_cache:
            constraints_dict = self._constraint_cache[scenario]
        else:
            constraints_dict = self.extract_constraints_from_docs(user_intents, docs)
            self._constraint_cache[scenario] = constraints_dict
            
        # 3. & 4. Combine and validate using validator prompt
        formatted_combinations = []
        for intent in user_intents:
            constraints = constraints_dict.get(intent, [])
            formatted_combinations.append(f"Intent: {intent}")
            if constraints:
                for c in constraints:
                    formatted_combinations.append(f"  - Constraint: {c}")
            else:
                formatted_combinations.append("  - No constraints")
        
        combinations_str = "\n".join(formatted_combinations)
        
        with open(self.validator_prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
            
        prompt = prompt_template.replace('{{ scenario }}', scenario)
        prompt = prompt.replace('{{ intents_and_constraints }}', combinations_str)
        
        response_msgs = self.llm_service(prompt)
        if not response_msgs:
            return []
            
        response_text = response_msgs[0].content
        
        # Try to parse JSON from the response
        try:
            # Clean up markdown formatting if the LLM wrapped it in ```json ... ```
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
                
            parsed_rqa = json.loads(json_str)
            
            research_questions = []
            for item in parsed_rqa:
                rq = ResearchQuestion(
                    user_intent=item.get("user_intent", "Unknown Intent"),
                    constraints=item.get("constraints", []),
                    question_text=item.get("question_text", "No question text provided")
                )
                research_questions.append(rq)
                
            return research_questions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse validator LLM output as JSON: {e}")
            return []
