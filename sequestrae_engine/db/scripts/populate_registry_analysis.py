import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from sequestrae_engine.core.utilities import load_json_file
from sequestrae_engine.db.client import SupabaseClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def populate_registry_analysis(registries_dir: str, client: SupabaseClient):
    """
    Parse multiple registry folders and upload project analysis data to Supabase tables.

    Args:
        registries_dir: Path to the root folder containing multiple registry folders
        client: SupabaseClient instance for database operations

    Returns:
        Dictionary mapping table names to their inserted content lists
    """
    try:
        registries_path = Path(registries_dir)
        if not registries_path.exists() or not registries_path.is_dir():
            raise ValueError(f"Directory not found or is not a directory: {registries_path}")

        # Find all registry folders (direct subdirectories of the root)
        registry_folders = [f for f in registries_path.iterdir() if f.is_dir()]

        if not registry_folders:
            raise ValueError(f"No registry folders found in {registries_path}")

        logger.info(f"Found {len(registry_folders)} registry folders to process")

        # Initialize IDs and table content lists
        project_id = 1
        detailed_answer_id = 1
        subtopic_summary_id = 1
        risk_factor_id = 1
        risk_factor_point_id = 1
        topic_summary_id = 1

        projects_table_content_list = []
        detailed_answers_table_content_list = []
        subtopic_summaries_table_content_list = []
        risk_factors_table_content_list = []
        risk_factor_points_table_content_list = []
        topic_summaries_table_content_list = []

        # Process each registry folder
        for registry_folder in registry_folders:
            registry_name = registry_folder.name
            logger.info(f"Processing registry: {registry_name}")

            try:
                # Find all project folders within the registry directory
                project_folders = [f for f in registry_folder.iterdir() if f.is_dir()]

                if not project_folders:
                    logger.warning(
                        f"No project folders found in registry: {registry_name}, skipping..."
                    )
                    continue

                logger.info(
                    f"Found {len(project_folders)} project folders in registry '{registry_name}'"
                )

                # Process each project folder
                for project_folder in project_folders:
                    try:
                        project_name = project_folder.name.replace(" ", "_")
                        logger.info(f"Processing project: {project_name}")

                        # Define expected analysis file names
                        detailed_answers_filename = (
                            f"{project_name}_analysis_mistral-large-latest.json"
                        )
                        subtopic_summaries_filename = (
                            f"{project_name}_analysis_mistral-large-latest_subtopic_summaries.json"
                        )
                        topic_summaries_filename = f"{project_name}_analysis_mistral-large-latest_subtopic_summaries_topic_summaries.json"

                        # Find analysis files
                        analysis_folder = project_folder / "analysis"
                        if not analysis_folder.exists() or not analysis_folder.is_dir():
                            logger.warning(f"Analysis folder not found for project: {project_name}")
                            continue

                        analysis_files = [f for f in analysis_folder.iterdir()]
                        filename_to_path = {path.name: path for path in analysis_files}

                        # Verify all required files exist
                        file_path_dict = {}
                        required_files = [
                            detailed_answers_filename,
                            subtopic_summaries_filename,
                            topic_summaries_filename,
                        ]

                        missing_files = []
                        for filename in required_files:
                            if filename in filename_to_path:
                                file_path_dict[filename] = filename_to_path[filename]
                            else:
                                missing_files.append(filename)

                        if missing_files:
                            logger.warning(
                                f"Missing required analysis files for project {project_name}: {missing_files}"
                            )
                            continue

                        # Add project to projects table
                        projects_table_content_list.append(
                            {
                                "project_id": project_id,
                                "project_name": project_name,
                                "registry": registry_name,
                            }
                        )

                        # Process detailed answers
                        try:
                            detailed_answers = load_json_file(
                                file_path_dict.get(detailed_answers_filename)
                            )
                            for detailed_answer in detailed_answers:
                                detailed_answer_dict = {
                                    "detailed_answer_id": detailed_answer_id,
                                    "project_id": project_id,
                                    "topic": detailed_answer.get("topic"),
                                    "sub_topic": detailed_answer.get("sub_topic"),
                                    "risk_factor": detailed_answer.get("risk_factor"),
                                    "question": detailed_answer.get("question"),
                                    "short_answer": detailed_answer.get("short_answer"),
                                    "long_answer": detailed_answer.get("long_answer"),
                                    "detail_level": detailed_answer.get("detail_level"),
                                    "evidence_found": detailed_answer.get("evidence_found"),
                                    "missing_data": detailed_answer.get("missing_data"),
                                    "contradictory_data": detailed_answer.get("contradictory_data"),
                                    "is_hallucination": (
                                        None
                                        if detailed_answer.get("is_hallucination") == ""
                                        else bool(detailed_answer.get("is_hallucination"))
                                    ),
                                    "hallucination_reasoning": detailed_answer.get(
                                        "hallucination_reasoning"
                                    ),
                                }
                                detailed_answers_table_content_list.append(detailed_answer_dict)
                                detailed_answer_id += 1
                        except Exception as e:
                            logger.error(
                                f"Error processing detailed answers for {project_name}: {e}"
                            )

                        # Process subtopic summaries
                        try:
                            subtopic_summaries = load_json_file(
                                file_path_dict.get(subtopic_summaries_filename)
                            )
                            for subtopic_summary in subtopic_summaries:
                                subtopic_summary_dict = {
                                    "subtopic_summary_id": subtopic_summary_id,
                                    "project_id": project_id,
                                    "topic": subtopic_summary.get("topic"),
                                    "sub_topic": subtopic_summary.get("sub_topic"),
                                    "overall_summary": subtopic_summary.get("overall_summary"),
                                }
                                subtopic_summaries_table_content_list.append(subtopic_summary_dict)

                                # Process risk factors within each subtopic
                                for risk_factor in subtopic_summary.get("analysis", []):
                                    risk_factor_dict = {
                                        "risk_factor_id": risk_factor_id,
                                        "subtopic_summary_id": subtopic_summary_id,
                                        "risk_factor_name": risk_factor.get("risk_factor"),
                                    }
                                    risk_factors_table_content_list.append(risk_factor_dict)

                                    # Process points for each risk factor
                                    for point_type in [
                                        "strengths",
                                        "considerations",
                                        "recommended_actions",
                                    ]:
                                        for point_info in risk_factor.get(point_type, []):
                                            risk_factor_points_dict = {
                                                "risk_factor_point_id": risk_factor_point_id,
                                                "risk_factor_id": risk_factor_id,
                                                "point_type": point_type,
                                            }

                                            # Handle different structures based on point type
                                            if point_type == "recommended_actions":
                                                risk_factor_points_dict["main_idea"] = (
                                                    point_info.get("action")
                                                )
                                            else:
                                                risk_factor_points_dict["main_idea"] = (
                                                    point_info.get("main_idea")
                                                )

                                            risk_factor_points_dict["explanation"] = point_info.get(
                                                "explanation"
                                            )
                                            risk_factor_points_table_content_list.append(
                                                risk_factor_points_dict
                                            )
                                            risk_factor_point_id += 1

                                    risk_factor_id += 1
                                subtopic_summary_id += 1
                        except Exception as e:
                            logger.error(
                                f"Error processing subtopic summaries for {project_name}: {e}"
                            )

                        # Process topic summaries
                        try:
                            topic_summaries = load_json_file(
                                file_path_dict.get(topic_summaries_filename)
                            )
                            for topic_summary in topic_summaries:
                                topic_summary_dict = {
                                    "topic_summary_id": topic_summary_id,
                                    "project_id": project_id,
                                    "topic": topic_summary.get("topic"),
                                    "topic_introduction": topic_summary.get("introduction"),
                                    "topic_summary": topic_summary.get("topic_summary"),
                                }
                                topic_summaries_table_content_list.append(topic_summary_dict)
                                topic_summary_id += 1
                        except Exception as e:
                            logger.error(
                                f"Error processing topic summaries for {project_name}: {e}"
                            )

                        logger.info(f"Successfully processed project: {project_name}")
                        project_id += 1

                    except Exception as e:
                        logger.error(f"Error processing project folder {project_folder}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error processing registry {registry_name}: {str(e)}")
                continue

        # Map table names to their content
        table_data_mapping = {
            "projects": projects_table_content_list,
            "detailed_answers": detailed_answers_table_content_list,
            "subtopic_summaries": subtopic_summaries_table_content_list,
            "risk_factors": risk_factors_table_content_list,
            "risk_factor_points": risk_factor_points_table_content_list,
            "topic_summaries": topic_summaries_table_content_list,
        }

        # Insert data into Supabase tables (single API call per table)
        for table_name, table_content in table_data_mapping.items():
            if not table_content:
                logger.warning(f"No data to insert for table: {table_name}")
                continue

            logger.info(f"Inserting {len(table_content)} total records into {table_name} table")
            response = client.table(table_name).insert(table_content).execute()
            logger.info(f"Successfully inserted data into {table_name} table")

        return table_data_mapping

    except Exception as e:
        logger.error(f"Failed to populate registry analysis data: {e}")
        raise e


def main():
    """Example usage of the populate_registry_analysis function."""
    import os

    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Initialize Supabase client
    client = SupabaseClient.get_client()

    # Example usage
    registries_dir = "../../project_data/"

    # Populate database tables
    populate_registry_analysis(registries_dir, client)


if __name__ == "__main__":
    main()
