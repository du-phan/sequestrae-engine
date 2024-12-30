from sequestrae_engine.core.constants import LATEST_METHOD_VERSIONS
from sequestrae_engine.core.exceptions import SequestraeValidationError
from sequestrae_engine.core.utilities import load_schema, validate_json_data
from sequestrae_engine.methodologies.factory import MethodologyFactory


def validate_user_inputs(input_dict):
    """
    Validates the user inputs against the reference input schema in `data/input_schema.json`.

    :param input_dict: Dictionary of user-provided inputs.
    :raises SequestraeValidationError: If the user inputs do not conform to the shared schema.
    """
    schema_json = load_schema("user_input")
    validate_json_data(input_dict, schema_json, context="user inputs")


def rebuild_user_inputs(user_inputs, schema):
    """
    Rebuilds the user inputs dictionary to include only the fields defined in the current methodology schema,
    including nested properties.

    :param user_inputs: Dictionary containing the original user inputs.
    :param schema: The schema for the specific methodology.
    :return: A rebuilt dictionary with only the relevant fields and a list of ignored fields.
    """
    schema_properties = schema.get("properties", {})
    rebuilt_inputs = {}
    ignored_fields = []

    for field, field_schema in schema_properties.items():
        if field in user_inputs:
            # If the field is an object, recurse into its properties
            if field_schema.get("type") == "object" and "properties" in field_schema:
                sub_rebuilt, sub_ignored = rebuild_user_inputs(user_inputs[field], field_schema)
                rebuilt_inputs[field] = sub_rebuilt
                ignored_fields.extend([f"{field}.{sub_field}" for sub_field in sub_ignored])
            else:
                # Direct field
                rebuilt_inputs[field] = user_inputs[field]
        else:
            # Field not in user inputs; treat as ignored
            ignored_fields.append(field)

    # Add any top-level ignored fields
    ignored_fields.extend([field for field in user_inputs.keys() if field not in schema_properties])
    return rebuilt_inputs, ignored_fields


def validate_methodology_inputs(user_input, methodology_list):
    """
    Validates user inputs against methodology-specific rules.

    :param user_input: Dictionary of user inputs.
    :param methodology_list: List of dictionaries containing methodology-specific configurations.
    :return: Tuple of (validated_methods, errors, ignored_fields_messages).
             - `validated_methods`: List of validated methodologies (name, version).
             - `errors`: A dictionary of validation errors for failed methodologies.
             - `ignored_fields_messages`: A dictionary of ignored fields for each methodology.
    """
    validated_methods = []
    errors = {}
    ignored_fields_messages = {}

    for methodology_dict in methodology_list:
        name = methodology_dict.get("name")
        version = methodology_dict.get("version", LATEST_METHOD_VERSIONS.get(name))

        if not version:
            errors[f"{name}"] = [
                {"context": "version", "message": f"No version specified or available for {name}."}
            ]
            continue

        try:
            # Load the methodology-specific schema
            specific_schema = load_schema("methodology", methodology=name, version=version)

            # Rebuild inputs based on the methodology schema
            rebuilt_inputs, ignored_fields = rebuild_user_inputs(user_input, specific_schema)

            # Validate the methodology-specific inputs
            validate_json_data(rebuilt_inputs, specific_schema, context=f"{name} v{version} inputs")
            validated_methods.append((name, version))

            # Store ignored fields in a separate message dictionary
            if ignored_fields:
                ignored_fields_messages[f"{name} {version}"] = ignored_fields

        except SequestraeValidationError as e:
            # Log validation errors for this methodology
            errors[f"{name} {version}"] = {
                "context": f"{name} v{version} inputs",
                "message": str(e),
            }
        except Exception as e:
            # Handle unexpected exceptions
            errors[f"{name} {version}"] = {
                "context": f"{name} v{version}",
                "message": f"Unexpected error: {str(e)}",
            }

    return validated_methods, errors, ignored_fields_messages


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
    - Messages regarding ignored fields for each methodology.

    :param data: Dictionary containing the full input data, including:
                 - "user_inputs": The shared inputs provided by the user for the project evaluation.
                 - "methodologies": A list of methodologies the user wants to test, each containing:
                   - "name": The name of the methodology (e.g., "PuroEarth", "Verra").
                   - "version": The version of the methodology to use (e.g., "v3").
    :return: Tuple of (validated_methods, error_log, ignored_fields_messages).
             - `validated_methods`: List of methodologies that passed validation.
             - `error_log`: A dictionary of validation errors for failed methodologies.
             - `ignored_fields_messages`: A dictionary of ignored fields for each methodology.
    :raises: SequestraeValidationError if validation fails for all methodologies, leaving no valid methods to process.
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
        raise SequestraeValidationError(errors)

    # Validate user inputs
    try:
        validate_user_inputs(user_input)
    except SequestraeValidationError as e:
        errors.append({"context": "user_inputs", "message": str(e)})

    # Validate the methodologies specified by the user
    validated_methods, methodology_errors, ignored_fields_messages = validate_methodology_inputs(
        user_input, methodology_list
    )
    errors.extend(methodology_errors.values())

    # Raise consolidated errors if all methodologies fail
    if not validated_methods:
        raise SequestraeValidationError(errors)

    return validated_methods, methodology_errors, ignored_fields_messages
