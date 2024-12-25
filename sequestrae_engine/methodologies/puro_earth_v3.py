from .abstract_methodology import BaseMethodology


class PuroEarthV3(BaseMethodology):
    def validate_inputs(self, inputs):
        pass

    def calculate_removals(self, inputs):
        pass

    def get_metadata(self):
        return {"framework": "Puro.earth", "version": "v3"}

    def format_output(self, results):
        pass
