import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from sequestrae_engine.core.utilities import get_json_files, load_json_file
from sequestrae_engine.db.client import SupabaseClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def populate_audit_reports(project_folder_path: str, client: SupabaseClient):
    """Populate the audit_report_info table with JSON data."""
    try:
        json_path_list = get_json_files(project_folder_path)
        logger.info(f"Found {len(json_path_list)} JSON files")

        json_list = []
        for json_path in json_path_list:
            try:
                data = load_json_file(json_path)
                json_list.append(data)
                logger.info(f"Loaded {json_path}")
            except Exception as e:
                logger.error(f"Error loading {json_path}: {e}")
                continue

        if not json_list:
            raise ValueError("No valid JSON files found to insert")

        response = client.table("audit_report_info").insert(json_list).execute()

        logger.info(f"Successfully inserted {len(json_list)} records")

    except Exception as e:
        logger.error(f"Failed to populate audit reports: {e}")
        raise e


def populate_feedstock_evaluation_table(project_folder_path: str, client: SupabaseClient):
    """Populate the feedstock_evaluation table with JSON data."""
    try:
        json_path_list = get_json_files(project_folder_path)
        feestock_analysis_json_list = [
            json_path for json_path in json_path_list if "feedstock_analysis" in json_path
        ]
        logger.info(f"Found {len(feestock_analysis_json_list)} feestock analysis JSON files")

        json_list = []
        for json_path in feestock_analysis_json_list:
            try:
                list_of_dict = load_json_file(json_path)

                # get the file name but remove the extension `feedstock_analysis` and replace the .json by .md
                audit_file = Path(json_path).stem.replace("_feedstock_analysis", "") + ".md"

                for dct in list_of_dict:
                    analysis_content = dct.get("analysis")
                    for criteria_item in analysis_content:
                        criteria_item["audit_file"] = audit_file
                        # TODO: temporary fix to rename the keys, we should update the prompts instead
                        criteria_item["missing_or_contradictory_data"] = criteria_item.pop(
                            "missingOrContradictoryData"
                        )
                        json_list.append(criteria_item)

                logger.info(f"Loaded {json_path}")
            except Exception as e:
                logger.error(f"Error loading {json_path}: {e}")
                continue

        if not json_list:
            raise ValueError("No valid JSON files found to insert")

        response = client.table("feestock_evaluation").insert(json_list).execute()

        logger.info(f"Successfully inserted {len(json_list)} records")

    except Exception as e:
        logger.error(f"Failed to populate feedstock evaluation: {e}")
        raise e


def populate_project_analysis_table(meta_folder_path: str, registry: str, client: SupabaseClient):
    """Populate the project_analysis table with due diligence analysis data."""
    # Define expected schema fields
    required_fields = {
        "topic",
        "sub_topic",
        "risk_factor",
        "question",
        "short_answer",
        "long_answer",
        "detail_level",
        "missing_data",
        "contradictory_data",
        "is_hallucination",
        "hallucination_reasoning",
    }

    try:
        # Get all project folders
        project_folders = [f for f in Path(meta_folder_path).iterdir() if f.is_dir()]
        logger.info(f"Found {len(project_folders)} project folders")

        all_records = []
        for project_folder in project_folders:
            try:
                project_name = project_folder.name.replace(" ", "_")
                analysis_file = (
                    project_folder
                    / "analysis"
                    / f"{project_name}_analysis_mistral-large-latest.json"
                )

                if not analysis_file.exists():
                    logger.warning(f"Analysis file not found for project: {project_name}")
                    continue

                analysis_data = load_json_file(analysis_file)

                # Validate each record before adding
                valid_records = []
                has_invalid_records = False

                for record in analysis_data:
                    record_fields = set(record.keys())

                    # Check for missing required fields
                    missing_fields = required_fields - record_fields
                    if missing_fields:
                        has_invalid_records = True
                        logger.warning(
                            f"Project {project_name} has records with missing fields: {missing_fields}. "
                            f"Skipping entire project for data consistency."
                        )
                        break

                    # Ensure boolean type for is_hallucination
                    record["is_hallucination"] = bool(record["is_hallucination"])

                    # Add project metadata
                    record["project_name"] = project_name
                    record["registry"] = registry
                    valid_records.append(record)

                if not has_invalid_records and valid_records:
                    all_records.extend(valid_records)
                    logger.info(f"Processed analysis for project: {project_name}")

            except Exception as e:
                logger.error(f"Error processing project folder {project_folder}: {e}")
                continue

        if not all_records:
            raise ValueError("No valid analysis records found to insert")

        response = client.table("project_analysis").insert(all_records).execute()
        logger.info(f"Successfully inserted {len(all_records)} analysis records")

    except Exception as e:
        logger.error(f"Failed to populate project analysis: {e}")
        raise e
