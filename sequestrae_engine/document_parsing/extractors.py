import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Literal, Optional, Union

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
PROJECT_OVERVIEW_EXTRACTION_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/project_overview_extraction_prompt.txt"
)
# Define prompt paths that have current/future versions
DUE_DILIGENCE_SYSTEM_PROMPT_CURRENT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/due_diligence_system_prompt_current_project.txt"
)
DUE_DILIGENCE_SYSTEM_PROMPT_FUTURE_PATH = os.path.join(
    SCRIPT_DIR, "prompts/due_diligence_system_prompt_future_project.txt"
)
DUE_DILIGENCE_CRITERIA_PATH = os.path.join(SCRIPT_DIR, "prompts/due_diligence_criteria.csv")

HALLUCINATION_DETECTION_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/hallucination_evaluation_prompt.txt"
)

HALLUCINATION_FIXING_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/hallucination_fixing_prompt.txt"
)

SUBTOPIC_RESUME_CURRENT_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/subtopic_resume_prompt_current_project.txt"
)
SUBTOPIC_RESUME_FUTURE_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/subtopic_resume_prompt_future_project.txt"
)
SUBTOPIC_REFINE_PROMPT_PATH = os.path.join(SCRIPT_DIR, "prompts/subtopic_refine_prompt.txt")

TOPIC_RESUME_CURRENT_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/topic_resume_prompt_current_project.txt"
)
TOPIC_RESUME_FUTURE_PROMPT_PATH = os.path.join(
    SCRIPT_DIR, "prompts/topic_resume_prompt_future_project.txt"
)

PROJECT_MAIN_IDEA_PROMPT_PATH = os.path.join(SCRIPT_DIR, "prompts/project_main_insight_prompt.txt")

MODEL_TEMPERATURE = 0

REQUIRED_FIELDS_FOR_DUE_DILIGENCE = {
    "topic",
    "sub_topic",
    "risk_factor",
    "question",
    "short_answer",
    "long_answer",
    "detail_level",
    "missing_data",
    "contradictory_data",
}

REQUIRED_FIELDS_FOR_SUBTOPIC_SUMMARIES = {"topic", "sub_topic", "analysis"}

REQUIRED_FIELDS_FOR_TOPIC_SUMMARIES = {"topic", "topic_summary"}

REQUIRED_FIELDS_FOR_MAIN_INSIGHTS = {
    "main_strengths",
    "main_considerations",
    "main_recommended_actions",
}


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


class PathManager:
    """
    Manages file paths for project data, standardizing path creation and derivation.
    """

    # Analysis file type constants
    ANALYSIS = "analysis"
    OVERVIEW = "overview"
    SUBTOPIC_SUMMARIES = "subtopic_summaries"
    TOPIC_SUMMARIES = "topic_summaries"
    MAIN_INSIGHTS = "main_insights"

    # Directory structure constants
    ANALYSIS_DIR = "analysis"
    PARSED_MARKDOWN_DIR = "parsed_markdown"

    # Common file names
    DEFAULT_MARKDOWN_FILE = "concatenated_documentation.md"

    def __init__(self, model: str, project_folder: str):
        """
        Initialize the PathManager with a model name and project folder.

        Args:
            model (str): Model name used for file naming
            project_folder (str): Path to project folder
        """
        self.model = model
        self.project_folder = project_folder
        # Always infer project name from project folder
        self._project_name = os.path.basename(os.path.normpath(project_folder))

    def set_project_folder(self, project_folder: str) -> None:
        """
        Set or update the project folder path.

        Args:
            project_folder (str): Path to the project folder
        """
        self.project_folder = project_folder
        # Update project name when folder changes
        self._project_name = os.path.basename(os.path.normpath(project_folder))

    @property
    def project_name(self) -> str:
        """
        Get project name from the project folder path.

        Returns:
            str: Name of the project derived from folder path
        """
        return self._project_name

    def get_analysis_dir(self) -> str:
        """
        Get the standard analysis directory path.

        Returns:
            str: Path to the analysis directory
        """
        return os.path.join(self.project_folder, self.ANALYSIS_DIR)

    def get_markdown_dir(self) -> str:
        """
        Get the standard parsed markdown directory path.

        Returns:
            str: Path to the parsed markdown directory
        """
        return os.path.join(self.project_folder, self.PARSED_MARKDOWN_DIR)

    def get_markdown_path(self, filename: Optional[str] = None) -> str:
        """
        Get path to a markdown file in the standard location.

        Args:
            filename (Optional[str]): Filename of the markdown file, defaults to standard name

        Returns:
            str: Path to the markdown file
        """
        if not filename:
            filename = self.DEFAULT_MARKDOWN_FILE
        return os.path.join(self.get_markdown_dir(), filename)

    def get_analysis_file_path(self) -> str:
        """
        Get path to the analysis file in the standard location.

        Returns:
            str: Path to the analysis file
        """
        filename = f"{self.project_name}_{self.ANALYSIS}.json"
        return os.path.join(self.get_analysis_dir(), filename)

    def get_overview_file_path(self) -> str:
        """
        Get path to the overview file in the standard location.

        Returns:
            str: Path to the overview file
        """
        filename = f"{self.project_name}_{self.OVERVIEW}.json"
        return os.path.join(self.get_analysis_dir(), filename)

    def get_subtopic_summaries_path(self) -> str:
        """
        Get path to the subtopic summaries file in the standard location.

        Returns:
            str: Path to the subtopic summaries file
        """
        return os.path.join(
            self.get_analysis_dir(), f"{self.project_name}_{self.SUBTOPIC_SUMMARIES}.json"
        )

    def get_topic_summaries_path(self) -> str:
        """
        Get path to the topic summaries file in the standard location.

        Returns:
            str: Path to the topic summaries file
        """
        return os.path.join(
            self.get_analysis_dir(), f"{self.project_name}_{self.TOPIC_SUMMARIES}.json"
        )

    def get_main_insights_path(self) -> str:
        """
        Get path to the main insights file in the standard location.

        Returns:
            str: Path to the main insights file
        """
        return os.path.join(
            self.get_analysis_dir(), f"{self.project_name}_{self.MAIN_INSIGHTS}.json"
        )

    def get_concatenated_doc_path(self) -> str:
        """
        Get the full path to the concatenated documentation file.

        Returns:
            str: Full path to the concatenated documentation file
        """
        filename = f"{self.project_name}_concatenated_documentation.md"
        return self.get_markdown_path(filename)

    def get_analysis_checkpoint_path(self) -> str:
        """
        Get path to the analysis checkpoint file in the standard location.

        Returns:
            str: Path to the analysis checkpoint file
        """
        filename = f"{self.project_name}_{self.ANALYSIS}_checkpoint.json"
        return os.path.join(self.get_analysis_dir(), filename)


class AuditReportExtractor:
    def __init__(
        self,
        mistral_api_key: str,
        project_folder: str,
        model: str = "mistral-large-latest",
        overwrite: bool = False,
    ):
        """
        Initialize the AuditReportExtractor with common parameters.

        Args:
            mistral_api_key (str): API key for Mistral
            model (str): Model to use for LLM inference
            project_folder (Optional[str]): Path to the project folder
            project_type (str): Type of project - "current" (ongoing) or "future" (planned)
            overwrite (bool): Whether to overwrite existing output files
        """
        self.model = model
        self.mistral_client = Mistral(api_key=mistral_api_key)
        self.overwrite = overwrite
        self.path_manager = PathManager(model, project_folder)
        self.project_type = None

    def set_project_folder(self, project_folder: str) -> None:
        """
        Set the project folder for analysis.

        Args:
            project_folder (str): Path to the project folder
        """
        self.path_manager.set_project_folder(project_folder)

    def _get_prompt_path(self, current_prompt_path: str, future_prompt_path: str) -> str:
        """
        Helper method to get the appropriate prompt path based on project type.

        Args:
            current_prompt_path (str): Path to the prompt file for current projects
            future_prompt_path (str): Path to the prompt file for future projects

        Returns:
            str: Selected prompt path
        """
        return current_prompt_path if self.project_type == "current" else future_prompt_path

    def _should_skip_existing(self, output_path: str) -> bool:
        """
        Check if output file exists and should be skipped.

        Args:
            output_path (str): Path to the output file

        Returns:
            bool: True if file exists and should be skipped, False otherwise
        """
        if os.path.exists(output_path) and not self.overwrite:
            logger.info(
                f"Output file already exists at {output_path} and overwrite=False. Skipping."
            )
            return True
        return False

    def _ensure_output_directory(self, output_path: str) -> None:
        """
        Ensure the output directory exists.

        Args:
            output_path (str): Path to the output file
        """
        output_dir = os.path.dirname(output_path)
        if output_dir:  # Only create directory if path has a parent directory
            os.makedirs(output_dir, exist_ok=True)

    def _save_json_output(self, data: Union[Dict, List], output_path: str) -> None:
        """
        Save data to JSON file.

        Args:
            data (Union[Dict, List]): Data to save
            output_path (str): Path to the output file
        """
        self._ensure_output_directory(output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Data saved to {output_path}")

    def extract_project_overview_data(self, overwrite: Optional[bool] = None):
        """
        Extract project overview data from the standard markdown document using Mistral LLM.

        Args:
            overwrite (Optional[bool]): Whether to overwrite existing output file

        Returns:
            Dict: Dictionary containing project overview data
        """
        # Use instance values if not specified
        overwrite = self.overwrite if overwrite is None else overwrite

        # Get standard file paths
        markdown_document_path = self.path_manager.get_concatenated_doc_path()
        output_path = self.path_manager.get_overview_file_path()

        # Check if file exists and should be skipped
        if self._should_skip_existing(output_path):
            # Load and return existing file
            return load_json_file(output_path)

        # Read the markdown file
        with open(markdown_document_path, "r", encoding="utf-8") as file:
            report_content = file.read()

        # Load the project overview extraction prompt
        with open(PROJECT_OVERVIEW_EXTRACTION_PROMPT_PATH, "r") as file:
            system_prompt = file.read()

        user_message_template = """
            Analyze carefully the following markdown and return the result in short JSON object:

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
            temperature=MODEL_TEMPERATURE,
        )

        response_content = chat_response.choices[0].message.content

        # Define required fields for project overview (adjust as needed)
        required_fields = {
            "country",
            "project_start_period",
            "feedstock_type",
            "project_description",
            "key_stakeholders",
        }

        # Validate and fix the response
        project_overview_data = self._validate_and_fix_llm_response(
            response_content, required_fields
        )

        # Save the JSON file using the helper method
        self._save_json_output(project_overview_data, output_path)

        logger.info(
            f"Extracted project overview data from {markdown_document_path} and saved to {output_path}"
        )

        return project_overview_data

    def analyze_due_diligence_criteria(self, overwrite: Optional[bool] = None):
        """
        Analyze due diligence criteria for a project with checkpointing for fault tolerance.

        Args:
            overwrite (Optional[bool]): Whether to overwrite existing output
        """
        # Use instance values if not specified
        overwrite = self.overwrite if overwrite is None else overwrite

        # Get standard file paths
        markdown_document_path = self.path_manager.get_concatenated_doc_path()
        output_path = self.path_manager.get_analysis_file_path()
        checkpoint_path = self.path_manager.get_analysis_checkpoint_path()

        # Check for ambiguous state (both output and checkpoint exist)
        if os.path.exists(output_path) and os.path.exists(checkpoint_path) and not overwrite:
            logger.warning(f"Both output file and checkpoint file exist. Using the output file.")
            # Prioritize the output file in this case
            return

        # Check if final output file exists and should be skipped
        if self._should_skip_existing(output_path):
            return

        # Check if checkpoint file exists
        checkpoint_exists = os.path.exists(checkpoint_path) and not overwrite
        result_list = []
        processed_indices = set()

        if checkpoint_exists:
            try:
                with open(checkpoint_path, "r", encoding="utf-8") as f:
                    checkpoint_data = json.load(f)
                    result_list = checkpoint_data.get("results", [])
                    processed_indices = set(map(int, checkpoint_data.get("processed_indices", [])))
                    logger.info(
                        f"Resuming from checkpoint with {len(result_list)} results and {len(processed_indices)} processed items"
                    )
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Error loading checkpoint file: {str(e)}. Starting from beginning.")
                result_list = []
                processed_indices = set()

        # Select the appropriate prompt file based on project_type
        due_diligence_prompt_path = self._get_prompt_path(
            DUE_DILIGENCE_SYSTEM_PROMPT_CURRENT_PATH, DUE_DILIGENCE_SYSTEM_PROMPT_FUTURE_PATH
        )

        with open(due_diligence_prompt_path, "r") as f:
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

        total_count = len(grouped_criteria_df)
        processed_count = len(processed_indices)
        remaining_count = total_count - processed_count

        # Ensure output directory exists
        self._ensure_output_directory(checkpoint_path)

        # Start time for this session
        session_start_time = time.time()
        # Track items processed in this current execution session
        session_processed_count = 0

        for idx, r in grouped_criteria_df.iterrows():
            # Skip already processed items
            if idx in processed_indices:
                continue

            # Calculate progress stats
            processed_count += 1
            remaining_count -= 1
            session_processed_count += 1  # Track items processed in this session
            percent_complete = (processed_count / total_count) * 100

            # Estimate time remaining if we have processed at least a few items in this session
            time_elapsed = time.time() - session_start_time

            if session_processed_count > 0:
                # Calculate average time per item based only on items processed in this session
                avg_time_per_item = time_elapsed / session_processed_count
                # Estimate remaining time based on items still to process
                est_time_remaining_mins = (avg_time_per_item * remaining_count) / 60
                # Format nicely with appropriate precision
                if est_time_remaining_mins < 1:
                    eta_str = f", ETA: <1 minute"
                else:
                    eta_str = f", ETA: {est_time_remaining_mins:.1f} minutes"
            else:
                eta_str = ""

            print(
                f"[{processed_count}/{total_count}] {percent_complete:.1f}%{eta_str} - "
                f"Processing: {r['topic']}, {r['sub_topic']}, {r['risk_factor']} "
                f"({len(r['qa_pairs'])} questions)"
            )

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

            try:
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

                # Mark as processed and update checkpoint file
                processed_indices.add(idx)

                # Save checkpoint
                checkpoint_data = {
                    "results": result_list,
                    "processed_indices": list(processed_indices),
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "progress_percent": percent_complete,
                }
                with open(checkpoint_path, "w", encoding="utf-8") as f:
                    json.dump(checkpoint_data, f, indent=2)

                running_time_in_minutes = round((time.time() - start_time) / 60, 2)
                print(f"    Item completed in {running_time_in_minutes} minutes")
                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.error(f"Error processing criteria {idx}: {str(e)}")
                logger.info(
                    f"Progress saved in checkpoint file. You can resume by running the function again."
                )
                # Return early but don't raise the exception - allows resuming from this point
                return

        # Save the final results using the helper method
        self._save_json_output(result_list, output_path)

        # If successful, clean up the checkpoint file
        if os.path.exists(checkpoint_path) and os.path.exists(output_path):
            try:
                os.remove(checkpoint_path)
                logger.info("Checkpoint file removed after successful completion")
            except OSError:
                logger.warning("Could not remove checkpoint file")

        logger.info(f"Due diligence analysis completed with {len(result_list)} results")

    def _validate_json_schema(self, json_data: List[Dict], required_fields: set) -> bool:
        """
        Validate that the input contains all required fields, handling both single dict and list of dicts.

        Args:
            json_data: Either a dictionary or list of dictionaries to validate
            required_fields: Set of field names that must be present

        Returns:
            bool: True if valid, False if invalid
        """
        # Handle single dictionary
        if isinstance(json_data, dict):
            return all(field in json_data for field in required_fields)

        # Handle list of dictionaries
        if isinstance(json_data, list):
            if not json_data:  # Empty list
                return False
            return all(
                isinstance(item, dict) and all(field in item for field in required_fields)
                for item in json_data
            )

        return False

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
                # logger.debug(f"Iteration {iteration + 1}: {current_hallucinations} remaining")
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
                print(result_list)
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

    def create_subtopic_summaries(self, overwrite: Optional[bool] = None):
        """
        Create summaries for each subtopic from an analysis JSON file.

        Args:
            overwrite (Optional[bool]): Whether to overwrite existing output file

        Returns:
            List[Dict]: List of summaries for each subtopic
        """
        # Use instance values if not specified
        overwrite = self.overwrite if overwrite is None else overwrite

        # Get standard file paths
        analysis_json_path = self.path_manager.get_analysis_file_path()
        output_path = self.path_manager.get_subtopic_summaries_path()

        # Check if file exists and should be skipped
        if self._should_skip_existing(output_path):
            return

        # Load analysis data directly to DataFrame
        df = pd.read_json(analysis_json_path)

        # Quick fix: Replace topic name (TODO: Fix naming inconsistency in upstream data)
        df["topic"] = df["topic"].replace("Climate science", "Carbon Accounting & Integrity")

        # Select the appropriate prompt file based on project_type
        subtopic_prompt_path = self._get_prompt_path(
            SUBTOPIC_RESUME_CURRENT_PROMPT_PATH, SUBTOPIC_RESUME_FUTURE_PROMPT_PATH
        )

        # Load the subtopic resume prompt
        with open(subtopic_prompt_path, "r") as f:
            print(f"Using subtopic prompt: {subtopic_prompt_path}")
            subtopic_resume_system_prompt = f.read()

        with open(SUBTOPIC_REFINE_PROMPT_PATH, "r") as f:
            refine_summary_system_prompt = f.read()

        # Template for the full message
        subtopic_summary_prompt_template = """
        {context_content}

        -------
        Carefully take into account the above instructions, analyze the following subtopic:

        ```json
        {input_data}
        ```

        Once you come up with the first version of the result, do a thorough step-by-step critical review based on the instructions above, try your best improve the result then return only the best version.
        """

        refine_summary_prompt_template = """
        {refine_summary_prompt}

        -------
        Carefully apply the instructions to the following input:

        ```json
        {original_json_summary}
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

            subtopic_summary_message = subtopic_summary_prompt_template.format(
                context_content=subtopic_resume_system_prompt,
                input_data=json.dumps(group_data, indent=2),
            )

            # Get response from Mistral
            chat_response_1 = self.mistral_client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": subtopic_summary_message}],
                response_format={"type": "json_object"},
                temperature=MODEL_TEMPERATURE,
            )

            summary_json = self._validate_and_fix_llm_response(
                chat_response_1.choices[0].message.content, REQUIRED_FIELDS_FOR_SUBTOPIC_SUMMARIES
            )

            refine_summary_message = refine_summary_prompt_template.format(
                refine_summary_prompt=refine_summary_system_prompt,
                original_json_summary=json.dumps(summary_json, indent=2),
            )

            chat_response_2 = self.mistral_client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": refine_summary_message}],
                response_format={"type": "json_object"},
                temperature=MODEL_TEMPERATURE,
            )

            refined_summary_json = self._validate_and_fix_llm_response(
                chat_response_2.choices[0].message.content, REQUIRED_FIELDS_FOR_SUBTOPIC_SUMMARIES
            )

            summaries.append(refined_summary_json)

            time.sleep(1)  # Rate limiting

        # Save summaries using the helper method
        self._save_json_output(summaries, output_path)
        logger.info(f"Created summaries for {len(summaries)} subtopics.")

        return summaries

    def create_topic_summaries(self, overwrite: Optional[bool] = None):
        """
        Create summaries for each topic from subtopic summaries.

        Args:
            overwrite (Optional[bool]): Whether to overwrite existing output file

        Returns:
            List[Dict]: List of summaries for each topic
        """
        # Use instance values if not specified
        overwrite = self.overwrite if not overwrite else overwrite

        # Get standard file paths
        subtopic_summaries_json_path = self.path_manager.get_subtopic_summaries_path()
        output_path = self.path_manager.get_topic_summaries_path()

        # Check if file exists and should be skipped
        if self._should_skip_existing(output_path):
            return

        # Load analysis data directly to DataFrame
        df = pd.read_json(subtopic_summaries_json_path)

        # Quick fix: Replace topic name (TODO: Fix naming inconsistency in upstream data)
        df["topic"] = df["topic"].replace("Climate science", "Carbon Accounting & Integrity")

        # Select the appropriate prompt file based on project_type
        topic_prompt_path = self._get_prompt_path(
            TOPIC_RESUME_CURRENT_PROMPT_PATH, TOPIC_RESUME_FUTURE_PROMPT_PATH
        )

        # Load the topic resume prompt
        with open(topic_prompt_path, "r") as f:
            print(f"Using topic prompt: {topic_prompt_path}")
            topic_resume_system_prompt = f.read()

        # Template for the full message
        topic_summary_prompt_template = """
        {context_content}

        -------
        Carefully taking into account the above instructions, please produce the aggregated overview paragraph for the provided topic analysis:

        ```json
        {input_data}
        ```
        """

        summaries = []
        # Group by topic
        grouped = df.groupby("topic")

        total_groups = len(grouped)
        for idx, (topic, group) in enumerate(grouped, 1):
            logger.info(f"Processing topic {idx}/{total_groups}: {topic}")
            # Convert group data to dict records
            group_data = group.to_dict("records")

            topic_summary_message = topic_summary_prompt_template.format(
                context_content=topic_resume_system_prompt,
                input_data=json.dumps(group_data, indent=2),
            )

            # Get response from Mistral
            chat_response = self.mistral_client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": topic_summary_message}],
                response_format={"type": "json_object"},
                temperature=MODEL_TEMPERATURE,
            )

            summary_json = self._validate_and_fix_llm_response(
                chat_response.choices[0].message.content, REQUIRED_FIELDS_FOR_TOPIC_SUMMARIES
            )
            summaries.append(summary_json)

            time.sleep(1)  # Rate limiting

        # Save summaries using the helper method
        self._save_json_output(summaries, output_path)
        logger.info(f"Created summaries for {len(summaries)} topics.")

        return summaries

    def create_topic_main_insights(self, overwrite: Optional[bool] = None):
        """
        Generate main insights for the project based on topic summaries.

        Args:
            overwrite (Optional[bool]): Whether to overwrite existing output file

        Returns:
            Dict: Project main idea
        """
        # Use instance values if not specified
        overwrite = self.overwrite if not overwrite else overwrite

        # Get standard file paths
        topic_summaries_json_path = self.path_manager.get_topic_summaries_path()
        output_path = self.path_manager.get_main_insights_path()

        # Check if file exists and should be skipped
        if self._should_skip_existing(output_path):
            return load_json_file(output_path)

        # Load topic summaries data
        topic_summaries = load_json_file(topic_summaries_json_path)

        # Load the project main idea prompt
        with open(PROJECT_MAIN_IDEA_PROMPT_PATH, "r") as f:
            project_main_insight_prompt = f.read()

        # Template for the full message
        main_insight_prompt_template = """
        {context_content}

        -------
        Carefully taking into account the above instructions, please produce the project main insights based on these topic summaries:

        ```json
        {input_data}
        ```
        """

        main_insight_message = main_insight_prompt_template.format(
            context_content=project_main_insight_prompt,
            input_data=json.dumps(topic_summaries, indent=2),
        )

        # Get response from Mistral
        chat_response = self.mistral_client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": main_insight_message}],
            response_format={"type": "json_object"},
            temperature=MODEL_TEMPERATURE,
        )

        main_insight_json = self._validate_and_fix_llm_response(
            chat_response.choices[0].message.content, REQUIRED_FIELDS_FOR_MAIN_INSIGHTS
        )

        # Save main idea using the helper method
        self._save_json_output(main_insight_json, output_path)
        logger.info(f"Created project main idea.")

        return main_insight_json

    def update_project_metadata(self) -> Dict:
        """
        Creates or updates the project metadata file with timestamp and model information.

        Returns:
            Dict: Updated metadata
        """
        # Get path for metadata file in the analysis directory
        metadata_path = os.path.join(self.path_manager.get_analysis_dir(), "metadata.json")

        # Initialize metadata with current information
        metadata = {
            "project_name": self.path_manager.project_name,
            "model_version": self.model,
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # If metadata file exists, load it and update only necessary fields
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    existing_metadata = json.load(f)
                    # Preserve existing fields, update only our specified fields
                    metadata = {**existing_metadata, **metadata}
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(
                    f"Error loading existing metadata file: {str(e)}. Creating new metadata."
                )

        # Save the updated metadata
        self._save_json_output(metadata, metadata_path)
        logger.info("Updated project metadata")

        return metadata

    def set_project_type(self, project_type: Literal["current", "future"]) -> None:
        """
        Set the project type for analysis.

        Args:
            project_type (str): Type of project - "current" (ongoing) or "future" (planned)
        """
        if project_type not in ["current", "future"]:
            raise ValueError("Project type must be 'current' or 'future'")

        self.project_type = project_type
        logger.info(f"Project type set to: {self.project_type}")

    def process_project(self) -> None:
        """
        Process a complete project through the entire pipeline.

        Args:
            project_folder (str): Path to the project folder
        """
        total_start_time = time.time()
        logger.info(f"Starting analysis pipeline for project: {self.path_manager.project_name}")

        # Step 1: Extract project overview data
        logger.info("Step 1/5: Extracting project overview data")
        step_start_time = time.time()
        overview_data = self.extract_project_overview_data()
        logger.info(
            f"✓ Project overview extraction completed in {(time.time() - step_start_time) / 60:.2f} minutes"
        )

        # Get project_type from overview_data, default to "future" if not present or null
        if "project_type" in overview_data and overview_data["project_type"] != "":
            self.set_project_type(overview_data["project_type"])
        else:
            logger.warning(
                "No project_type found in overview data or value is null, defaulting to 'future'"
            )
            self.set_project_type("future")

        # Step 2: Analyze due diligence criteria
        logger.info("Step 2/5: Analyzing due diligence criteria")
        step_start_time = time.time()
        self.analyze_due_diligence_criteria()
        logger.info(
            f"✓ Due diligence analysis completed in {(time.time() - step_start_time) / 60:.2f} minutes"
        )

        # Step 3: Create subtopic summaries
        logger.info("Step 3/5: Creating subtopic summaries")
        step_start_time = time.time()
        self.create_subtopic_summaries()
        logger.info(
            f"✓ Subtopic summaries created in {(time.time() - step_start_time) / 60:.2f} minutes"
        )

        # Step 4: Create topic summaries
        logger.info("Step 4/5: Creating topic summaries")
        step_start_time = time.time()
        self.create_topic_summaries()
        logger.info(
            f"✓ Topic summaries created in {(time.time() - step_start_time) / 60:.2f} minutes"
        )

        logger.info("Step 5/5: Generating main project insights")
        step_start_time = time.time()
        self.create_topic_main_insights()
        logger.info(
            f"✓ Main insights generated in {(time.time() - step_start_time) / 60:.2f} minutes"
        )

        # Step 6: Update project metadata
        logger.info("Updating project metadata")
        self.update_project_metadata()

        total_time = time.time() - total_start_time
        minutes, seconds = divmod(total_time, 60)
        logger.info(
            f"Project analysis pipeline completed in {int(minutes)} minutes {seconds:.2f} seconds"
        )
