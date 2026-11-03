"""
Similitud semántica con embeddings preentrenados (modelos de IA).

Modelos (ver scripts/construir_embeddings.py):
  * GloVe 100d   (glove-wiki-gigaword-100): vectores entrenados factorizando la
    matriz global de co-ocurrencias de palabras (Pennington et al., 2014).
  * FastText 300d (fasttext-wiki-news-subwords-300): skip-gram/CBOW con
    n-gramas de caracteres (Bojanowski et al., 2017; Mikolov et al., 2018).

Representación del abstract (mean pooling):
    v(d) = (1/k) · Σ_{i=1..k} e(w_i)
donde w_1..w_k son los tokens de d (sin stopwords, sin stemming) que existen en
el vocabulario del modelo y e(w) es el embedding de la palabra.

Medidas:
    coseno(u, v)     = u·v / (||u|| ||v||)
    euclidiana(u, v) = sqrt( Σ (u_i - v_i)² ),  similitud = 1 / (1 + distancia)

Las operaciones vectoriales se escriben con ciclos explícitos para que el
cálculo sea transparente (la dimensión es 100 o 300, así que es rápido).
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from src.corpus import RAIZ

CARPETA = RAIZ / "data" / "embeddings"
MODELOS_DISPONIBLES = {
    "glove100": "GloVe (Wikipedia+Gigaword, 100 dim.)",
    "fasttext300": "FastText (Wiki-News subwords, 300 dim.)",
}


class ModeloEmbeddings:
    def __init__(self, nombre: str):
        ruta = CARPETA / f"{nombre}.npz"
        if not ruta.exists():
            raise FileNotFoundError(
                f"No se encontró {ruta}. Ejecuta: python scripts/construir_embeddings.py")
        datos = np.load(ruta)
        self.nombre = nombre
        self.descripcion = MODELOS_DISPONIBLES.get(nombre, nombre)
        palabras = [str(p) for p in datos["palabras"]]
        vectores = datos["vectores"]
        self.dimension = int(vectores.shape[1])
        self.tabla: dict[str, list[float]] = {
            p: [float(x) for x in vectores[i]] for i, p in enumerate(palabras)}

    def vector_palabra(self, palabra: str) -> list[float] | None:
        return self.tabla.get(palabra)

    def vector_documento(self, tokens: list[str]) -> tuple[list[float], list[str], list[str]]:
        """Promedio de los vectores de las palabras. Devuelve (vector, usadas, fuera_vocab)."""
        suma = [0.0] * self.dimension
        usadas, oov = [], []
        for t in tokens:
            v = self.tabla.get(t)
            if v is None:
                oov.append(t)
                continue
            usadas.append(t)
            for i in range(self.dimension):
                suma[i] += v[i]
        k = len(usadas)
        if k:
            suma = [x / k for x in suma]
        return suma, usadas, oov


@lru_cache(maxsize=4)
def cargar_modelo(nombre: str) -> ModeloEmbeddings:
    return ModeloEmbeddings(nombre)


def producto_punto(u: list[float], v: list[float]) -> float:
    total = 0.0
    for i in range(len(u)):
        total += u[i] * v[i]
    return total


def norma(u: list[float]) -> float:
    return math.sqrt(producto_punto(u, u))


def coseno(u: list[float], v: list[float]) -> float:
    nu, nv = norma(u), norma(v)
    if nu == 0 or nv == 0:
        return 0.0
    return producto_punto(u, v) / (nu * nv)


def euclidiana(u: list[float], v: list[float]) -> float:
    total = 0.0
    for i in range(len(u)):
        d = u[i] - v[i]
        total += d * d
    return math.sqrt(total)


def similitud_euclidiana(u: list[float], v: list[float]) -> float:
    return 1.0 / (1.0 + euclidiana(u, v))
