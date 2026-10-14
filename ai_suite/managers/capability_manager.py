class CapabilityManager:
    def __init__(self, sr): pass
    def request(self, cap): return DummyLogger()
class DummyLogger:
    def log(self, msg): print(msg)
