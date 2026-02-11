# -*- coding: utf-8 -*-

"""
@Date : 2026-02-09
@Author : xiezizhe
"""
import json
import os
from typing import List

import json_repair
import pandas as pd
from csc_ai_agent.llm.schema import Message, USER, ASSISTANT, FUNCTION, FunctionCall

from csc_ai_deep_mining.schema import Document

from csc_ai_deep_mining.utils.data_io import read_word_files_to_markdown

# Point to the 'logs' directory as per usage description
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
# Point to the 'docs' directory
DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs')


def read_chat_dialogue() -> List[List[Message]]:
    """
    Read chat dialogues from the Excel file and convert them into a list of message lists.
    
    Optimized to structure tool calls (getSellerPunish) in ChatML format:
    - Assistant: Function Call
    - Function: Tool Output
    - Assistant/User: Text content

    Returns:
        List[List[Message]]: A list where each element is a list of Message objects representing a dialogue session.
    """
    filepath = os.path.join(DATA, 'output_dialogue_robustV2.xlsx')
    if not os.path.exists(filepath):
        print(f"Warning: File not found at {filepath}")
        return []

    df = pd.read_excel(filepath)
    dialogues: List[List[Message]] = []

    if '备注' not in df.columns or 'processed_content' not in df.columns:
        return []

    for d_str in df[df['备注'] == '处理成功']['processed_content']:
        try:
            content_list = json.loads(json_repair.repair_json(d_str))
            # Sort by create_time
            dialogue_obj = sorted(content_list, key=lambda x: x.get('create_time', 0))

            messages: List[Message] = []
            for d_item in dialogue_obj:
                role = USER if d_item.get('sender') == '用户' else ASSISTANT
                text = d_item.get('text', '')
                features = d_item.get('features')

                if features:
                    # Construct FunctionCall
                    fc = FunctionCall(name='getSellerPunish', arguments='{}')
                    fc_msg = Message(role=ASSISTANT, content='', function_call=fc)

                    # Construct Tool Output
                    tool_content = json.dumps(features, ensure_ascii=False)
                    tool_msg = Message(role=FUNCTION, name='getSellerPunish', content=tool_content)

                    if role == ASSISTANT:
                        # Logic: Assistant called tool -> got result -> generated text
                        messages.append(fc_msg)
                        messages.append(tool_msg)
                        messages.append(Message(role=role, content=text))
                    else:
                        # Logic: Context indicates tool was used around User turn (less common, implies system pre-fetch)
                        messages.append(Message(role=role, content=text))
                        messages.append(fc_msg)
                        messages.append(tool_msg)
                else:
                    messages.append(Message(role=role, content=text))

            dialogues.append(messages)
        except Exception as e:
            print(f"Error parsing dialogue row: {e}")
            continue

    return dialogues


def read_docs() -> List[Document]:
    """
    Read all .docx files from the 'docs' directory and convert them to Document objects.

    Returns:
        List[Document]: A list of Document objects containing the Markdown content of the files.
    """
    if not os.path.exists(DOCS):
        print(f"Warning: Docs directory not found at {DOCS}")
        return []

    word_content_dict = read_word_files_to_markdown(DOCS)
    documents = []
    
    for filename, content in word_content_dict.items():
        doc = Document(
            content=content,
            source=os.path.join(DOCS, filename),
            metadata={"filename": filename}
        )
        documents.append(doc)
        
    return documents


if __name__ == '__main__':
    a = read_chat_dialogue()
    b = read_docs()
    print(len(a))
    print(len(b))
