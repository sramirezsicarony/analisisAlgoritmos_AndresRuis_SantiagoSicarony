"""
Coeficiente de Jaccard (modelo de conjuntos).

    J(A, B) = |A ∩ B| / |A ∪ B|        en [0, 1]

A y B son los conjuntos de términos (o de k-gramas de caracteres, si se elige
esa representación) de cada abstract. La intersección se cuenta recorriendo el
conjunto más pequeño y consultando el otro (tabla hash): O(min(|A|, |B|));
|A ∪ B| = |A| + |B| - |A ∩ B|.
"""
from __future__ import annotations


def conjunto(tokens) -> set:
    resultado = set()
    for t in tokens:
        resultado.add(t)
    return resultado


def kgramas(texto: str, k: int = 3) -> set[str]:
    """Shingles de k caracteres: 'learning' -> {'lea', 'ear', 'arn', ...}."""
    resultado = set()
    for i in range(len(texto) - k + 1):
        resultado.add(texto[i:i + k])
    return resultado


def interseccion(a: set, b: set) -> set:
    if len(a) > len(b):
        a, b = b, a
    comun = set()
    for x in a:
        if x in b:
            comun.add(x)
    return comun


def coeficiente(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    inter = len(interseccion(a, b))
    union = len(a) + len(b) - inter
    return inter / union


def detalle(a: set, b: set) -> dict:
    inter = interseccion(a, b)
    union = len(a) + len(b) - len(inter)
    return {"A": len(a), "B": len(b), "interseccion": sorted(inter),
            "n_interseccion": len(inter), "n_union": union,
            "jaccard": len(inter) / union if union else 1.0,
            "solo_A": sorted(x for x in a if x not in b),
            "solo_B": sorted(x for x in b if x not in a)}
