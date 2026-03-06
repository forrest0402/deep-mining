# -*- coding: utf-8 -*-
"""
LLM utility functions for parsing and repairing JSON responses.
@Date : 2026-03-06
"""

import json
import logging
import re
import json_repair

logger = logging.getLogger(__name__)

def extract_json_from_llm(text: str) -> dict:
    """
    Extracts and parses JSON content from an LLM response string using json_repair.

    This function handles potential Markdown formatting (e.g., ```json ... ```)
    and uses json_repair to fix common structural errors in the LLM output.

    Args:
        text (str): The raw text response from the LLM.

    Returns:
        dict: A dictionary containing the parsed and repaired JSON data. 
            Returns an empty dict (or occasionally a list if the LLM output was a list) 
            wrapped in common cases if parsing fails after repair.
    """
    if not text:
        return {}

    text = text.strip()
    
    # Try to find JSON block in markdown
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if match:
        json_str = match.group(1).strip()
    else:
        # If no code block, look for the first '{' and last '}'
        # or first '[' and last ']'
        start_brace = text.find('{')
        start_bracket = text.find('[')
        
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            end_brace = text.rfind('}')
            if end_brace != -1:
                json_str = text[start_brace:end_brace+1]
            else:
                json_str = text[start_brace:]
        elif start_bracket != -1:
            end_bracket = text.rfind(']')
            if end_bracket != -1:
                json_str = text[start_bracket:end_bracket+1]
            else:
                json_str = text[start_bracket:]
        else:
            json_str = text

    try:
        # Use json_repair to fix structural issues
        repaired_json = json_repair.repair_json(json_str)
        # repair_json returns a string that should be valid JSON
        # json_repair.loads() could also be used directly if version allows,
        # but the common pattern in this project seems to be repairing then loading.
        
        # NOTE: json_repair newer versions have loads() which is even better
        # Let's try to use json_repair.loads for convenience and better handling of types
        return json_repair.loads(json_str)
    except Exception as e:
        # Fallback to standard json if repair fails or results in something weird
        try:
            return json.loads(json_str)
        except Exception:
            logger.error(f"Failed to parse and repair JSON from LLM: {e}\nRaw fragment candidate: {json_str[:200]}...")
            return {}
