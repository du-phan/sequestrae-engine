import logging
import os

import nest_asyncio
from llama_index.core import SimpleDirectoryReader
from llama_parse import LlamaParse

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PDFToMarkdownParser:
    def __init__(self, api_key):
        self.api_key = api_key

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
            continuous_mode=True,
            disable_image_extraction=True,
            output_tables_as_HTML=False,
            api_key=self.api_key,
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
