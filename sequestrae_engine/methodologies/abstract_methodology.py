from abc import ABC, abstractmethod


class BaseMethodology(ABC):
    """
    Abstract base class for all methodologies.
    """

    # Methodology metadata to be defined in subclasses
    methodology_name = None
    methodology_version = None

    @abstractmethod
    def validate_inputs(self, user_input):
        """
        Validates inputs specific to the methodology.
        :param user_input: Dictionary of user inputs.
        :raises: ValidationError if validation fails.
        """
        pass
