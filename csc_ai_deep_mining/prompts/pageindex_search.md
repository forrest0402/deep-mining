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
