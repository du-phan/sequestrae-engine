import os
from pathlib import Path

from sequestrae_engine.document_parsing.parser import PDFToMarkdownParser


def parse_pdfs_command(api_key, project_dir, limit=5):
    if limit is None:
        limit = 5
    print(f"Max number of files to process: {limit}")

    if not api_key:
        print("Error: LLAMA_API_KEY is required")
        return 1

    parser = PDFToMarkdownParser(api_key=api_key)
    project_path = Path(project_dir)

    if not project_path.exists():
        print(f"Error: Directory not found at {project_path}")
        return 1

    pdf_count = 0
    for folder_path in project_path.iterdir():
        if not folder_path.name.startswith(".") and folder_path.is_dir() and pdf_count < limit:
            for pdf_path in folder_path.glob("*.pdf"):
                if pdf_path.is_file() and "report" in pdf_path.stem.lower():
                    pdf_count += 1
                    parser.parse_pdf(pdf_path)

    print(f"Successfully processed {pdf_count} PDF files")
    return 0
