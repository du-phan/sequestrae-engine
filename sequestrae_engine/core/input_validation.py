from sequestrae_engine.core.constants import LATEST_METHOD_VERSIONS
from sequestrae_engine.core.exceptions import SequestraeValidationError
from sequestrae_engine.core.utilities import load_schema, remove_empty_dicts, validate_json_data
from sequestrae_engine.methodologies.factory import MethodologyFactory


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
    """
    validated_methods = []
    errors = []
    ignored_fields_messages = {}

    for methodology_dict in methodology_list:
        name = methodology_dict.get("name")
        version = methodology_dict.get("version", LATEST_METHOD_VERSIONS.get(name))

        if not version:
            errors.append(
                {"context": f"{name}", "message": f"No version specified or available for {name}."}
            )
            continue

        try:
            specific_schema = load_schema("methodology", methodology=name, version=version)
            # Rebuild user inputs based on methodology schema and track any ignored fields
            rebuilt_inputs, ignored_fields = rebuild_user_inputs(user_input, specific_schema)

            # Instantiate the methodology class and validate inputs
            methodology_instance = MethodologyFactory.get_methodology(name, version)
            methodology_instance.validate_inputs(rebuilt_inputs)

            validated_methods.append((name, version))

            if ignored_fields:
                ignored_fields_messages[f"{name} {version}"] = ignored_fields

        except SequestraeValidationError as e:
            errors.append({"context": f"{name} {version} inputs", "message": e.errors})
        except Exception as e:
            errors.append({"context": f"{name} {version}", "message": str(e)})

    return validated_methods, errors, ignored_fields_messages


def validate_input(data):
    """
    Validates the input data against methodology-specific schemas.

    :param data: Dictionary containing 'user_inputs' and 'methodologies'.
                 'user_inputs' is a dictionary of user-provided inputs.
                 'methodologies' is a list of dictionaries, each containing 'name' and 'version' of the methodology.
    :return: A tuple containing:
             - validated_methods: A list of tuples with validated methodology names and versions.
             - methodology_errors: A dictionary of errors encountered during validation.
             - ignored_fields_messages: A dictionary of ignored fields for each methodology.
    :raises SequestraeValidationError: If there are errors in the input data or no methodologies are validated.
    """
    errors = []
    user_input = data.get("user_inputs")
    methodology_list = data.get("methodologies")

    if not user_input:
        errors.append(
            {
                "context": "user_inputs",
                "message": "Missing 'user_inputs' section in the input data.",
            }
        )

    if len(user_input) == 0:
        errors.append(
            {
                "context": "user_inputs",
                "message": "No user inputs specified for validation.",
            }
        )

    if not methodology_list:
        errors.append(
            {
                "context": "methodologies",
                "message": "Missing 'methodologies' section in the input data.",
            }
        )

    methodology_list = remove_empty_dicts(methodology_list)

    if len(methodology_list) == 0:
        errors.append(
            {
                "context": "methodologies",
                "message": "No methodologies specified for validation.",
            }
        )

    # Stop here if there are major problems with the input data
    if errors:
        raise SequestraeValidationError(errors)
    else:
        validated_methods, methodology_errors, ignored_fields_messages = (
            validate_methodology_inputs(user_input, methodology_list)
        )

        # in case there is problem with all the required methodologies, raise an error
        if not validated_methods:
            raise SequestraeValidationError(methodology_errors)

        return validated_methods, methodology_errors, ignored_fields_messages
