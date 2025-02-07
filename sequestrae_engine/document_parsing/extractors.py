import json
import logging
import os
import re
import time
from typing import Dict, List

import pandas as pd
from mistralai import Mistral

from sequestrae_engine.core.utilities import load_json_file

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define paths relative to this file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_PROMPT_PATH = os.path.join(SCRIPT_DIR, "prompts/system_prompt.txt")
DUE_DILIGENCE_SYSTEM_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/due_diligence_system_prompt.txt"
)
DUE_DILIGENCE_CRITERIA_PATH = os.path.join(SCRIPT_DIR, "prompts/due_diligence_criteria.csv")
FEEDSTOCK_PROMPT_PATH = os.path.join(SCRIPT_DIR, "prompts/feedstock_prompt.txt")
FEEDSTOCK_CRITERIA_PATH = os.path.join(SCRIPT_DIR, "prompts/feedstock_criteria.json")


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
        with open(SYSTEM_PROMPT_PATH, "r") as file:
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

    def analyze_due_diligence_criteria(
        self, project_name: str, markdown_document_path: str, output_path=None, overwrite=False
    ):

        if output_path is None:
            # output_path = os.path.join(markdown_document_path, "../", "analysis", "{}_analysis.json".format(project_name))
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(markdown_document_path)),
                "analysis",
                f"{project_name}_analysis.json",
            )

        # Check if file exists and overwrite is False
        if os.path.exists(output_path) and not overwrite:
            logger.info(
                f"Output file already exists at {output_path} and overwrite=False. Skipping."
            )
            return

        with open(DUE_DILIGENCE_SYSTEM_PROMPT_PATH, "r") as f:
            context_content = f.read()

        criteria_df = pd.read_csv(DUE_DILIGENCE_CRITERIA_PATH)
        grouped_criteria_df = (
            criteria_df.groupby(["topic", "sub_topic", "risk_factor"])
            .apply(lambda x: dict(zip(x["question"], x["instruction"])))
            .reset_index(name="qa_pairs")
        )

        # Template for the full message
        full_message_template = """
        {context_content}

        **Criteria Guideline**

        Topic: {topic}
        Subtopic: {sub_topic}
        Risk factor: {risk_factor}
        Questions & Instruction: {questions}

        **Project documents**

        {audit_report}
        """

        with open(markdown_document_path, "r") as file:
            concatenated_project_doc = file.read()

        result_list = []
        for _, r in grouped_criteria_df.iterrows():
            question_list = []
            template_instruction = """
                Question: {question}.
                Instruction: {instruction}
                ----
            """

            for question, instruction in r["qa_pairs"].items():
                question_list.append(
                    template_instruction.format(question=question, instruction=instruction)
                )

                joined_question = "".join(question_list)

            full_message = full_message_template.format(
                context_content=context_content,
                topic=r["topic"],
                sub_topic=r["sub_topic"],
                risk_factor=r["risk_factor"],
                questions=joined_question,
                audit_report=concatenated_project_doc,
            )
            messages = [{"role": "user", "content": full_message}]

            chat_response = self.mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=messages,
                response_format={"type": "json_object"},
            )

            response_content = chat_response.choices[0].message.content
            response_content_dict = json.loads(response_content)
            result_list.extend(response_content_dict.get("analysis"))
            time.sleep(3)  # Rate limiting

        # Create parent directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:  # Only create directory if path has a parent directory
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_list, f, indent=2)

    def analyze_feedstock_sustainability(
        self, audit_path: str, output_folder_path=None, overwrite=False
    ) -> List[Dict]:
        """
        Analyze feedstock sustainability from audit report using Mistral LLM.

        Args:
            audit_path: Path to the audit report file
            output_folder_path: Optional path to output folder. If None, uses same directory as input
            overwrite: Whether to overwrite existing output file

        Returns:
            List of analysis results for each topic
        """
        start_time = time.time()

        # Determine output path
        input_dir = os.path.dirname(audit_path)
        input_filename = os.path.basename(audit_path)
        output_filename = os.path.splitext(input_filename)[0] + "_feedstock_analysis.json"

        output_path = os.path.join(
            output_folder_path if output_folder_path else input_dir, output_filename
        )

        # Check if file exists and overwrite is False
        if os.path.exists(output_path) and not overwrite:
            logger.info(
                f"Output file already exists at {output_path} and overwrite=False. Skipping."
            )
            return

        # Load prompts and criteria
        with open(FEEDSTOCK_PROMPT_PATH, "r") as f:
            context_content = f.read()
        with open(audit_path, "r") as file:
            audit_report = file.read()

        criteria_guideline = load_json_file(FEEDSTOCK_CRITERIA_PATH)

        # Template for the full message
        full_message_template = """
        {context_content}

        **Criteria Guideline**

        Topic: {topic}
        {questions}

        **Audit report**

        {audit_report}
        """

        result_list = []

        # Process each topic in the criteria guideline
        for topic in criteria_guideline.keys():
            questions = criteria_guideline.get(topic)

            full_message = full_message_template.format(
                context_content=context_content,
                topic=topic,
                questions=questions,
                audit_report=audit_report,
            )

            messages = [{"role": "user", "content": full_message}]

            chat_response = self.mistral_client.chat.complete(
                model=self.model, messages=messages, response_format={"type": "json_object"}
            )

            response_content = chat_response.choices[0].message.content
            response_content_dict = json.loads(response_content)
            result_list.append(response_content_dict)
            time.sleep(1)  # Rate limiting

        # Save the JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_list, f, indent=2)

        running_time_in_minutes = round((time.time() - start_time) / 60, 2)
        logger.info(
            f"Feedstock analysis complete in {running_time_in_minutes} minutes. Results saved to {output_path}"
        )
        return result_list
