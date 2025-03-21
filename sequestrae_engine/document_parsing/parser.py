import logging
import os
import time

from google import genai
from google.genai import types

from sequestrae_engine.document_parsing.extractors import PathManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PDFToMarkdownParser:
    def __init__(self, gemini_api_key, project_folder, model="gemini-2.0-flash-001"):
        # self.llama_api_key = llama_api_key
        self.model = model
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.path_manager = PathManager(model=model, project_folder=project_folder)
        # No need to store project_name, PathManager already has it

    """
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
    """

    def save_markdown(self, markdown_content, output_path):
        # Ensure the directory exists before writing the file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as md_file:
            md_file.write(markdown_content)

    def parse_pdf_folder(self, overwrite=False):
        """
        Parse PDFs in the project folder or use existing markdown files if available.
        For each PDF, checks if a corresponding .md file exists:
        - If yes, use the markdown content directly
        - If no, parse the PDF to markdown

        Args:
            overwrite (bool): Whether to overwrite existing output file
        """
        # Get the project folder path
        project_folder = self.path_manager.project_folder

        # Get the output path for the combined markdown
        output_path = self.path_manager.get_concatenated_doc_path()

        if os.path.exists(output_path) and not overwrite:
            logger.info(
                f"Output file {output_path} already exists and overwrite=False. Skipping processing."
            )
            return

        # Get all PDF files in the folder
        pdf_files = [f for f in os.listdir(project_folder) if f.lower().endswith(".pdf")]

        if not pdf_files:
            logger.warning(f"No PDF files found in {project_folder}")
            return

        combined_content = []

        # Process each PDF file
        for pdf_file in pdf_files:
            base_name = os.path.splitext(pdf_file)[0]
            md_file = f"{base_name}.md"
            md_path = os.path.join(project_folder, md_file)

            # Check if corresponding markdown file exists
            if os.path.exists(md_path):
                logger.info(f"Using existing markdown file for: {pdf_file}")
                with open(md_path, "r") as f:
                    doc_content = f.read()
            else:
                # Parse the PDF if no markdown exists
                pdf_path = os.path.join(project_folder, pdf_file)
                logger.info(f"Processing PDF: {pdf_file}")

                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                prompt = """
                Perform OCR on the following pages and convert the content into Markdown format.

                - Output **only** the Markdown text—do not include any additional comments, explanations, or summaries.
                - The document pertains to a biochar project and may include project documentation, audit reports, or related materials.
                - Ignore the table of contents—it is not needed.
                - Preserve section headings, bullet points, and emphasized text (bold, italic) as they appear in the document.

                ### Table Handling:
                - **Extract all tables** from the document—**do not skip any tables.**
                - Convert tables into **structured and readable Markdown tables** instead of HTML.
                - If a table's format is unclear or difficult to read, **restructure or transpose it** for better clarity while preserving the original meaning.
                - If a table is spread across multiple pages, **reconstruct it properly** in the output.
                - If the document contains tabular data without clear table formatting, **detect and format it as a Markdown table** to improve readability.
                """
                response = self.gemini_client.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Part.from_bytes(
                            data=pdf_bytes,
                            mime_type="application/pdf",
                        ),
                        prompt,
                    ],
                )

                doc_content = response.text
                time.sleep(1)  # Sleep for 1 second to avoid rate limiting

            file_section = (
                f"# The following text is the content of file: {pdf_file}\n{doc_content}\n\n"
            )
            combined_content.append(file_section)

        # Save combined content
        final_content = "".join(combined_content)
        self.save_markdown(final_content, output_path)
        logger.info(f"Combined markdown saved to {output_path}")
