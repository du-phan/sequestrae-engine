import logging
import os
import time

import nest_asyncio
from llama_index.core import SimpleDirectoryReader
from llama_parse import LlamaParse

nest_asyncio.apply()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PDFToMarkdownParser:
    def __init__(self, llama_api_key):
        self.llama_api_key = llama_api_key

    def parse_pdf(self, pdf_path, output_folder_path=None, overwrite=False):
        pdf_dir = os.path.dirname(pdf_path)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

        # Determine output path
        if output_folder_path:
            output_path = os.path.join(output_folder_path, f"{pdf_name}.md")
        else:
            # Default to same directory as PDF
            output_path = os.path.join(pdf_dir, f"{pdf_name}.md")

        # Check if file already exists and respect overwrite flag
        if os.path.exists(output_path) and not overwrite:
            logger.info(f"Markdown file {output_path} already exists and overwrite=False")
            return

        parser = LlamaParse(
            language="en",
            result_type="markdown",
            disable_image_extraction=True,
            skip_diagonal_text=True,
            output_tables_as_HTML=True,
            api_key=self.llama_api_key,
        )

        file_extractor = {".pdf": parser}

        logger.info(f"Parsing {pdf_path} and save to {output_path}")
        nest_asyncio.apply()  # Required for running asyncio in Jupyter Notebook
        documents = SimpleDirectoryReader(
            input_files=[pdf_path], file_extractor=file_extractor
        ).load_data()

        doc_dict = documents[0].dict()
        markdown_content = doc_dict.get("text")

        self.save_markdown(markdown_content, output_path)

    def save_markdown(self, markdown_content, output_path):
        with open(output_path, "w") as md_file:
            md_file.write(markdown_content)

    def parse_pdf_folder(self, folder_path, output_path=None):
        """
        Parse all PDF files in a folder (excluding those with '_report' in name)
        and concatenate their content into a single markdown file.
        Also includes content from existing _report.md files.

        Args:
            folder_path: Path to the folder containing PDFs
            output_path: Optional output path. If None, defaults to
                        {folder_path}/parsed_markdown/concatenated_documentation.md
        """
        start_time = time.time()
        if output_path is None:
            output_path = os.path.join(
                folder_path, "parsed_markdown", "concatenated_documentation.md"
            )
            # Create the parsed_markdown directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Get all files in the folder
        all_files = os.listdir(folder_path)
        pdf_files = [
            f for f in all_files if f.lower().endswith(".pdf") and "report" not in f.lower()
        ]
        report_files = [f for f in all_files if f.lower().endswith(".md") and "report" in f.lower()]

        print("Report file: ", report_files)

        if not pdf_files and not report_files:
            logger.warning(f"No eligible files found in {folder_path}")
            return

        # Initialize parser once for all files
        parser = LlamaParse(
            language="en",
            result_type="markdown",
            disable_image_extraction=True,
            skip_diagonal_text=True,
            output_tables_as_HTML=True,
            api_key=self.llama_api_key,
        )
        file_extractor = {".pdf": parser}

        combined_content = []

        # Process regular PDFs
        for pdf_file in pdf_files:
            pdf_path = os.path.join(folder_path, pdf_file)
            logger.info(f"Processing PDF: {pdf_file}")

            documents = SimpleDirectoryReader(
                input_files=[pdf_path], file_extractor=file_extractor
            ).load_data()

            doc_content = documents[0].dict().get("text")
            file_section = (
                f"# The following text is the content of file: {pdf_file}\n{doc_content}\n\n"
            )
            combined_content.append(file_section)
            time.sleep(1)  # Sleep for 1 second to avoid rate limiting

        # Add content from report markdown files
        for md_file in report_files:
            md_path = os.path.join(folder_path, md_file)
            logger.info(f"Adding report file: {md_file}")

            with open(md_path, "r") as f:
                report_content = f.read()
            file_section = (
                f"# The following text is the content of file: {md_file}\n{report_content}\n\n"
            )
            combined_content.append(file_section)

        # Save combined content
        final_content = "".join(combined_content)
        self.save_markdown(final_content, output_path)
        logger.info(f"Combined markdown saved to {output_path}")
        end_time = time.time()
        duration_in_seconds = round(end_time - start_time, 2)
        logger.info(f"Processing completed in {duration_in_seconds} seconds")
