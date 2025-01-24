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
