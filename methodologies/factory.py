class MethodologyFactory:
    _registry = {}

    @classmethod
    def register_methodology(cls, name, version, methodology_cls):
        cls._registry[(name, version)] = methodology_cls

    @classmethod
    def get_methodology(cls, name, version):
        methodology_cls = cls._registry.get((name, version))
        if not methodology_cls:
            raise ValueError(f"Methodology {name} version {version} not found.")
        return methodology_cls()
