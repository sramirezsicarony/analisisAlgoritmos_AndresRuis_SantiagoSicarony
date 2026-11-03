"""Carga del corpus (data/corpus.json) generado por scripts/construir_corpus.py."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_CORPUS = RAIZ / "data" / "corpus.json"


@lru_cache(maxsize=1)
def cargar_corpus() -> tuple[dict, ...]:
    if not RUTA_CORPUS.exists():
        raise FileNotFoundError(
            "No existe data/corpus.json. Ejecuta: python scripts/construir_corpus.py")
    with open(RUTA_CORPUS, encoding="utf-8") as f:
        return tuple(json.load(f))


def articulo_por_id(id_articulo: int) -> dict:
    for art in cargar_corpus():
        if art["id"] == id_articulo:
            return art
    raise KeyError(f"No existe el artículo {id_articulo}")


def etiqueta_corta(art: dict, largo: int = 45) -> str:
    titulo = art["titulo"]
    if len(titulo) > largo:
        titulo = titulo[: largo - 1] + "…"
    return f"{art['id']}. {titulo}"
