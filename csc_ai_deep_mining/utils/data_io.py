# -*- coding: utf-8 -*-

"""
@Date : 2026-02-09
@Author : xiezizhe
"""
import os

from pathlib import Path
import mammoth


def read_word_files_to_markdown(directory_path: str) -> dict:
    """
    Recursively finds all .docx files in a directory, reads their content,
    converts it to Markdown, and returns a dictionary.

    Args:
        directory_path: The path to the root directory to search.

    Returns:
        A dictionary where keys are the file names (e.g., "report.docx")
        and values are the Markdown content of the files.
    """
    if not os.path.isdir(directory_path):
        print(f"Error: Directory not found at '{directory_path}'")
        return {}

    word_content_dict = {}

    # Use pathlib for a modern, object-oriented way to handle file paths.
    # .rglob('*.docx') recursively finds all files ending with .docx.
    # This is perfect for searching through subfolders.
    root_path = Path(directory_path)
    docx_files = list(root_path.rglob('*.docx'))

    print(f"Found {len(docx_files)} .docx file(s) to process.")

    for file_path in docx_files:
        file_name = file_path.name
        print(f"Processing: {file_name}...")

        try:
            # .docx files must be opened in binary read mode ("rb")
            with open(file_path, "rb") as docx_file:
                # The core conversion step using mammoth
                result = mammoth.convert_to_markdown(docx_file)

                # The result object contains the markdown string in its .value attribute
                markdown_content = result.value

                # Add the file name and its content to our dictionary
                word_content_dict[file_name] = markdown_content

                # The result object also contains any messages/warnings from the conversion
                if result.messages:
                    print(f"  -> Warnings for {file_name}: {result.messages}")

        except Exception as e:
            # This makes the script robust against corrupted or unreadable files
            print(f"  -> Could not process file: {file_name}. Error: {e}")

    return word_content_dict
