from typing import Any
from ai_suite.core.workspace.types import NotificationPriority, NotificationDestination
from jarvis_ai.utils.logger import LOGGER

class NotificationManager:
    """Centralized notification routing across workspaces."""
    
    def __init__(self, event_bus: Any):
        self.event_bus = event_bus
        
    def notify(
        self, 
        title: str, 
        message: str, 
        priority: NotificationPriority = NotificationPriority.INFO,
        destination: NotificationDestination = NotificationDestination.TOAST
    ) -> None:
        """Pushes an alert to the requested destination."""
        
        if destination == NotificationDestination.LOG:
            if priority in (NotificationPriority.ERROR, NotificationPriority.SYSTEM):
                LOGGER.error(f"[{title}] {message}")
            elif priority == NotificationPriority.WARNING:
                LOGGER.warning(f"[{title}] {message}")
            else:
                LOGGER.info(f"[{title}] {message}")
            return
            
        if destination == NotificationDestination.VOICE:
            if hasattr(self.event_bus, "voiceCommandReceived"):
                # Ideally capability manager speaks this, but for now we log
                LOGGER.info(f"VOICE NOTIFICATION: {message}")
            return
            
        # For UI elements (TOAST, SIDEBAR, STATUS_BAR), we emit an event
        # that the active workspace UI can subscribe to and render
        if hasattr(self.event_bus, "systemNotification"):
            self.event_bus.systemNotification.emit(title, message, priority.value, destination.value)
        else:
            LOGGER.warning(f"No systemNotification signal found. Dropped UI alert: {message}")