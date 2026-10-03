"""
Base runner class for low-dimensional environments.
Provides interface for policy evaluation.
"""

from typing import Dict
from abc import ABC, abstractmethod


class BaseLowdimRunner(ABC):
    """
    Abstract base class for environment runners.
    Handles policy evaluation in simulation environments.
    """

    def __init__(self, output_dir: str):
        """
        Initialize runner.
        
        Args:
            output_dir: Directory to save evaluation outputs
        """
        self.output_dir = output_dir

    @abstractmethod
    def run(self, policy) -> Dict:
        """
        Run policy in environment and collect metrics.
        
        Args:
            policy: Policy to evaluate (must have predict_action method)
            
        Returns:
            results: Dict with evaluation metrics (rewards, episode_lengths, etc.)
        """
        pass
