"""AI Suite Boot Screen — Boot Controller and Worker.

Orchestrates the boot sequence. The BootWorker runs in a QThread to initialize
services without blocking the GUI, emitting BootStage signals as it progresses.
The BootController connects these signals to the BootWindow.
"""

from __future__ import annotations

import time
import sys
from typing import Dict, Any
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from ai_suite.ui.boot.boot_theme import BootStage, STAGE_CONFIG

# Service imports
from ai_suite.core.events import EventBus
from ai_suite.core.registry import ServiceContainer
from ai_suite.managers.assistant_manager import AssistantManager
from ai_suite.managers.session_manager import SessionManager
from ai_suite.managers.model_manager import ModelManager
from ai_suite.models.factory import ProviderFactory

# We will need the rest of the imports that were in main.py for initialization
# I will structure the worker first, then we can migrate the exact imports and logic
# from main.py in the next iteration if needed, but for now let's set up the structure.

class BootWorker(QThread):
    """Background thread that executes the actual application initialization."""
    
    stage_complete = pyqtSignal(BootStage)
    
    # Emits a dictionary of all constructed services and managers upon completion.
    finished_data = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.error = None
        self._skip_requested = False
        
    def skip(self):
        self._skip_requested = True
        
    def _sleep(self, seconds: float):
        """Sleeps in small increments to allow immediate skip."""
        steps = int(seconds / 0.1)
        for _ in range(steps):
            if self._skip_requested:
                break
            time.sleep(0.1)
        
    def run(self):
        try:
            services = {}
            
            # --- STAGE: CORE ---
            self.stage_complete.emit(BootStage.CORE)
            event_bus = EventBus()
            assistant_manager = AssistantManager(event_bus)
            session_manager = SessionManager(event_bus)
            provider_factory = ProviderFactory()
            model_manager = ModelManager(event_bus, provider_factory)
            
            services['event_bus'] = event_bus
            services['assistant_manager'] = assistant_manager
            services['session_manager'] = session_manager
            
            # --- STAGE: MEMORY ---
            self.stage_complete.emit(BootStage.MEMORY)
            from ai_suite.core.memory.storage import SQLiteStorageProvider
            from ai_suite.core.memory.engine import MemoryEngine
            from ai_suite.core.memory.context import ContextBuilder
            from shared.config.config_manager import ConfigManager
            
            storage_provider = SQLiteStorageProvider(db_path=ConfigManager.MEMORY_DB)
            memory_engine = MemoryEngine(event_bus, storage_provider)
            context_builder = ContextBuilder(memory_engine)
            
            # --- STAGE: HARDWARE ---
            from shared.hardware.manager import HardwareManager
            hw = HardwareManager()
            hw.detect_all()
            
            # --- STAGE: INTELLIGENCE ---
            self.stage_complete.emit(BootStage.INTELLIGENCE)
            from ai_suite.core.services.registry import ServiceRegistry
            from ai_suite.managers.capability_manager import CapabilityManager
            from ai_suite.intelligence import IntelligenceService
            from ai_suite.intelligence.hardware import CPUInspector, MemoryInspector, GPUInspector, BatteryInspector, DiskInspector, NetworkInspector
            from ai_suite.intelligence.system import WindowsInspector, ProcessInspector
            from ai_suite.intelligence.development import GitInspector, ProjectInspector, PythonInspector, ToolchainInspector, OllamaInspector, JarvisInspector
            from ai_suite.managers.service_manager import ServiceManager
            from ai_suite.core.services.log_service import LogService
            
            service_registry = ServiceRegistry(event_bus)
            capability_manager = CapabilityManager(service_registry)
            intelligence_service = IntelligenceService()
            
            # Register all inspectors
            for InspectorCls in [CPUInspector, MemoryInspector, GPUInspector, BatteryInspector, DiskInspector, NetworkInspector,
                                 WindowsInspector, ProcessInspector, GitInspector, ProjectInspector, PythonInspector, 
                                 ToolchainInspector, OllamaInspector, JarvisInspector]:
                intelligence_service.register(InspectorCls())
                
            service_manager = ServiceManager(event_bus, service_registry)
            
            # Container Registration
            ServiceContainer.register(AssistantManager, assistant_manager)
            ServiceContainer.register(SessionManager, session_manager)
            ServiceContainer.register(ModelManager, model_manager)
            ServiceContainer.register(MemoryEngine, memory_engine)
            ServiceContainer.register(ContextBuilder, context_builder)
            ServiceContainer.register(ServiceRegistry, service_registry)
            ServiceContainer.register(CapabilityManager, capability_manager)
            ServiceContainer.register(IntelligenceService, intelligence_service)
            ServiceContainer.register(ServiceManager, service_manager)
            
            # --- STAGE: VOICE ---
            self.stage_complete.emit(BootStage.VOICE)
            from ai_suite.core.services.tts_service import TTSAdapterService
            from ai_suite.core.services.stt_service import STTAdapterService
            log_service = LogService(event_bus)
            tts_service = TTSAdapterService(event_bus)
            stt_service = STTAdapterService(event_bus)
            service_registry.register(log_service)
            service_registry.register(tts_service)
            service_registry.register(stt_service)
            
            # --- STAGE: VISION ---
            self.stage_complete.emit(BootStage.VISION)
            from ai_suite.core.services.camera_service import CameraAdapterService
            from ai_suite.core.services.vision_service import VisionAdapterService
            from ai_suite.core.services.ocr_service import OCRAdapterService
            from ai_suite.core.services.face_service import FaceRecognitionAdapterService
            camera_service = CameraAdapterService(event_bus)
            vision_service = VisionAdapterService(event_bus)
            ocr_service = OCRAdapterService(event_bus)
            face_service = FaceRecognitionAdapterService(event_bus)
            service_registry.register(camera_service)
            service_registry.register(vision_service)
            service_registry.register(ocr_service)
            service_registry.register(face_service)
            
            # --- STAGE: AUTOMATION ---
            self.stage_complete.emit(BootStage.AUTOMATION)
            service_manager.bootstrap()
            logger = capability_manager.request("LOGGING")
            if logger:
                logger.log("Service Platform successfully bootstrapped.")
                
            # --- STAGE: WORKSPACE ---
            self.stage_complete.emit(BootStage.WORKSPACE)
            from ai_suite.core.workspace.registry import WorkspaceRegistry
            from ai_suite.managers.workspace_manager import WorkspaceCoordinator
            from ai_suite.managers.notification_manager import NotificationManager
            from ai_suite.managers.project_manager import ProjectManager
            
            workspace_registry = WorkspaceRegistry(event_bus)
            workspace_manager = WorkspaceCoordinator(event_bus, workspace_registry)
            notification_manager = NotificationManager(event_bus)
            project_manager = ProjectManager(event_bus)
            
            services['workspace_manager'] = workspace_manager
            
            ServiceContainer.register(WorkspaceRegistry, workspace_registry)
            ServiceContainer.register(WorkspaceCoordinator, workspace_manager)
            ServiceContainer.register(NotificationManager, notification_manager)
            ServiceContainer.register(ProjectManager, project_manager)
            
            from ai_suite.core.assistant.registry import AssistantRegistry
            from ai_suite.core.assistant.delegation import TaskDelegationEngine
            from ai_suite.core.assistant.context import SharedContextTransfer
            from ai_suite.core.assistant.planner import TaskPlanner
            from ai_suite.core.assistant.router import AssistantRouter
            from ai_suite.core.assistant.types import AssistantProfile, ReasoningPolicy, DelegationTransparency
            
            assistant_registry = AssistantRegistry(event_bus)
            context_transfer = SharedContextTransfer(memory_engine)
            delegation_engine = TaskDelegationEngine(event_bus, assistant_registry)
            task_planner = TaskPlanner(assistant_registry, delegation_engine, context_transfer)
            assistant_router = AssistantRouter(assistant_registry)
            
            # Recreate assistant_manager
            assistant_manager = AssistantManager(event_bus, assistant_registry)
            services['assistant_manager'] = assistant_manager
            
            ServiceContainer.register(AssistantManager, assistant_manager)
            ServiceContainer.register(AssistantRegistry, assistant_registry)
            ServiceContainer.register(TaskPlanner, task_planner)
            ServiceContainer.register(AssistantRouter, assistant_router)
            
            # Register Profiles
            assistant_registry.register(AssistantProfile(
                id="jarvis", display_name="JARVIS", 
                description="General-purpose desktop assistant specializing in conversational AI and automation.",
                workspace_id="jarvis", system_prompt="You are JARVIS. Assist the user with general tasks.",
                reasoning_policy=ReasoningPolicy("conversational"),
                default_capabilities=["vision", "voice", "camera", "automation", "ocr"],
                supported_capabilities=["vision", "voice", "camera", "automation", "ocr", "planning"],
                routing_keywords=["camera", "see", "speak", "schedule"],
                routing_priority=100, visibility=DelegationTransparency.INTERACTIVE, icon="zap"
            ))
            
            assistant_registry.register(AssistantProfile(
                id="friday", display_name="FRIDAY", 
                description="Advanced development assistant specializing in IDE, code actions, and project analysis.",
                workspace_id="friday", system_prompt="You are FRIDAY. Assist the user with development and coding.",
                reasoning_policy=ReasoningPolicy("structured_code"),
                default_capabilities=["ide", "git", "terminal", "project_analysis", "code_actions"],
                supported_capabilities=["ide", "git", "terminal", "project_analysis", "code_actions", "code_generation"],
                routing_keywords=["code", "script", "git", "terminal", "compile"],
                routing_priority=90, visibility=DelegationTransparency.SILENT, icon="code"
            ))
            
            assistant_registry.register(AssistantProfile(
                id="edith", display_name="EDITH", 
                description="Deep research and OSINT assistant.",
                workspace_id="edith", system_prompt="You are EDITH. Research and analyze.",
                reasoning_policy=ReasoningPolicy("research"),
                default_capabilities=["web_search", "document_analysis", "data_mining"],
                supported_capabilities=["web_search", "document_analysis", "data_mining"],
                routing_keywords=["research", "search", "find", "analyze"],
                routing_priority=80, visibility=DelegationTransparency.INFORMATIONAL, icon="glasses"
            ))
            
            from ai_suite.workspaces.jarvis_workspace import JarvisWorkspace
            from ai_suite.workspaces.friday_workspace import FridayWorkspace
            from ai_suite.workspaces.edith_workspace import EdithWorkspace
            
            jarvis_workspace = JarvisWorkspace(event_bus, capability_manager)
            friday_workspace = FridayWorkspace(event_bus, capability_manager, session_manager, project_manager)
            edith_workspace = EdithWorkspace(event_bus)
            
            workspace_registry.register(jarvis_workspace)
            workspace_registry.register(friday_workspace)
            workspace_registry.register(edith_workspace)
            
            # --- STAGE: COMPLETE ---
            self._sleep(0.5)
            self.stage_complete.emit(BootStage.COMPLETE)
            
            # Allow the greeting to fade in and be visible briefly
            # before we trigger the final cinematic transition.
            self._sleep(1.5)
            
            # CRITICAL: Move all QObjects instantiated in this thread 
            # to the main thread before this thread exits.
            # Otherwise, Qt will destroy them when the thread terminates,
            # causing an immediate crash when they are accessed.
            from PyQt5.QtWidgets import QApplication
            main_thread = QApplication.instance().thread()
            
            for key, svc in services.items():
                if hasattr(svc, 'moveToThread'):
                    try:
                        svc.moveToThread(main_thread)
                    except Exception as e:
                        import logging
                        logging.getLogger("boot").warning(f"Could not move {key} to main thread: {e}")
            
            self.finished_data.emit(services)
            
        except Exception as e:
            import traceback
            pass
            pass
            with open(r'C:\Users\VICTUS\AppData\Local\AISuite\logs\packaged_crash.log', 'a') as f:
                traceback.print_exc(file=f)
            import logging
            logging.getLogger("boot").error(f"BootWorker Exception: {e}")
            self.error = e


class BootController(QObject):
    """Orchestrates the boot UI and the background initialization thread."""
    
    # Emitted when the entire boot process (including transition) is complete
    # and the main application window is ready to take over.
    boot_finished = pyqtSignal(dict)
    
    def __init__(self, boot_overlay):
        super().__init__()
        self._skipped = False
        self.overlay = boot_overlay
        self.worker = BootWorker()
        
        self.worker.stage_complete.connect(self._on_stage_complete)
        self.worker.finished_data.connect(self._on_worker_finished)
        self.overlay.skip_requested.connect(self._on_skip_requested)
        
    def start(self):
        """Start the initialization worker."""
        self.overlay.begin_phase1()
        self.worker.start()
        
    def _on_stage_complete(self, stage: BootStage):
        """Called when the worker completes a stage."""
        info = STAGE_CONFIG[stage]
        self.overlay.reactor.set_reactor_level(info.reactor_level)
        self.overlay.add_message(info.display_text)
        
        if stage == BootStage.COMPLETE:
            display_name = self._get_user_display_name()
            self.overlay.set_greeting(f"Welcome back,\n{display_name}")
            
    def _get_user_display_name(self) -> str:
        """Fetch Windows Display Name or fallback to getpass."""
        import ctypes
        import getpass
        try:
            get_user_name_ex = ctypes.windll.secur32.GetUserNameExW
            NameDisplay = 3
            size = ctypes.pointer(ctypes.c_ulong(0))
            get_user_name_ex(NameDisplay, None, size)
            if size.contents.value > 0:
                buf = ctypes.create_unicode_buffer(size.contents.value)
                if get_user_name_ex(NameDisplay, buf, size):
                    name = buf.value.strip()
                    if name:
                        return name
        except Exception:
            pass
            
        # Fallback to username
        name = getpass.getuser()
        if not name:
            name = "Developer"
        return name.capitalize() if name.islower() else name
            
    @pyqtSlot(dict)
    def _on_worker_finished(self, services: Dict[str, Any]):
        """Called when the worker thread finishes all initialization."""
        if self.worker.error:
            import logging
            logging.getLogger("boot").error(f"Error during boot: {self.worker.error}")
            
        self.services = services
        
        if self._skipped:
            self._on_transition_halfway()
            self.overlay.close_boot()
            return
        
        # Connect halfway signal to emit boot_finished
        # so the main window can be constructed behind the glowing boot screen
        self.overlay.transition_halfway.connect(self._on_transition_halfway)
        
        # Start the cinematic transition
        self.overlay.start_transition()
        
    @pyqtSlot()
    def _on_transition_halfway(self):
        """Called halfway through the glow expansion."""
        self.boot_finished.emit(self.services)
        
    def _on_skip_requested(self):
        """Handle ESC key press to skip boot animation."""
        self._skipped = True
        self.worker.skip()
        self.overlay.stop_animations()
        
        # If the worker is already finished, finish immediately
        if hasattr(self, 'services'):
            self._on_transition_halfway()
            self.overlay.close_boot()

