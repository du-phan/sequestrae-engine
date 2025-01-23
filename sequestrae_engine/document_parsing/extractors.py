import json
import logging
import os
import re

from mistralai import Mistral

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_markdown_file(filepath: str) -> str:
    """
    Read a markdown file and return its contents as a string

    Args:
        filepath (str): Path to the markdown file

    Returns:
        str: Contents of the markdown file
    """
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        raise FileNotFoundError(f"Could not find markdown file at {filepath}")
    except Exception as e:
        raise Exception(f"Error reading markdown file: {str(e)}")


class AuditReportExtractor:
    def __init__(self, api_key, model="mistral-large-latest"):
        self.model = model
        self.mistral_client = Mistral(api_key=api_key)

    def parse_audit_report(self, audit_report_path, output_folder_path=None, overwrite=False):
        # Read the markdown file
        report_content = read_markdown_file(audit_report_path)

        # Extract relevant information from the markdown content
        audit_report_dict = self.extract_audit_report_data(report_content)

        # Determine output path
        input_dir = os.path.dirname(audit_report_path)
        input_filename = os.path.basename(audit_report_path)
        output_filename = os.path.splitext(input_filename)[0] + ".json"

        output_path = os.path.join(
            output_folder_path if output_folder_path else input_dir, output_filename
        )

        # Check if file exists and overwrite is False
        if os.path.exists(output_path) and not overwrite:
            logger.info(f"Output file already exists at {output_path} and overwrite=False")

        # Save the JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(audit_report_dict, f, indent=2)

        logger.info(f"Parsing {audit_report_path} and saving to {output_path}")

        return audit_report_dict

    def extract_audit_report_data(self, report_content):
        # load the system prompt file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(script_dir, "system_prompt.txt")
        with open(prompt_path, "r") as file:
            system_prompt = file.read()

        user_message_template = """
            Analyze carefully the following audit report and return the result in short JSON object:

            ```markdown
            {report_content}
            ```
        """

        user_message = user_message_template.format(report_content=report_content)
        full_message_template = """
            {system_prompt}
            ---
            {user_prompt}
        """

        full_message = full_message_template.format(
            system_prompt=system_prompt, user_prompt=user_message
        )

        messages = [
            {
                "role": "user",
                "content": full_message,
            }
        ]

        chat_response = self.mistral_client.chat.complete(
            model=self.model,
            messages=messages,
            response_format={
                "type": "json_object",
            },
        )

        audit_info = chat_response.choices[0].message.content
        audit_dict = json.loads(audit_info)

        return audit_dict
