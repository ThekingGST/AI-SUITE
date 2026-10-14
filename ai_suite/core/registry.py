class ServiceContainer:
    _services = {}

    @classmethod
    def register(cls, interface, impl):
        cls._services[interface] = impl

    @classmethod
    def get(cls, interface):
        return cls._services.get(interface)
