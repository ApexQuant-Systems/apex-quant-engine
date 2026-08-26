# filename: data_pipeline/asset_manager.py
import logging
from typing import List
from config.global_config import GLOBAL_CONFIG

class ApexAssetManager:
    """
    Module 1.1: Guardrail engine controlling asset universe constraints.
    Insulates downstream systems from tracking unauthorized symbols.
    """
    def __init__(self):
        self._universe = set(GLOBAL_CONFIG.FAVORITES_MATRIX)
        self.logger = logging.getLogger("ApexAssetManager")

    def is_allowed(self, symbol: str) -> bool:
        """Determines if the queried symbol falls within the uncorrupted matrix bounds."""
        return symbol.upper() in self._universe

    def get_active_universe(self) -> List[str]:
        """Returns the frozen active instrument registry matrix."""
        return list(self._universe)
