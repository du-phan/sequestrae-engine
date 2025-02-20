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

HALLUCINATION_DETECTION_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/hallucination_evaluation_prompt.txt"
)

HALLUCINATION_FIXING_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/hallucination_fixing_prompt.txt"
)

PERTINENCE_EVALUATION_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/pertinence_evaluation_prompt.txt"
)

SUBTOPIC_RESUME_PROMPT_PATH = os.path.join(SCRIPT_DIR, "prompts/subtopic_resume_prompt.txt")

MODEL_TEMPERATURE = 0

REQUIRED_FIELDS_FOR_DUE_DILIGENCE = {
    "topic",
    "sub_topic",
    "risk_factor",
    "question",
    "short_answer",
    "long_answer",
    "detail_level",
    "evidence_found",
    "missing_data",
    "contradictory_data",
}

REQUIRED_FIELDS_FOR_SUMMARIES = {"topic", "sub_topic", "analysis"}


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
    def __init__(self, mistral_api_key, model="mistral-large-latest"):
        self.model = model
        self.mistral_client = Mistral(api_key=mistral_api_key)

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
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(markdown_document_path)),
                "analysis",
                f"{project_name}_analysis_{self.model}.json",
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
        count = 1
        for _, r in grouped_criteria_df.iterrows():
            print(
                f"{count}/{len(grouped_criteria_df)}",
                r["topic"],
                r["sub_topic"],
                r["risk_factor"],
                len(r["qa_pairs"]),
            )
            count += 1
            start_time = time.time()
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
                temperature=MODEL_TEMPERATURE,
            )

            response_content = chat_response.choices[0].message.content
            due_diligence_json_array = self._validate_and_fix_llm_response(
                response_content, REQUIRED_FIELDS_FOR_DUE_DILIGENCE
            )

            result_with_hallucination_analysis = self._analyze_hallucination(
                due_diligence_json_array, concatenated_project_doc
            )

            fixed_results = self._fix_hallucinations_recursive(
                result_with_hallucination_analysis, concatenated_project_doc
            )
            result_list.extend(fixed_results)
            running_time_in_minutes = round((time.time() - start_time) / 60, 2)
            print(f"    Total time: {running_time_in_minutes} minutes")
            time.sleep(1)  # Rate limiting

        # Create parent directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:  # Only create directory if path has a parent directory
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_list, f, indent=2)

    def _validate_json_schema(self, json_array: List[Dict], required_fields: set) -> bool:
        """
        Validate that the JSON array contains all required fields in each object.

        Args:
            json_array: List of dictionaries to validate
            required_fields: Set of field names that must be present

        Returns:
            bool: True if valid, False if invalid
        """
        if not isinstance(json_array, list):
            return False

        for item in json_array:
            if not isinstance(item, dict):
                return False
            if not all(field in item for field in required_fields):
                return False
        return True

    def _analyze_hallucination(
        self, criteria_response_json_array: List[Dict], concatenated_project_doc: str
    ):
        """
        Analyze hallucination in the project document using Mistral LLM.

        Args:
            criteria_response: Dictionary containing the criteria response
            concatenated_project_doc: Concatenated project document
        """
        start_time = time.time()

        full_message_template = """
        {context_content}

        **Context**
        The following text is the concatenated Markdown document to be used as context:
        ```md
        {concatenated_project_doc}
        ```

        **Answer to evaluate**
        The following json object contains the answer provided by the previous LLM to be evaluated:
        {criteria_response}
        """
        with open(HALLUCINATION_DETECTION_PROMPT_PATH, "r") as f:
            context_content = f.read()

        full_message = full_message_template.format(
            context_content=context_content,
            concatenated_project_doc=concatenated_project_doc,
            criteria_response=criteria_response_json_array,
        )

        chat_response = self.mistral_client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": full_message}],
            response_format={"type": "json_object"},
            temperature=MODEL_TEMPERATURE,
        )

        response_content = chat_response.choices[0].message.content
        response_json_array = self._validate_and_fix_llm_response(
            response_content, REQUIRED_FIELDS_FOR_DUE_DILIGENCE
        )
        end_time = time.time()
        running_time_in_seconds = round(end_time - start_time, 2)
        # logger.info('Hallucination analysis complete in {} seconds'.format(running_time_in_seconds))
        time.sleep(1)  # Rate limiting
        return response_json_array

    def _fix_hallucination(
        self, criteria_response_json_array: List[Dict], concatenated_project_doc: str
    ):
        """
        Fix hallucination in the project document using Mistral LLM.

        Args:
            criteria_response: Dictionary containing the criteria response
            concatenated_project_doc: Concatenated project document
        """
        start_time = time.time()

        full_message_template = """
        {context_content}

        **Context**
        The following text is the concatenated Markdown document to be used as context:
        ```md
        {concatenated_project_doc}
        ```

        **Answer to fix**
        The following json object contains the answer provided by the previous LLM with hallucination issues to be fixed:

        ```json
        {criteria_response}
        ```

        Return only the fixed JSON array and nothing else:

        """
        with open(HALLUCINATION_FIXING_PROMPT_PATH, "r") as f:
            context_content = f.read()

        full_message = full_message_template.format(
            context_content=context_content,
            concatenated_project_doc=concatenated_project_doc,
            criteria_response=json.dumps(criteria_response_json_array, indent=2),
        )

        chat_response = self.mistral_client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": full_message}],
            response_format={"type": "json_object"},
            temperature=MODEL_TEMPERATURE,
        )

        response_content = chat_response.choices[0].message.content
        response_json_array = self._validate_and_fix_llm_response(
            response_content, REQUIRED_FIELDS_FOR_DUE_DILIGENCE
        )
        end_time = time.time()
        running_time_in_seconds = round(end_time - start_time, 2)
        time.sleep(1)
        return response_json_array

    def _fix_hallucinations_recursive(
        self, result_json_array: List[Dict], concatenated_project_doc: str, max_iterations: int = 5
    ) -> List[Dict]:
        """
        Recursively fix hallucinations in the results until no hallucinations are found or max iterations reached.
        """
        start_time = time.time()
        iteration = 0

        # Count initial hallucinations
        initial_hallucinations = sum(
            1 for result in result_json_array if result.get("is_hallucination") == True
        )

        if initial_hallucinations == 0:
            # print("    No hallucinations detected in initial results")
            return result_json_array

        print(
            f"    Starting hallucination fixing process. Found {initial_hallucinations} hallucinations"
        )

        while iteration < max_iterations:
            fixed_result = self._fix_hallucination(result_json_array, concatenated_project_doc)
            print("    fixed_result:", fixed_result)
            print("------------")
            analyzed_result = self._analyze_hallucination(fixed_result, concatenated_project_doc)
            print("    analyzed_result:", analyzed_result)
            print("------------")

            num_remaining_hallucinations = sum(
                1 for result in analyzed_result if result.get("is_hallucination") == True
            )

            if num_remaining_hallucinations == 0:
                end_time = time.time()
                running_time_in_minutes = round((end_time - start_time) / 60, 2)
                print(
                    f"    Successfully fixed {initial_hallucinations} hallucinations in {running_time_in_minutes} minutes after {iteration + 1} iterations"
                )
                return analyzed_result
            else:
                result_json_array = analyzed_result
                iteration += 1
                # logger.debug(f"Iteration {iteration + 1}: {current_hallucinations} hallucinations remaining")
                print(
                    f"   Iteration {iteration + 1}: {num_remaining_hallucinations} hallucinations remaining"
                )

        logger.warning(
            f"Reached maximum iterations ({max_iterations}). {num_remaining_hallucinations} remaining hallucinations"
        )
        return result_json_array

    def _fix_malformatted_json(
        self, criteria_response_json_array: List[Dict], required_fields: set
    ):
        """
        Fix malformatted JSON array with LLM

        Args:
            criteria_response_json_array: Dictionary containing the criteria response
            required_fields: Set of field names that must be present in each object
        """

        fields_list = "\n".join(f'* "{field}"' for field in required_fields)

        full_message_template = """
        Fix the following malformatted JSON array. Each entry must have at least the following fields:
        {fields_list}

        The provided malformed JSON array is:
        ```json
        {criteria_response}
        ```

        Return only the fixed JSON array and nothing else.
        """
        full_message = full_message_template.format(
            fields_list=fields_list, criteria_response=criteria_response_json_array
        )

        chat_response = self.mistral_client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": full_message}],
            response_format={"type": "json_object"},
            temperature=MODEL_TEMPERATURE,
        )

        response_content = chat_response.choices[0].message.content
        response_content_dict = json.loads(response_content)
        return response_content_dict

    def _analyze_pertinence(self, criteria_response: Dict, concatenated_project_doc: str):
        """
        Analyze the pertinence of the criteria response.

        Args:
            criteria_response: Dictionary containing the criteria response
            concatenated_project_doc: Concatenated project document
        """
        start_time = time.time()

        full_message_template = """
        {context_content}

        **Context**
        The following text is the concatenated Markdown document to be used as context:
        ```md
        {concatenated_project_doc}
        ```

        **Answer to evaluate**
        The following json object contains the answer provided by the previous LLM to be evaluated:
        {criteria_response}
        """
        with open(PERTINENCE_EVALUATION_PROMPT_PATH, "r") as f:
            context_content = f.read()

        full_message = full_message_template.format(
            context_content=context_content,
            concatenated_project_doc=concatenated_project_doc,
            criteria_response=json.dumps(criteria_response, indent=2),
        )

        chat_response = self.mistral_client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": full_message}],
            response_format={"type": "json_object"},
            temperature=MODEL_TEMPERATURE,
        )

        response_content = chat_response.choices[0].message.content
        response_content_dict = json.loads(response_content)
        end_time = time.time()
        running_time_in_seconds = round(end_time - start_time, 2)
        # logger.info('Pertinence evaluation complete in {} seconds'.format(running_time_in_seconds))
        time.sleep(1)  # Rate limiting
        return response_content_dict

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

    def _validate_and_fix_llm_response(
        self, response_content: str, required_fields: set
    ) -> List[Dict]:
        """
        Validate and fix JSON response from LLM if needed.

        Args:
            response_content: String containing the LLM response that should be JSON
            required_fields: Set of fields that must be present in each object

        Returns:
            List[Dict]: Validated JSON array matching required schema

        Raises:
            ValueError: If response cannot be parsed or fixed to match required schema
        """
        try:
            result_list = json.loads(response_content)
            if not self._validate_json_schema(result_list, required_fields):
                logger.warning("Response JSON does not match required schema, attempting to fix...")
                result_list = self._fix_malformatted_json(response_content, required_fields)
                if not self._validate_json_schema(result_list, required_fields):
                    logger.error("Failed to fix JSON schema after attempt")
                    raise ValueError("Could not generate valid JSON response")
        except json.JSONDecodeError:
            logger.warning("Invalid JSON response, attempting to fix...")
            result_list = self._fix_malformatted_json(response_content, required_fields)
            if not self._validate_json_schema(result_list, required_fields):
                logger.error("Failed to fix JSON schema after attempt")
                raise ValueError("Could not generate valid JSON response")

        return result_list

    def create_subtopic_summaries(self, analysis_json_path: str, output_path=None, overwrite=False):
        """
        Create summaries for each subtopic from an analysis JSON file.

        Args:
            analysis_json_path (str): Path to the analysis JSON file
            output_path (str, optional): Path to save the summaries. Defaults to None.
            overwrite (bool, optional): Whether to overwrite existing output file. Defaults to False.

        Returns:
            List[Dict]: List of summaries for each subtopic
        """
        # Set default output path if none provided
        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(analysis_json_path),
                os.path.splitext(os.path.basename(analysis_json_path))[0] + "_summaries.json",
            )

        # Check if file exists and overwrite is False
        if os.path.exists(output_path) and not overwrite:
            logger.info(
                f"Output file already exists at {output_path} and overwrite=False. Skipping."
            )
            return

        # Load analysis data directly to DataFrame
        df = pd.read_json(analysis_json_path)

        # Load the subtopic resume prompt
        with open(SUBTOPIC_RESUME_PROMPT_PATH, "r") as f:
            subtopic_prompt_template = f.read()

        # Template for the full message
        full_message_template = """
        {context_content}

        -------
        Carefully take into account the above instructions, analyze the following subtopic:

        ```json
        {input_data}
        ```
        """

        summaries = []
        # Group by topic and sub_topic
        grouped = df.groupby(["topic", "sub_topic"])

        total_groups = len(grouped)
        for idx, ((topic, subtopic), group) in enumerate(grouped, 1):
            logger.info(f"Processing group {idx}/{total_groups}: {topic} - {subtopic}")

            # Convert group data to dict records
            group_data = group.to_dict("records")

            full_message = full_message_template.format(
                context_content=subtopic_prompt_template,
                input_data=json.dumps(group_data, indent=2),
            )

            # Get response from Mistral
            chat_response = self.mistral_client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": full_message}],
                response_format={"type": "json_object"},
                temperature=MODEL_TEMPERATURE,
            )

            response_content = chat_response.choices[0].message.content
            summary_json = self._validate_and_fix_llm_response(
                response_content, REQUIRED_FIELDS_FOR_SUMMARIES
            )
            summaries.append(summary_json)

            time.sleep(1)  # Rate limiting

        # Save summaries to file
        with open(output_path, "w") as f:
            json.dump(summaries, f, indent=2)

        logger.info(f"Created summaries for {len(summaries)} subtopics. Saved to {output_path}")
