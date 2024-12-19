# This file will contain the abstract base class for different methodologies.

from abc import ABC, abstractmethod


class BaseMethodology(ABC):
    @abstractmethod
    def validate_inputs(self, inputs):
        pass

    @abstractmethod
    def calculate_removals(self, inputs):
        pass

    @abstractmethod
    def get_metadata(self):
        pass

    @abstractmethod
    def format_output(self, results):
        pass
