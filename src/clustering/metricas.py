"""
Métricas de evaluación interna del agrupamiento (no requieren etiquetas reales).

1) Coeficiente de correlación cofenética (CCC), Sokal & Rohlf (1962):
   la distancia cofenética c(i,j) es la altura del dendrograma donde i y j
   quedan por primera vez en el mismo clúster. El CCC es la correlación de
   Pearson entre las distancias originales d(i,j) y c(i,j) para todos los pares
   i < j. Mide qué tan fielmente el árbol preserva las distancias originales
   (1 = perfecto). O(n²) pares.

2) Coeficiente de silueta (Rousseeuw, 1987) para un corte en k clústeres:
     a(i) = distancia media de i a los demás miembros de su clúster
     b(i) = mínima, sobre los otros clústeres C, de la distancia media de i a C
     s(i) = (b(i) - a(i)) / max(a(i), b(i))     (s(i) = 0 si su clúster tiene 1 elemento)
     S    = promedio de s(i)                   en [-1, 1]
   Valores altos = grupos compactos y bien separados. O(n²).
"""
from __future__ import annotations

import math

from src.clustering.jerarquico import Fusion, miembros


def matriz_cofenetica(fusiones: list[Fusion], n: int) -> list[list[float]]:
    C = [[0.0] * n for _ in range(n)]
    grupos = miembros(fusiones, n)
    for f in fusiones:
        for i in grupos[f.a]:
            for j in grupos[f.b]:
                C[i][j] = C[j][i] = f.distancia
    return C


def pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    sxy = sxx = syy = 0.0
    for i in range(n):
        dx, dy = x[i] - mx, y[i] - my
        sxy += dx * dy
        sxx += dx * dx
        syy += dy * dy
    if sxx == 0 or syy == 0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def correlacion_cofenetica(D: list[list[float]], fusiones: list[Fusion]) -> float:
    n = len(D)
    C = matriz_cofenetica(fusiones, n)
    orig, cof = [], []
    for i in range(n):
        for j in range(i + 1, n):
            orig.append(D[i][j])
            cof.append(C[i][j])
    return pearson(orig, cof)


def silueta(D: list[list[float]], etiquetas: list[int]) -> tuple[float, list[float]]:
    n = len(D)
    grupos: dict[int, list[int]] = {}
    for i, e in enumerate(etiquetas):
        grupos.setdefault(e, []).append(i)
    valores = []
    for i in range(n):
        propio = grupos[etiquetas[i]]
        if len(propio) == 1:
            valores.append(0.0)
            continue
        a = sum(D[i][j] for j in propio if j != i) / (len(propio) - 1)
        b = math.inf
        for e, otros in grupos.items():
            if e == etiquetas[i]:
                continue
            media = sum(D[i][j] for j in otros) / len(otros)
            if media < b:
                b = media
        valores.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return sum(valores) / n, valores
