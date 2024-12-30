import json


class ValidationError(Exception):
    """
    Custom exception for validation errors with structured feedback.
    """

    def __init__(self, errors):
        """
        :param errors: A list of dictionaries detailing validation errors.
        """
        self.errors = errors

    def __str__(self):
        return json.dumps(self.errors, indent=2)
