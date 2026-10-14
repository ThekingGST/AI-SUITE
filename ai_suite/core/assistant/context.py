from typing import Any, List, Optional
from ai_suite.core.assistant.types import DelegationContext
from ai_suite.core.memory.engine import MemoryEngine
from jarvis_ai.utils.logger import LOGGER

class SharedContextTransfer:
    """Safely extracts structured context for a delegated assistant without duplicating history."""
    
    def __init__(self, memory_engine: MemoryEngine):
        self.memory_engine = memory_engine
        
    def build_delegation_context(
        self,
        task: str,
        goal: str,
        constraints: List[str],
        workspace_id: str,
        source_id: str,
        target_id: str,
        project_path: Optional[str] = None,
        user_intent: str = ""
    ) -> DelegationContext:
        """Constructs a context package for the delegated assistant."""
        
        # 1. Retrieve the most relevant memory IDs from the active session
        # This prevents the receiving assistant from needing a full copy of the conversation.
        # Instead, it receives pointers (IDs) to relevant facts and context.
        recent_memories = self._get_recent_memory_ids(workspace_id)
        
        # 2. Package context
        ctx = DelegationContext(
            task=task,
            goal=goal,
            constraints=constraints,
            workspace_id=workspace_id,
            source_assistant_id=source_id,
            target_assistant_id=target_id,
            project_path=project_path,
            relevant_memory_ids=recent_memories,
            relevant_files=[],
            user_intent=user_intent
        )
        LOGGER.info(f"Built SharedContextTransfer from {source_id} to {target_id}")
        return ctx
        
    def _get_recent_memory_ids(self, workspace_id: str) -> List[str]:
        # In a real implementation, we would query the MemoryEngine for recent memory IDs in the session.
        # For this prototype, we return a mock list of IDs.
        return ["mem-123", "mem-456"]
