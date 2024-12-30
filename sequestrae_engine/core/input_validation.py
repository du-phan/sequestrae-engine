from sequestrae_engine.core.constants import LATEST_METHOD_VERSIONS
from sequestrae_engine.core.exceptions import ValidationError
from sequestrae_engine.core.utilities import load_schema, validate_json_data
from sequestrae_engine.methodologies.factory import MethodologyFactory


def validate_user_inputs(input_dict):
    """
    Validates the user inputs against the reference input schema in `data/input_schema.json`.
    """
    schema_json = load_schema("user_input")
    validate_json_data(input_dict, schema_json, context="user inputs")


def validate_methodology_inputs(user_input, methodology_list):
    """
    Validates user inputs against methodology-specific rules.

    :param user_input: Dictionary of user inputs.
    :param methodology_list: List of dictionaries containing methodology-specific configurations.
    :return: Tuple of (validated_methods, errors).
    """
    validated_methods = []
    errors = {}

    for methodology_dict in methodology_list:
        name = methodology_dict.get("name")
        version = methodology_dict.get("version", LATEST_METHOD_VERSIONS.get(name))

        if not version:
            errors[f"{name}"] = [
                {"context": "version", "message": f"No version specified or available for {name}."}
            ]
            continue

        try:
            # Get the methodology instance
            methodology_instance = MethodologyFactory.get_methodology(name, version)

            # Validate inputs for the methodology
            methodology_instance.validate_inputs(user_input)
            validated_methods.append((name, version))  # Add valid methodology to the list
        except ValidationError as e:
            # Log validation errors for this methodology
            errors[f"{name} {version}"] = e.errors

    return validated_methods, errors


def validate_input(data):
    """
    Validates the entire input data, including the user inputs and the methodologies the user wants to test.

    This function performs the following steps:
    1. Validates the user-provided input data against the general schema (`user_inputs`).
    2. Checks each methodology specified by the user (name and version) to ensure the inputs are compatible with
       the specific requirements of that methodology.

    If validation for one or more methodologies fails, it does not stop the entire process. The function continues
    to validate and process other methodologies. At the end, it returns:
    - A list of methodologies that passed validation.
    - A structured error log detailing the issues for methodologies that failed validation.

    :param data: Dictionary containing the full input data, including:
                 - "user_inputs": The shared inputs provided by the user for the project evaluation.
                 - "methodologies": A list of methodologies the user wants to test, each containing:
                   - "name": The name of the methodology (e.g., "PuroEarth", "Verra").
                   - "version": The version of the methodology to use (e.g., "v3").
    :return: Tuple of (validated_methods, error_log).
             - `validated_methods`: List of methodologies that passed validation.
             - `error_log`: A dictionary of validation errors for failed methodologies.
    :raises: ValidationError if validation fails for all methodologies, leaving no valid methods to process.
    """
    errors = []

    # Extract user inputs and methodology list
    user_input = data.get("user_inputs")
    methodology_list = data.get("methodologies")

    # Check for missing required sections
    if not user_input:
        errors.append(
            {
                "context": "user_inputs",
                "message": "Missing 'user_inputs' section in the input data.",
            }
        )
    if not methodology_list:
        errors.append(
            {
                "context": "methodologies",
                "message": "Missing 'methodologies' section in the input data.",
            }
        )

    # If structure errors exist, raise immediately
    if errors:
        raise ValidationError(errors)

    # Validate user inputs
    try:
        validate_user_inputs(user_input)
    except ValidationError as e:
        errors.append({"context": "user_inputs", "message": str(e)})

    # Validate the methodologies specified by the user
    validated_methods, methodology_errors = validate_methodology_inputs(
        user_input, methodology_list
    )
    errors.extend(methodology_errors.values())

    # Raise consolidated errors if all methodologies fail
    if not validated_methods:
        raise ValidationError(errors)

    return validated_methods, methodology_errors
