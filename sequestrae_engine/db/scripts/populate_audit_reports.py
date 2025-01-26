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
                        criteria_item["evidence_found"] = criteria_item.pop("evidenceFound")
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
