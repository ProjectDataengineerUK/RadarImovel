from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayerStats:
    layer_type: str
    polygons_loaded: int
    source: str
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class MeshResult:
    """Resultado do ibge_mesh loader: mesh dict + stats de carga."""

    mesh: dict[str, dict[str, Any]]  # {ibge_code: {name, state, geom_wkt}}
    municipalities_loaded: int
    errors: list[str] = field(default_factory=list)


class GeoLoader(ABC):
    @abstractmethod
    def load(self, session: Any, **kwargs: Any) -> LayerStats: ...
