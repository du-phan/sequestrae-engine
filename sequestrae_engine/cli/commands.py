import os
import time
from pathlib import Path

from sequestrae_engine.db.client import SupabaseClient
from sequestrae_engine.db.scripts.populate_audit_reports import populate_feedstock_evaluation_table
from sequestrae_engine.document_parsing.extractors import AuditReportExtractor
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


def extract_audit_information_command(api_key, project_dir, limit=100):
    if limit is None:
        limit = 100
    print(f"Max number of files to process: {limit}")

    if not api_key:
        print("Error: MISTRAL_API_KEY is required")
        return 1

    extractor = AuditReportExtractor(api_key=api_key)
    project_path = Path(project_dir)

    if not project_path.exists():
        print(f"Error: Directory not found at {project_path}")
        return 1

    markdown_count = 0
    for folder_path in project_path.iterdir():
        if not folder_path.name.startswith(".") and folder_path.is_dir() and markdown_count < limit:
            for md_path in folder_path.glob("*.md"):
                if md_path.is_file() and "report" in md_path.stem.lower():
                    markdown_count += 1
                    try:
                        extractor.parse_audit_report(audit_report_path=md_path)
                    except Exception as e:
                        print(f"Error processing {md_path}: {str(e)}")
                    time.sleep(1)  # Sleep for 1 second to avoid rate limiting

    print(f"Successfully processed {markdown_count} markdown files")
    return 0


def evaluate_feedstock_sustainability_command(api_key, project_dir, limit=100):
    if limit is None:
        limit = 100
    print(f"Max number of files to process: {limit}")

    if not api_key:
        print("Error: MISTRAL_API_KEY is required")
        return 1

    extractor = AuditReportExtractor(api_key=api_key)
    project_path = Path(project_dir)

    if not project_path.exists():
        print(f"Error: Directory not found at {project_path}")
        return 1

    markdown_count = 0
    for folder_path in project_path.iterdir():
        if not folder_path.name.startswith(".") and folder_path.is_dir() and markdown_count < limit:
            for md_path in folder_path.glob("*.md"):
                if md_path.is_file() and "report" in md_path.stem.lower():
                    markdown_count += 1
                    try:
                        extractor.analyze_feedstock_sustainability(audit_path=md_path)
                    except Exception as e:
                        print(f"Error processing {md_path}: {str(e)}")
                    time.sleep(1)  # Sleep for 1 second to avoid rate limiting

    print(f"Successfully processed {markdown_count} markdown files")
    return 0


def populate_feedstock_evaluation_command(supabase_url, supabase_api_key, project_dir):
    if not supabase_url or not supabase_api_key:
        print("Error: Supabase URL and api key are required")
        return 1

    try:
        supabase_client = SupabaseClient.get_client(supabase_url, supabase_api_key)
        populate_feedstock_evaluation_table(project_dir, supabase_client)
        print("Successfully populated feedstock evaluation table")
        return 0
    except Exception as e:
        print(f"Error populating feedstock evaluation table: {str(e)}")
        return 1
