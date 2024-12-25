from sequestrae_engine.core.utilities import load_schema, validate_json_data


def validate_shared_inputs(shared_input_dict):
    """
    Validates the shared inputs against the shared schema.

    :param shared_input_dict: Dictionary containing shared inputs.
    :raises: ValidationError if validation fails.
    """
    schema_json = load_schema("shared")
    validate_json_data(shared_input_dict, schema_json, context="shared inputs")


def validate_methodology_inputs(methodology_list):
    """
    Validates the methodology-specific inputs against their respective schemas.

    :param methodology_list: List of dictionaries containing methodology-specific inputs.
    :raises: ValidationError if validation fails.
    """
    for methodology_dict in methodology_list:
        name = methodology_dict.get("name")
        version = methodology_dict.get("version")
        specific_input_dict = methodology_dict.get("specific_inputs")

        schema_json = load_schema("methodology", methodology=name, version=version)
        validate_json_data(specific_input_dict, schema_json, context=f"{name} methodology inputs")


def validate_input(data):
    """
    Validates the entire input data, including shared and methodology-specific inputs.

    :param data: Dictionary containing the entire input data.
    :raises: ValidationError if validation fails.
    """
    shared_input_dict = data.get("shared_inputs")
    methodology_list = data.get("methodologies")

    validate_shared_inputs(shared_input_dict)
    validate_methodology_inputs(methodology_list)
