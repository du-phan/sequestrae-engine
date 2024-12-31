from sequestrae_engine.core.exceptions import SequestraeValidationError
from sequestrae_engine.core.utilities import load_schema, validate_json_data
from sequestrae_engine.methodologies.abstract_methodology import BaseMethodology


class PuroEarthV3(BaseMethodology):
    """
    Implementation of PuroEarth v3 methodology.
    """

    methodology_name = "puro_earth"
    methodology_version = "v3"

    def validate_inputs(self, user_input):
        """
        Validates user inputs against PuroEarth-specific rules.
        """
        # Load schema using class attributes
        schema_json = load_schema(
            "methodology", methodology=self.methodology_name, version=self.methodology_version
        )

        # Validate against JSON schema
        validate_json_data(
            user_input,
            schema_json,
            context=f"{self.methodology_name} {self.methodology_version} inputs",
        )

        # Example of additional custom validation
        moisture_content = user_input.get("feedstock", {}).get("moisture_content")
        if moisture_content is not None and (moisture_content < 10 or moisture_content > 50):
            raise SequestraeValidationError(
                [
                    {
                        "field": "feedstock.moisture_content",
                        "expected": "between 10 and 50",
                        "actual": moisture_content,
                        "context": f"{self.methodology_name} {self.methodology_version}",
                    }
                ]
            )
