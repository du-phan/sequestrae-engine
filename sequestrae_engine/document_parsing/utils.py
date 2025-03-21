import json
import logging
import os
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def ensure_directory_exists(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def create_metadata_files(project_root, csv_path):
    """
    Reads project URLs from a CSV file and creates metadata.json files in the analysis/ folders
    of the corresponding projects if they do not already exist.

    :param project_root: Root directory containing project folders.
    :param csv_path: Path to the CSV file containing project names and URLs.
    """
    # Load the project_url.csv file
    df = pd.read_csv(csv_path)

    # Ensure column names are lowercase and stripped for consistency
    df.columns = df.columns.str.strip().str.lower()

    # Check that expected columns exist
    if "project_name" not in df.columns or "project_url" not in df.columns:
        raise ValueError("CSV file must contain 'project_name' and 'project_url' columns")

    # Create a lookup dictionary
    project_url_dict = dict(zip(df["project_name"].str.strip(), df["project_url"].str.strip()))

    # Traverse the project folders
    for registry in ["puro", "riverse", "verra"]:
        registry_path = os.path.join(project_root, registry)

        if not os.path.exists(registry_path):
            continue  # Skip if registry folder does not exist

        for project_name in os.listdir(registry_path):
            project_path = os.path.join(registry_path, project_name)
            analysis_path = os.path.join(project_path, "analysis")
            metadata_file = os.path.join(analysis_path, "metadata.json")

            if os.path.isdir(analysis_path):  # Ensure analysis folder exists
                if not os.path.exists(metadata_file):  # Only create if not exists
                    project_url = project_url_dict.get(project_name)
                    if project_url:
                        metadata = {"project_url": project_url}
                        with open(metadata_file, "w", encoding="utf-8") as f:
                            json.dump(metadata, f, indent=4)
                        print(f"Created metadata.json for {project_name}")
                    else:
                        print(f"No URL found for {project_name}, skipping...")


# Example usage
# create_metadata_files("project_folder", "/mnt/data/project_url.csv")
