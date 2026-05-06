from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ModelAdapter(ABC):
    """Interface for every risk-category adapter."""

    name: str

    @abstractmethod
    def predict(
        self,
        features: dict[str, Any],
        normalized: dict[str, float],
        feature_risks: dict[str, float],
        external_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError
