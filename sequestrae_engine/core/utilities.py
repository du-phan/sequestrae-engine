import json
import logging
import os

from jsonschema import validate
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from sequestrae_engine.core.constants import LATEST_METHOD_VERSIONS

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

    :param schema_type: Type of schema to load ('shared' or 'methodology').
    :param methodology: Name of the methodology (required if schema_type is 'methodology').
    :param version: Version of the methodology (optional, defaults to latest version).
    :return: Dictionary containing the JSON schema.
    :raises: FileNotFoundError, json.JSONDecodeError
    """
    base_path = os.path.dirname(__file__)

    if schema_type == "shared":
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
        raise ValueError("Invalid schema type. Must be 'shared' or 'methodology'.")

    return read_json(schema_path)


def validate_json_data(json_dict, schema, context=""):
    """
    Validates a JSON data instance against a given schema.

    :param json_dict: The JSON data instance to validate (typically a dictionary).
    :param schema: The JSON schema to validate against.
    :param context: Context information for error messages.
    :raises: ValidationError with a clear error message if validation fails.
    """
    try:
        validate(instance=json_dict, schema=schema)
    except JsonSchemaValidationError as e:
        error_message = f"Validation error in {context}: {e.message}"
        raise JsonSchemaValidationError(error_message)