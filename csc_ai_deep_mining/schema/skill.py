# -*- coding: utf-8 -*-
"""
@Date : 2026-03-05
@Author : xiezizhe
"""

import os
import yaml
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .document import Document

class ScriptFile(BaseModel):
    filename: str = Field(..., description="The name of the script file, e.g. execute_tool.py")
    content: str = Field(..., description="The actual code content of the script")

class ReferenceFile(BaseModel):
    filename: str = Field(..., description="The mapped filename for the reference, e.g. refund_policy_v1.pdf")
    content: str = Field(..., description="The actual extracted policy content or schema instructions")

class AtomicSkill(BaseModel):
    """
    Represents a specific, actionable LLM skill generated from traversing the SOP Graph.
    This corresponds to the atomic abilities attached to action nodes or dialogue blocks.
    Adheres strictly to the docs/skill-creator progressive disclosure pattern.
    """
    name: str = Field(..., description="The highly specific name of the skill, usually kebab-case (e.g., interpret-penalty-rules)")
    description: str = Field(..., description="This is the primary triggering mechanism. Must include both what the skill does AND specific triggers/contexts for when to use it.")
    skill_body: str = Field(..., description="The concise Markdown body of SKILL.md. Contains high level workflow and references pointing to other files.")
    scripts: List[ScriptFile] = Field(default_factory=list, description="Executable code scripts to be placed in the scripts/ folder.")
    references: List[ReferenceFile] = Field(default_factory=list, description="Detailed external documentation to be placed in the references/ folder.")

    def export_to_folder(self, base_dir: str, docs: List[Document] = None):
        """
        Exports the skill to a Claude-compatible skill folder structure:
        - SKILL.md
        - scripts/
        - references/
        - assets/
        """
        skill_dir = os.path.join(base_dir, self.name)
        
        # Create directories
        os.makedirs(skill_dir, exist_ok=True)
        os.makedirs(os.path.join(skill_dir, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(skill_dir, "references"), exist_ok=True)
        os.makedirs(os.path.join(skill_dir, "assets"), exist_ok=True)
        
        # 1. Write SKILL.md with strict YAML frontmatter
        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        frontmatter = {
            "name": self.name,
            "description": self.description
        }
        
        with open(skill_md_path, 'w', encoding='utf-8') as f:
            f.write("---\n")
            yaml.dump(frontmatter, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            f.write("---\n\n")
            f.write(self.skill_body)
            
        # 2. Write Scripts
        for script in self.scripts:
            script_path = os.path.join(skill_dir, "scripts", script.filename)
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script.content)
                
        # 3. Write References
        for ref in self.references:
            ref_path = os.path.join(skill_dir, "references", ref.filename)
            with open(ref_path, 'w', encoding='utf-8') as f:
                f.write(ref.content)

