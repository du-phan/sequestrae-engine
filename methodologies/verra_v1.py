from .abstract_methodology import BaseMethodology


class VerraV1(BaseMethodology):
    def validate_inputs(self, inputs):
        pass

    def calculate_removals(self, inputs):
        pass

    def get_metadata(self):
        return {"framework": "Verra", "version": "v1"}

    def format_output(self, results):
        pass
