import pytest
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from sequestrae_engine.core.input_validation import validate_input


@pytest.fixture
def valid_user_input():
    return {
        "feedstock": {
            "feedstock_type": "forestry_residues",
            "moisture_content": 20,
            "sustainability_compliance": {"certification": "FSC"},
            "origin": "forest",
            "geography": "US",
        },
        "production_process": {
            "technology_type": "pyrolysis",
            "production_temperature": 600,
            "energy_source": "renewable",
            "process_emissions_control": True,
        },
        "biochar_properties": {"h_c_ratio": 0.5, "organic_carbon_content": 80, "ash_content": 5},
        "biochar_application": {
            "application_type": "soil",
            "co_benefits": {"soil_improvement": True, "biodiversity": False},
        },
        "lifecycle_emissions": {
            "baseline_emission_evidence": None,
            "process_emissions": {"pre_treatment": 1.0, "fugitive_emissions": None},
            "transportation_emissions": 0.5,
            "transport_mode": "road",
        },
    }


@pytest.fixture
def valid_methodology_list():
    return [{"name": "puro_earth", "version": "v3"}]


def test_valid_input(valid_user_input, valid_methodology_list):
    data = {"user_inputs": valid_user_input, "methodologies": valid_methodology_list}
    validated_methods, error_log, ignored_fields = validate_input(data)
    assert len(validated_methods) == 1
    assert not error_log


def test_missing_optional_fields(valid_user_input, valid_methodology_list):
    user_input = valid_user_input.copy()
    user_input["feedstock"].pop("origin")
    user_input["feedstock"].pop("geography")
    data = {"user_inputs": user_input, "methodologies": valid_methodology_list}
    validated_methods, error_log, ignored_fields = validate_input(data)
    assert len(validated_methods) == 1
    assert not error_log


def test_invalid_feedstock_type(valid_user_input, valid_methodology_list):
    user_input = valid_user_input.copy()
    user_input["feedstock"]["feedstock_type"] = "invalid_type"
    data = {"user_inputs": user_input, "methodologies": valid_methodology_list}
    with pytest.raises(ValidationError):
        validate_input(data)


def test_missing_required_fields(valid_user_input, valid_methodology_list):
    user_input = valid_user_input.copy()
    user_input["feedstock"].pop("feedstock_type")
    data = {"user_inputs": user_input, "methodologies": valid_methodology_list}
    with pytest.raises(JsonSchemaValidationError):
        validate_input(data)
