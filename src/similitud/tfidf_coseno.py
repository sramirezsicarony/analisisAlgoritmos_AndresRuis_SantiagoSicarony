"""
Similitud del coseno sobre vectores TF-IDF (modelo de espacio vectorial).

Para un término t en el documento d de un corpus con N documentos:
    tf(t, d)  = frecuencia de t en d / número de tokens de d
    idf(t)    = ln( (1 + N) / (1 + df(t)) ) + 1        (idf suavizado)
    w(t, d)   = tf(t, d) · idf(t)

    cos(A, B) = Σ_t w(t,A)·w(t,B) / ( sqrt(Σ_t w(t,A)²) · sqrt(Σ_t w(t,B)²) )
    ángulo    = arccos(cos(A, B))

El IDF se calcula con los 20 abstracts del corpus, de modo que las palabras que
aparecen en casi todos (p. ej. "artificial", "intelligence") pesan poco.

Los vectores se guardan como diccionarios dispersos {término: peso}; el producto
punto solo recorre los términos del vector más pequeño.
Complejidad: construir el modelo O(T) con T = total de tokens del corpus;
coseno entre dos documentos O(min(|A|, |B|)) con |A| = términos distintos de A.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


def frecuencias(tokens: list[str]) -> dict[str, int]:
    conteo: dict[str, int] = {}
    for t in tokens:
        conteo[t] = conteo.get(t, 0) + 1
    return conteo


@dataclass
class ModeloTFIDF:
    documentos: list[list[str]]
    df: dict[str, int] = field(default_factory=dict)
    idf: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        n = len(self.documentos)
        for tokens in self.documentos:
            for t in frecuencias(tokens):        # cada término cuenta una vez por documento
                self.df[t] = self.df.get(t, 0) + 1
        for t, d in self.df.items():
            self.idf[t] = math.log((1 + n) / (1 + d)) + 1

    def tf(self, tokens: list[str]) -> dict[str, float]:
        total = len(tokens)
        return {t: c / total for t, c in frecuencias(tokens).items()} if total else {}

    def vector(self, tokens: list[str]) -> dict[str, float]:
        n = len(self.documentos)
        idf_nuevo = math.log((1 + n) / 1) + 1      # término no visto en el corpus
        return {t: f * self.idf.get(t, idf_nuevo) for t, f in self.tf(tokens).items()}


def producto_punto(u: dict[str, float], v: dict[str, float]) -> float:
    if len(u) > len(v):
        u, v = v, u
    total = 0.0
    for t, w in u.items():
        if t in v:
            total += w * v[t]
    return total


def norma(u: dict[str, float]) -> float:
    suma = 0.0
    for w in u.values():
        suma += w * w
    return math.sqrt(suma)


def coseno(u: dict[str, float], v: dict[str, float]) -> float:
    nu, nv = norma(u), norma(v)
    if nu == 0 or nv == 0:
        return 0.0
    return producto_punto(u, v) / (nu * nv)


def angulo_grados(cos: float) -> float:
    cos = max(-1.0, min(1.0, cos))
    return math.degrees(math.acos(cos))


def detalle(modelo: ModeloTFIDF, tokens_a: list[str], tokens_b: list[str]) -> dict:
    """Tabla término a término para la demostración paso a paso."""
    fa, fb = frecuencias(tokens_a), frecuencias(tokens_b)
    va, vb = modelo.vector(tokens_a), modelo.vector(tokens_b)
    filas = []
    for t in sorted(set(fa) | set(fb)):
        wa, wb = va.get(t, 0.0), vb.get(t, 0.0)
        filas.append({
            "termino": t, "f_A": fa.get(t, 0), "f_B": fb.get(t, 0),
            "tf_A": wa and fa[t] / len(tokens_a), "tf_B": wb and fb[t] / len(tokens_b),
            "df": modelo.df.get(t, 0), "idf": modelo.idf.get(t, 0.0),
            "w_A": wa, "w_B": wb, "w_A*w_B": wa * wb,
        })
    pp = producto_punto(va, vb)
    na, nb = norma(va), norma(vb)
    c = pp / (na * nb) if na and nb else 0.0
    return {"filas": filas, "producto_punto": pp, "norma_A": na, "norma_B": nb,
            "coseno": c, "angulo": angulo_grados(c),
            "n_tokens_A": len(tokens_a), "n_tokens_B": len(tokens_b)}
