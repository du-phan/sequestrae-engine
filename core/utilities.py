import json
import logging
import os

# Configure logging to include the package name
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_json(file_path):
    """
    Reads a JSON file and returns the data as a dictionary.

    :param file_path: Path to the JSON file.
    :return: Dictionary containing data read from the JSON file.
    :raises: FileNotFoundError, json.JSONDecodeError
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r") as file:
        try:
            json_dict = json.load(file)
            logger.info(f"Successfully read JSON file: {file_path}")
            return json_dict
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from file {file_path}: {e}")
            raise e


def write_json(file_path, json_dict):
    """
    Writes a dictionary to a JSON file.

    :param file_path: Path to the JSON file.
    :param json_dict: Dictionary to write to the JSON file.
    :raises: TypeError, IOError
    """
    with open(file_path, "w") as file:
        try:
            json.dump(json_dict, file, indent=4)
            logger.info(f"Successfully wrote JSON to file: {file_path}")
        except TypeError as e:
            logger.error(f"Error encoding data to JSON for file {file_path}: {e}")
            raise e
        except IOError as e:
            logger.error(f"Error writing to file {file_path}: {e}")
            raise e
