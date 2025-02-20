import logging
import os
import time
from functools import wraps
from pathlib import Path
from time import sleep

from sequestrae_engine.db.client import SupabaseClient
from sequestrae_engine.db.scripts.populate_audit_reports import populate_feedstock_evaluation_table
from sequestrae_engine.document_parsing.extractors import AuditReportExtractor
from sequestrae_engine.document_parsing.parser import PDFToMarkdownParser

# Configure logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def retry_on_error(max_retries=3, delay=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise e
                    logger.warning(
                        f"Error occurred: {str(e)}. Retrying in {delay} seconds... (Attempt {retries}/{max_retries})"
                    )
                    sleep(delay)
            return None

        return wrapper

    return decorator


def parse_pdfs_command(api_key, project_dir, limit=5):
    if limit is None:
        limit = 5
    logger.info(f"Max number of files to process: {limit}")

    if not api_key:
        logger.error("LLAMA_API_KEY is required")
        return 1

    parser = PDFToMarkdownParser(api_key=api_key)
    project_path = Path(project_dir)

    if not project_path.exists():
        logger.error(f"Directory not found at {project_path}")
        return 1

    pdf_count = 0
    for folder_path in project_path.iterdir():
        if not folder_path.name.startswith(".") and folder_path.is_dir() and pdf_count < limit:
            for pdf_path in folder_path.glob("*.pdf"):
                if pdf_path.is_file() and "report" in pdf_path.stem.lower():
                    pdf_count += 1
                    parser.parse_pdf(pdf_path)

    logger.info(f"Successfully processed {pdf_count} PDF files")
    return 0


def extract_audit_information_command(api_key, project_dir, limit=100):
    if limit is None:
        limit = 100
    logger.info(f"Max number of files to process: {limit}")

    if not api_key:
        logger.error("MISTRAL_API_KEY is required")
        return 1

    extractor = AuditReportExtractor(mistral_api_key=api_key)
    project_path = Path(project_dir)

    if not project_path.exists():
        logger.error(f"Directory not found at {project_path}")
        return 1

    markdown_count = 0
    for folder_path in project_path.iterdir():
        if not folder_path.name.startswith(".") and folder_path.is_dir() and markdown_count < limit:
            for md_path in folder_path.glob("*.md"):
                if md_path.is_file() and "report" in md_path.stem.lower():
                    markdown_count += 1
                    try:
                        retry_on_error()(extractor.parse_audit_report)(audit_report_path=md_path)
                    except Exception as e:
                        logger.error(f"Error processing {md_path}: {str(e)}")
                    time.sleep(1)  # Sleep for 1 second to avoid rate limiting

    logger.info(f"Successfully processed {markdown_count} markdown files")
    return 0


def evaluate_feedstock_sustainability_command(api_key, project_dir, limit=100):
    if limit is None:
        limit = 100
    logger.info(f"Max number of files to process: {limit}")

    if not api_key:
        logger.error("MISTRAL_API_KEY is required")
        return 1

    extractor = AuditReportExtractor(mistral_api_key=api_key)
    project_path = Path(project_dir)

    if not project_path.exists():
        logger.error(f"Directory not found at {project_path}")
        return 1

    markdown_count = 0
    for folder_path in project_path.iterdir():
        if not folder_path.name.startswith(".") and folder_path.is_dir() and markdown_count < limit:
            for md_path in folder_path.glob("*.md"):
                if md_path.is_file() and "report" in md_path.stem.lower():
                    markdown_count += 1
                    try:
                        retry_on_error()(extractor.analyze_feedstock_sustainability)(
                            audit_path=md_path
                        )
                    except Exception as e:
                        logger.error(f"Error processing {md_path}: {str(e)}")
                    time.sleep(1)  # Sleep for 1 second to avoid rate limiting

    logger.info(f"Successfully processed {markdown_count} markdown files")
    return 0


def populate_feedstock_evaluation_command(supabase_url, supabase_api_key, project_dir):
    if not supabase_url or not supabase_api_key:
        logger.error("Supabase URL and api key are required")
        return 1

    try:
        supabase_client = SupabaseClient.get_client(supabase_url, supabase_api_key)
        populate_feedstock_evaluation_table(project_dir, supabase_client)
        logger.info("Successfully populated feedstock evaluation table")
        return 0
    except Exception as e:
        logger.error(f"Error populating feedstock evaluation table: {str(e)}")
        return 1


def analyze_due_diligence_command(gemini_api_key, mistral_api_key, project_dir):
    """
    Process all PDFs in project subfolders and analyze due diligence criteria.

    Args:
        gemini_api_key: API key for PDF parsing
        mistral_api_key: API key for analysis
        project_dir: Root directory containing project folders
    """
    # max_num_folder = 60

    if not gemini_api_key or not mistral_api_key:
        logger.error("Both GEMINI_API_KEY and MISTRAL_API_KEY are required")
        return 1

    project_path = Path(project_dir)
    if not project_path.exists():
        logger.error(f"Directory not found at {project_path}")
        return 1

    pdf_parser = PDFToMarkdownParser(gemini_api_key=gemini_api_key)
    audit_extractor = AuditReportExtractor(mistral_api_key=mistral_api_key)

    # Count total subfolders (excluding hidden folders)
    total_folders = sum(
        1
        for folder in project_path.iterdir()
        if folder.is_dir() and not folder.name.startswith(".")
    )

    logger.info(f"Found {total_folders} project folders to process")

    processed_folder = 1
    for folder_path in project_path.iterdir():
        # if processed_folder >= max_num_folder:
        # break

        if not folder_path.name.startswith(".") and folder_path.is_dir():
            project_name = "_".join(folder_path.name.split())
            logger.info(f"Analyzing project {processed_folder}/{total_folders}: {project_name} ...")

            # Parse PDFs in folder
            start_time = time.time()
            pdf_parser.parse_pdf_folder(folder_path, overwrite=False)
            logger.info(
                f"--------- PDF processing completed in {round((time.time() - start_time)/60, 2)} minutes ---------"
            )

            # Analyze due diligence
            markdown_document_path = os.path.join(
                folder_path, "parsed_markdown", f"concatenated_documentation_{pdf_parser.model}.md"
            )
            start_time = time.time()
            retry_on_error()(audit_extractor.analyze_due_diligence_criteria)(
                project_name=project_name, markdown_document_path=markdown_document_path
            )
            logger.info(
                f"--------- Due diligence analysis complete in {round((time.time() - start_time)/60, 2)} minutes."
            )
            processed_folder += 1

        time.sleep(1)

    logger.info("Completed processing all projects")
    return 0


def create_subtopic_summaries_command(mistral_api_key, project_dir):
    """
    Process all analysis JSON files in project subfolders and create subtopic summaries.

    Args:
        mistral_api_key: API key for analysis
        project_dir: Root directory containing project folders
    """
    if not mistral_api_key:
        logger.error("MISTRAL_API_KEY is required")
        return 1

    project_path = Path(project_dir)
    if not project_path.exists():
        logger.error(f"Directory not found at {project_path}")
        return 1

    audit_extractor = AuditReportExtractor(mistral_api_key=mistral_api_key)

    # Count total subfolders (excluding hidden folders)
    total_folders = sum(
        1
        for folder in project_path.iterdir()
        if folder.is_dir() and not folder.name.startswith(".")
    )

    logger.info(f"Found {total_folders} project folders to process")

    processed_folder = 1
    for folder_path in project_path.iterdir():
        if not folder_path.name.startswith(".") and folder_path.is_dir():
            project_name = "_".join(folder_path.name.split())
            logger.info(
                f"Processing project {processed_folder}/{total_folders}: {project_name} ..."
            )

            # Find analysis file
            analysis_path = (
                folder_path / "analysis" / f"{project_name}_analysis_mistral-large-latest.json"
            )
            if not analysis_path.exists():
                logger.warning(f"Analysis file not found for {project_name}, skipping...")
                continue

            # Create summaries
            start_time = time.time()
            try:
                retry_on_error()(audit_extractor.create_subtopic_summaries)(
                    analysis_json_path=str(analysis_path)
                )
                logger.info(
                    f"--------- Subtopic summaries created in {round((time.time() - start_time)/60, 2)} minutes."
                )
            except Exception as e:
                logger.error(f"Error processing {project_name}: {str(e)}")

            processed_folder += 1
            time.sleep(1)

    logger.info("Completed processing all projects")
    return 0
