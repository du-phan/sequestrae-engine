from sequestrae_engine.methodologies.puro_earth_v3 import PuroEarthV3
from sequestrae_engine.methodologies.verra_v1 import VerraV1


class MethodologyFactory:
    """
    Factory for creating and validating methodology-specific logic.
    """

    METHODOLOGY_CLASSES = {
        "puro_earth": {"v3": PuroEarthV3},
        "verra": {"v1": VerraV1},
    }

    @staticmethod
    def get_methodology(name, version):
        """
        Retrieve the methodology class for a given name and version.
        """
        try:
            return MethodologyFactory.METHODOLOGY_CLASSES[name][version]()
        except KeyError:
            raise ValueError(f"Unsupported methodology: {name} version {version}")
