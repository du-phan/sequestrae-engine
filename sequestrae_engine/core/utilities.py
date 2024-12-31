import json
import logging
import os

from jsonschema import validate, validators

from sequestrae_engine.core.constants import LATEST_METHOD_VERSIONS
from sequestrae_engine.core.exceptions import SequestraeValidationError

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


def load_schema(schema_type, methodology=None, version=None):
    """
    Loads a JSON schema from the file system.

    :param schema_type: Type of schema to load ('user_input' or 'methodology').
    :param methodology: Name of the methodology (required if schema_type is 'methodology').
    :param version: Version of the methodology (optional, defaults to latest version).
    :return: Dictionary containing the JSON schema.
    :raises: FileNotFoundError, json.JSONDecodeError
    """
    base_path = os.path.dirname(__file__)

    if schema_type == "user_input":
        schema_path = os.path.join(base_path, "../data/input_schema.json")
    elif schema_type == "methodology":
        if not methodology:
            raise ValueError("Methodology name must be provided for methodology schema type.")
        if not version:
            version = LATEST_METHOD_VERSIONS.get(methodology)
        schema_path = os.path.join(
            base_path,
            f"../data/{methodology}/{methodology}_methodology_input_{version}.json",
        )
    else:
        raise ValueError("Invalid schema type. Must be 'user_input' or 'methodology'.")

    return read_json(schema_path)


def validate_json_data(json_dict, schema, context=""):
    """
    Validates a JSON data instance against a schema and returns all validation errors.

    :param json_dict: The JSON data instance to validate (typically a dictionary).
    :param schema: The JSON schema to validate against.
    :param context: Context information for error messages.
    :raises: SequestraeValidationError with all error messages if validation fails.
    """
    # Get the validator class from the schema
    validator_class = validators.validator_for(schema)
    validator = validator_class(schema)

    # Collect all errors
    errors = list(validator.iter_errors(json_dict))

    if errors:
        # Build comprehensive error message
        error_details = []
        for error in errors:
            path = " -> ".join(str(p) for p in error.path) if error.path else "root"
            error_details.append({"input_field": path, "message": error.message})

        raise SequestraeValidationError(error_details)


def remove_empty_dicts(data_list: list) -> list:
    """Remove empty dictionaries from a list.

    Args:
        data_list (list): List containing dictionaries

    Returns:
        list: List with empty dictionaries removed
    """
    return [d for d in data_list if d]  # Empty dicts evaluate to False
