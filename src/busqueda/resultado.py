"""Estructura común de resultados para los algoritmos de búsqueda de patrones."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResultadoBusqueda:
    algoritmo: str
    patron: str
    posiciones: list[int]
    comparaciones: int                 # comparaciones carácter a carácter
    tiempo_preproceso_s: float
    tiempo_busqueda_s: float
    pasos: list[dict] = field(default_factory=list)   # traza (si se pidió)
    extra: dict = field(default_factory=dict)          # tablas auxiliares, colisiones...

    @property
    def tiempo_total_s(self) -> float:
        return self.tiempo_preproceso_s + self.tiempo_busqueda_s
