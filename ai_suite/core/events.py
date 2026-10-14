from PyQt5.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    workspaceActivated = pyqtSignal(str)
    workspaceDeactivated = pyqtSignal(str)
    workspaceSuspended = pyqtSignal(str)
    workspaceResumed = pyqtSignal(str)
    workspaceChanged = pyqtSignal(str, str)
    
    # Assistant Lifecycle Events
    assistantRegistered = pyqtSignal(str)
    assistantReady = pyqtSignal(str)
    assistantBusy = pyqtSignal(str)
    assistantDelegated = pyqtSignal(str)
    assistantCompleted = pyqtSignal(str)
    assistantFailed = pyqtSignal(str)
    assistantStateChanged = pyqtSignal(str, str, str)  # id, old_state, new_state
    
    def __init__(self):
        super().__init__()
