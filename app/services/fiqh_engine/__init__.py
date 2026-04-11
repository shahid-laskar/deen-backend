"""
Fiqh Engine — Factory & Registry
=================================
Single import point. Resolves a madhab string to the correct engine.
"""

from app.services.fiqh_engine.base import BaseMadhab, CycleInput, FiqhRuling
from app.services.fiqh_engine.hanafi import HanafiEngine
from app.services.fiqh_engine.madhabs import ShafiEngine, MalikiEngine, HanbaliEngine

__all__ = ["get_fiqh_engine", "CycleInput", "FiqhRuling", "BaseMadhab"]

_REGISTRY: dict[str, BaseMadhab] = {
    "hanafi": HanafiEngine(),
    "shafii": ShafiEngine(),
    "maliki": MalikiEngine(),
    "hanbali": HanbaliEngine(),
}


def get_fiqh_engine(madhab: str) -> BaseMadhab:
    """
    Return the fiqh engine for the given madhab key.
    Raises ValueError for unknown madhabs.
    """
    engine = _REGISTRY.get(madhab.lower())
    if engine is None:
        raise ValueError(
            f"Unknown madhab: '{madhab}'. "
            f"Supported: {list(_REGISTRY.keys())}"
        )
    return engine


def classify_cycle(madhab: str, cycle: CycleInput) -> FiqhRuling:
    """Convenience function — get engine and classify in one call."""
    return get_fiqh_engine(madhab).classify_cycle(cycle)
