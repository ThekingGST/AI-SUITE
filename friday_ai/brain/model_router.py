"""Model Router: Intelligently selects the best model based on intent and profile."""

from __future__ import annotations
from typing import Optional

from friday_ai.brain.task_analyzer import TaskIntent
from friday_ai.brain.model_registry import ModelRegistry, ModelCapabilities, ModelProfile
from friday_ai.services.provider_manager import ProviderHealth


class ModelRouter:
    """Intelligently routes requests to the optimal AI model."""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        
    def get_best_model(
        self, 
        intent: TaskIntent, 
        profile: ModelProfile, 
        health_status: dict[str, ProviderHealth]
    ) -> Optional[ModelCapabilities]:
        """Route to the best model using a filtering and scoring pipeline."""
        
        all_models = self.registry.get_all_models()
        if not all_models:
            return None
            
        # 1. Profile Filter (Hard constraints)
        candidates = []
        for m in all_models:
            if profile == ModelProfile.OFFLINE_ONLY and not m.is_local:
                continue
            if profile == ModelProfile.CLOUD_PREFERRED and m.is_local:
                # If they prefer cloud, we only filter locals if there ARE cloud models,
                # but for simplicity, we treat it as a soft preference later. 
                # Let's treat it as a hard constraint here IF there are cloud models.
                pass
            candidates.append(m)
            
        if not candidates:
            # Fallback if hard constraints eliminated everything
            candidates = all_models
            
        # 2. Health Filter
        healthy_candidates = []
        for m in candidates:
            h = health_status.get(m.provider)
            if h and h.is_healthy:
                healthy_candidates.append(m)
                
        if healthy_candidates:
            candidates = healthy_candidates
            
        # 3. Scoring Pipeline
        best_model = None
        best_score = -1.0
        
        for m in candidates:
            score = 0.0
            
            # Base capability scoring based on Intent
            if intent in (TaskIntent.CODE_GENERATION, TaskIntent.REFACTORING, TaskIntent.DEBUGGING):
                score += m.coding_capability * 2.0
                score += m.reasoning_capability * 1.5
            elif intent == TaskIntent.ARCHITECTURE:
                score += m.reasoning_capability * 2.0
                score += m.coding_capability * 1.0
            elif intent == TaskIntent.CHAT or intent == TaskIntent.EXPLANATION:
                score += m.chat_capability * 2.0
                score += m.speed_rating * 1.0
            else:
                score += m.reasoning_capability + m.coding_capability + m.chat_capability
                
            # Profile Soft Weights
            if profile == ModelProfile.FAST:
                score += m.speed_rating * 3.0
            elif profile == ModelProfile.DEEP_REASONING:
                score += m.reasoning_capability * 3.0
            elif profile == ModelProfile.CLOUD_PREFERRED and not m.is_local:
                score += 5.0
            elif profile == ModelProfile.CODING:
                score += m.coding_capability * 3.0
                
            if score > best_score:
                best_score = score
                best_model = m
                
        return best_model
